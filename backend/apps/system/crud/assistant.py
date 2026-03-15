import importlib
import json
import re
from typing import Protocol, cast

from fastapi import FastAPI
from sqlmodel import Session, col, select
from starlette.middleware.cors import CORSMiddleware

# from apps.datasource.embedding.table_embedding import get_table_embedding
from apps.datasource.models.datasource import CoreDatasource
from apps.datasource.utils.utils import aes_encrypt
from apps.system.models.system_model import AssistantModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import (
    AssistantHeader,
    AssistantOutDsSchema,
    UserInfoDTO,
)
from common.core.config import settings
from common.core.db import engine
from common.core.sqlbot_cache import cache
from common.utils.locale import I18nHelper
from common.utils.utils import SQLBotLogUtil, get_domain_list, string_to_numeric_hash

_requests_module = importlib.import_module("requests")


class RequestsResponseProtocol(Protocol):
    status_code: int
    text: str


class RequestsGetProtocol(Protocol):
    def __call__(
        self,
        *,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        cookies: dict[str, str],
        timeout: int,
    ) -> RequestsResponseProtocol: ...


class LLMServiceProtocol(Protocol):
    current_assistant: AssistantHeader | None
    out_ds_instance: "AssistantOutDs | None"


def _parse_json_object(raw_json: str) -> dict[str, object]:
    parsed = cast(object, json.loads(raw_json))
    return cast(dict[str, object], parsed) if isinstance(parsed, dict) else {}


def _parse_json_object_list(raw_json: str) -> list[dict[str, object]]:
    parsed = cast(object, json.loads(raw_json))
    if not isinstance(parsed, list):
        return []
    parsed_list = cast(list[object], parsed)
    return [
        cast(dict[str, object], item) for item in parsed_list if isinstance(item, dict)
    ]


def _get_str_value(mapping: dict[str, object], key: str, default: str = "") -> str:
    value = mapping.get(key)
    return value if isinstance(value, str) else default


def _get_int_value(mapping: dict[str, object], key: str, default: int) -> int:
    value = mapping.get(key)
    return value if isinstance(value, int) else default


def _get_int_list(mapping: dict[str, object], key: str) -> list[int]:
    value = mapping.get(key)
    if not isinstance(value, list):
        return []
    value_list = cast(list[object], value)
    return [item for item in value_list if isinstance(item, int)]


requests_get = cast(RequestsGetProtocol, _requests_module.get)


@cache(
    namespace=CacheNamespace.EMBEDDED_INFO.value,
    cacheName=CacheName.ASSISTANT_INFO.value,
    keyExpression="assistant_id",
)
async def get_assistant_info(
    *, session: Session, assistant_id: int
) -> AssistantModel | None:
    db_model = session.get(AssistantModel, assistant_id)
    return db_model


def get_assistant_user(*, id: int) -> UserInfoDTO:
    return UserInfoDTO(
        id=id,
        account="sqlbot-inner-assistant",
        oid=1,
        name="sqlbot-inner-assistant",
        email="sqlbot-inner-assistant@sqlbot.com",
    )


def get_assistant_ds(
    session: Session, llm_service: LLMServiceProtocol
) -> list[dict[str, object]]:
    current_assistant = llm_service.current_assistant
    if current_assistant is None:
        return []
    assistant: AssistantHeader = current_assistant
    assistant_type = assistant.type
    if assistant_type == 0 or assistant_type == 2:
        configuration = assistant.configuration
        stmt = select(CoreDatasource).where(col(CoreDatasource.id) == -1)
        if configuration:
            config = _parse_json_object(configuration)
            oid = _get_int_value(config, "oid", 0)
            stmt = select(CoreDatasource).where(col(CoreDatasource.oid) == oid)
            if not assistant.online:
                public_list = _get_int_list(config, "public_list")
                if public_list:
                    stmt = stmt.where(col(CoreDatasource.id).in_(public_list))
                else:
                    return []
                """ private_list: list[int] = config.get('private_list') or None
                if private_list:
                    stmt = stmt.where(~CoreDatasource.id.in_(private_list)) """
        db_ds_list = session.exec(stmt).all()

        result_list = [
            {"id": ds.id, "name": ds.name, "description": ds.description}
            for ds in db_ds_list
        ]

        # filter private ds if offline
        return result_list
    out_ds_instance: AssistantOutDs = AssistantOutDsFactory.get_instance(assistant)
    llm_service.out_ds_instance = out_ds_instance
    dslist = out_ds_instance.get_simple_ds_list()
    # format?
    return list(dslist)


def init_dynamic_cors(app: FastAPI) -> tuple[bool, Exception] | None:
    try:
        with Session(engine) as session:
            list_result = session.exec(
                select(AssistantModel).order_by(col(AssistantModel.create_time))
            ).all()
            seen: set[str] = set()
            unique_domains: list[str] = []
            for item in list_result:
                if item.domain:
                    for domain in get_domain_list(item.domain):
                        domain = domain.strip()
                        if domain and domain not in seen:
                            seen.add(domain)
                            unique_domains.append(domain)
            cors_middleware = None
            for middleware in app.user_middleware:
                if getattr(middleware, "cls", None) is CORSMiddleware:
                    cors_middleware = middleware
                    break
            if cors_middleware:
                updated_origins = list(set(settings.all_cors_origins + unique_domains))
                cors_middleware.kwargs["allow_origins"] = updated_origins
    except Exception as e:
        return False, e
    return None


class AssistantOutDs:
    assistant: AssistantHeader
    ds_list: list[AssistantOutDsSchema] | None = None
    certificate: str | None = None
    request_origin: str | None = None

    def __init__(self, assistant: AssistantHeader) -> None:
        self.assistant = assistant
        self.ds_list = None
        self.certificate = assistant.certificate
        self.request_origin = assistant.request_origin
        _ = self.get_ds_from_api()

    # @cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_DS, keyExpression="current_user.id")
    def get_ds_from_api(self) -> list[AssistantOutDsSchema]:
        configuration = self.assistant.configuration
        if not configuration:
            raise Exception("Assistant configuration is empty")
        config = _parse_json_object(configuration)
        endpoint: str | None = self.get_complete_endpoint(
            endpoint=_get_str_value(config, "endpoint")
        )
        if not endpoint:
            raise Exception(
                f"Failed to get datasource list from {_get_str_value(config, 'endpoint')}, error: [Assistant domain or endpoint miss]"
            )
        certificate_list = _parse_json_object_list(self.certificate or "[]")
        header: dict[str, str] = {}
        cookies: dict[str, str] = {}
        param: dict[str, str] = {}
        for item in certificate_list:
            target = item.get("target")
            key = item.get("key")
            value = item.get("value")
            if not isinstance(key, str):
                continue
            if target == "header":
                header[key] = str(value)
            if target == "cookie":
                cookies[key] = str(value)
            if target == "param":
                param[key] = str(value)
        timeout = _get_int_value(config, "timeout", 10)
        res = requests_get(
            url=endpoint,
            params=param,
            headers=header,
            cookies=cookies,
            timeout=timeout,
        )
        if res.status_code == 200:
            result_json = _parse_json_object(res.text)
            if result_json.get("code") == 0 or result_json.get("code") == 200:
                temp_list = _parse_json_object_list(
                    json.dumps(result_json.get("data", []))
                )
                temp_ds_list = [self.convert2schema(item, config) for item in temp_list]
                self.ds_list = temp_ds_list
                return self.ds_list
            else:
                raise Exception(
                    f"Failed to get datasource list from {endpoint}, error: {result_json.get('message')}"
                )
        else:
            SQLBotLogUtil.error(
                f"Failed to get datasource list from {endpoint}, response: {res}"
            )
            raise Exception(
                f"Failed to get datasource list from {endpoint}, response: {res}"
            )

    def get_first_element(self, text: str) -> str:
        parts = re.split(r"[,;]", text.strip())
        first_domain = parts[0].strip()
        return first_domain

    def get_complete_endpoint(self, endpoint: str) -> str | None:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        domain_text = self.assistant.domain
        if not domain_text:
            return None
        if "," in domain_text or ";" in domain_text:
            return (
                self.request_origin.strip("/")
                if self.request_origin
                else self.get_first_element(domain_text).strip("/")
            ) + endpoint
        else:
            return f"{domain_text}{endpoint}"

    def get_simple_ds_list(self) -> list[dict[str, object]]:
        if self.ds_list:
            return [
                {"id": ds.id, "name": ds.name, "description": ds.comment}
                for ds in self.ds_list
            ]
        else:
            raise Exception("Datasource list is not found.")

    def get_db_schema(
        self,
        ds_id: int,
        question: str = "",
        embedding: bool = True,
        table_list: list[str] | None = None,
    ) -> str:
        _ = question
        _ = embedding
        ds = self.get_ds(ds_id)
        schema_str = ""
        db_name = (
            ds.db_schema
            if ds.db_schema is not None and ds.db_schema != ""
            else ds.dataBase
        )
        schema_str += f"【DB_ID】 {db_name}\n【Schema】\n"
        tables: list[dict[str, object]] = []
        i = 0
        for table in ds.tables or []:
            # 如果传入了 table_list，则只处理在列表中的表
            if table_list is not None and table.name not in table_list:
                continue

            i += 1
            schema_table = ""
            schema_table += (
                f"# Table: {db_name}.{table.name}"
                if ds.type != "mysql" and ds.type != "es"
                else f"# Table: {table.name}"
            )
            table_comment = table.comment
            if table_comment == "":
                schema_table += "\n[\n"
            else:
                schema_table += f", {table_comment}\n[\n"

            field_list: list[str] = []
            for field in table.fields or []:
                field_comment = field.comment
                if field_comment == "":
                    field_list.append(f"({field.name}:{field.type})")
                else:
                    field_list.append(f"({field.name}:{field.type}, {field_comment})")
            schema_table += ",\n".join(field_list)
            schema_table += "\n]\n"
            t_obj = {"id": i, "schema_table": schema_table}
            tables.append(t_obj)

        # do table embedding
        # if embedding and tables and settings.TABLE_EMBEDDING_ENABLED:
        #     tables = get_table_embedding(tables, question)

        if tables:
            for s in tables:
                schema_str += str(s.get("schema_table", ""))

        return schema_str

    def get_ds(
        self, ds_id: int, trans: I18nHelper | None = None
    ) -> AssistantOutDsSchema:
        if self.ds_list:
            for ds in self.ds_list:
                if ds.id == ds_id:
                    return ds
        else:
            raise Exception("Datasource list is not found.")
        raise Exception(
            f"Datasource id {ds_id} is not found."
            if trans is None
            else trans("i18n_data_training.datasource_id_not_found", key=ds_id)
        )

    def convert2schema(
        self,
        ds_dict: dict[str, object],
        config: dict[str, object],
    ) -> AssistantOutDsSchema:
        id_marker: str = ""
        attr_list = [
            "name",
            "type",
            "host",
            "port",
            "user",
            "dataBase",
            "schema",
            "mode",
        ]
        if config.get("encrypt", False):
            key_raw = config.get("aes_key", None)
            iv_raw = config.get("aes_iv", None)
            key_text = key_raw if isinstance(key_raw, str) else None
            iv_text = iv_raw if isinstance(iv_raw, str) else None
            aes_attrs = [
                "host",
                "user",
                "password",
                "dataBase",
                "db_schema",
                "schema",
                "mode",
            ]
            for attr in aes_attrs:
                attr_value = ds_dict.get(attr)
                if isinstance(attr_value, str):
                    try:
                        from common.utils.aes_crypto import simple_aes_decrypt

                        ds_dict[attr] = simple_aes_decrypt(
                            attr_value,
                            key_text,
                            iv_text,
                        )
                    except Exception as e:
                        raise Exception(
                            f"Failed to encrypt {attr} for datasource {ds_dict.get('name')}, error: {str(e)}"
                        )

        ds_id_raw = ds_dict.get("id", None)
        ds_id: int
        if not isinstance(ds_id_raw, (int, str)) or not ds_id_raw:
            for attr in attr_list:
                if attr in ds_dict:
                    id_marker += str(ds_dict.get(attr, "")) + "--sqlbot--"
            ds_id = string_to_numeric_hash(id_marker)
        else:
            ds_id = int(ds_id_raw)
        db_schema = ds_dict.get("schema", ds_dict.get("db_schema", ""))
        _ = ds_dict.pop("schema", None)
        return AssistantOutDsSchema.model_validate(
            {**ds_dict, "id": ds_id, "db_schema": str(db_schema)}
        )


class AssistantOutDsFactory:
    @staticmethod
    def get_instance(assistant: AssistantHeader) -> AssistantOutDs:
        return AssistantOutDs(assistant)


def get_out_ds_conf(ds: AssistantOutDsSchema, timeout: int = 30) -> bytes:
    conf = {
        "host": ds.host or "",
        "port": ds.port or 0,
        "username": ds.user or "",
        "password": ds.password or "",
        "database": ds.dataBase or "",
        "driver": "",
        "extraJdbc": ds.extraParams or "",
        "dbSchema": ds.db_schema or "",
        "timeout": timeout or 30,
        "mode": ds.mode or "",
    }
    conf["extraJdbc"] = ""
    return aes_encrypt(json.dumps(conf))
