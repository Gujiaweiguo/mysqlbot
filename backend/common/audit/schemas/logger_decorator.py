import functools
import inspect
import json
import re
import time
import traceback
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal, cast

from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import and_
from sqlmodel import Session
from sqlmodel import select as sqlmodel_select

from apps.system.crud.user import get_user_by_account
from apps.system.schemas.system_schema import UserInfoDTO
from common.audit.models.log_model import (
    OperationStatus,
    OperationType,
    SystemLog,
    SystemLogsResource,
)
from common.audit.schemas.log_utils import build_resource_union_query
from common.audit.schemas.request_context import RequestContext
from common.core.db import engine


def get_resource_name_by_id_and_module(
    session: Session, resource_id: object | list[object] | None, module: str
) -> list[dict[str, str]]:
    resource_union_query = build_resource_union_query()
    resource_alias = resource_union_query.alias("resource")

    if resource_id is None:
        return []

    resource_ids: list[object]
    if isinstance(resource_id, list):
        resource_ids = cast(list[object], resource_id)
    else:
        resource_ids = [resource_id]

    if not resource_ids:
        return []

    # 构建查询，使用 IN 条件
    query = sqlmodel_select(
        resource_alias.c.id, resource_alias.c.name, resource_alias.c.module
    ).where(
        and_(
            resource_alias.c.id.in_([str(id_) for id_ in resource_ids]),
            resource_alias.c.module == module,
        )
    )

    results = cast(
        list[tuple[str | None, str | None, str | None]],
        session.exec(query).all(),
    )

    return [
        {
            "resource_id": row[0] or "",
            "resource_name": row[1] or "",
            "module": row[2] or "",
        }
        for row in results
    ]


class LogConfig(BaseModel):
    operation_type: OperationType
    operation_detail: str | None = None
    module: str | None = None

    # Extract the expression of resource ID from the parameters
    resource_id_expr: str | None = None

    # Extract the expression for resource ID from the returned result
    result_id_expr: str | None = None

    # Extract the expression for resource name or other info from the returned result
    remark_expr: str | None = None

    # Is it only recorded upon success
    save_on_success_only: bool = False

    # Whether to ignore errors (i.e. record them as successful even when they occur)
    ignore_errors: bool = False

    # Whether to extract request parameters
    extract_params: bool = True

    # Delay recording (if the resource ID needs to be extracted from the result, it can be set to True)
    delay_logging: bool = False


class SystemLogger:
    @staticmethod
    async def create_log(
        session: Session,
        operation_type: OperationType,
        operation_detail: str,
        user: UserInfoDTO | None = None,
        status: OperationStatus = OperationStatus.SUCCESS,
        ip_address: str | None = None,
        user_agent: str | None = None,
        execution_time: int = 0,
        error_message: str | None = None,
        module: str | None = None,
        resource_id: object | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        remark: str | None = None,
    ) -> SystemLog | None:
        try:
            resource_id_str: str | None = None
            if resource_id is not None:
                resource_id_str = str(resource_id)

            log = SystemLog(
                operation_type=operation_type,
                operation_detail=operation_detail,
                user_id=user.id if user else None,
                user_name=user.account if user else None,
                operation_status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                execution_time=execution_time,
                error_message=error_message,
                module=module,
                resource_id=resource_id_str,
                request_method=request_method,
                request_path=request_path,
                create_time=datetime.now(),
                remark=remark,
            )
            session.add(log)
            session.commit()
            return log
        except Exception as e:
            session.rollback()
            print(f"Failed to create system log: {e}")
            return None

    @staticmethod
    def get_client_info(request: Request) -> dict[str, str | None]:
        """Obtain client information"""
        ip_address = None
        user_agent = None

        if request:
            # Obtain IP address
            if request.client:
                ip_address = request.client.host
            # Attempt to obtain the real IP from X-Forwarded-For
            if "x-forwarded-for" in request.headers:
                ip_address = request.headers["x-forwarded-for"].split(",")[0].strip()

            # Get User Agent
            user_agent = request.headers.get("user-agent")

        return {"ip_address": ip_address, "user_agent": user_agent}

    @staticmethod
    def extract_value_from_object(expression: str, obj: object) -> object | None:
        """
        Extract values from objects based on expressions
        support:
        -Object attribute: 'user. id'
        -Dictionary key: 'data ['id'] '
        -List index: 'items [0]. id'
        """
        if not expression or obj is None:
            return None

        if expression == "result_self":
            return obj

        try:
            # Handling point separated attribute access
            parts = expression.split(".")
            current: object | None = obj

            for part in parts:
                if not current:
                    return None

                # Handle dictionary key access, such as data ['id ']
                if "[" in part and "]" in part:
                    match = re.search(r"\[['\"]?([^\]'\"\]]+)['\"]?\]", part)
                    if match:
                        key = match.group(1)
                        # Get Object Part
                        obj_part = part.split("[")[0]
                        if isinstance(current, dict):
                            current_dict = cast(dict[str, object], current)
                            current = current_dict.get(obj_part)
                        else:
                            current = cast(
                                object | None, getattr(current, obj_part, None)
                            )
                        if current is None:
                            return None

                        # Get key value
                        if isinstance(current, dict):
                            current_dict = cast(dict[str, object], current)
                            current = current_dict.get(key)
                        elif isinstance(current, (list, tuple)) and key.isdigit():
                            current_seq = cast(
                                list[object] | tuple[object, ...], current
                            )
                            index = int(key)
                            if 0 <= index < len(current_seq):
                                current = current_seq[index]
                            else:
                                return None
                        else:
                            current = cast(object | None, getattr(current, key, None))
                        if current is None:
                            return None
                    else:
                        return None

                # Process list indexes, such as items.0.id
                elif part.isdigit() and isinstance(current, (list, tuple)):
                    current_seq = cast(list[object] | tuple[object, ...], current)
                    index = int(part)
                    if 0 <= index < len(current_seq):
                        current = current_seq[index]
                    else:
                        return None

                    # Normal attribute access
                else:
                    if isinstance(current, dict):
                        current = cast(object | None, current.get(part))
                    else:
                        current = cast(object | None, getattr(current, part, None))
                    if current is None:
                        return None

            return current if current is not None else None

        except Exception:
            return None

    @staticmethod
    def extract_resource_id(
        expression: str | None,
        source: object,
        source_type: Literal["args", "kwargs", "result"] = "args",
    ) -> object | None:
        """Extract resource IDs from different sources"""
        if not expression:
            return None

        try:
            if source_type == "result":
                # Extract directly from the result object
                return SystemLogger.extract_value_from_object(expression, source)

            elif source_type == "args":
                # Extract from function parameters
                if isinstance(source, tuple):
                    source_tuple = cast(tuple[object, ...], source)
                    if not source_tuple:
                        return None
                    # The first element is the function itself
                    func_args = (
                        cast(tuple[object, ...], source_tuple[0])
                        if isinstance(source_tuple[0], tuple)
                        else source_tuple
                    )

                    # Processing args [index] expression
                    if expression.startswith("args["):
                        pattern = r"args\[(\d+)\]"
                        match = re.match(pattern, expression)
                        if match:
                            index = int(match.group(1))
                            if index < len(func_args):
                                value = func_args[index]
                                return value if value is not None else None

                    # Process attribute expressions
                    return SystemLogger.extract_value_from_object(expression, func_args)
                elif isinstance(source, dict):
                    source_dict = cast(dict[str, object], source)
                    # Simple parameter name
                    if expression in source_dict:
                        value = source_dict[expression]
                        return value if value is not None else None

                    # complex expression
                    return SystemLogger.extract_value_from_object(
                        expression, source_dict
                    )

            elif source_type == "kwargs":
                # Extract from keyword parameters
                if isinstance(source, dict):
                    source_dict = cast(dict[str, object], source)
                    # Simple parameter name
                    if expression in source_dict:
                        value = source_dict[expression]
                        return value if value is not None else None

                    # complex expression
                    return SystemLogger.extract_value_from_object(
                        expression, source_dict
                    )

            return None

        except Exception:
            return None

    @staticmethod
    def extract_from_function_params(
        expression: str | None, func_args: object, func_kwargs: dict[str, object]
    ) -> object | None:
        """Extract values from function parameters"""
        if not expression:
            return None

        # Attempt to extract from location parameters
        result = SystemLogger.extract_resource_id(expression, func_args, "args")
        if result:
            return result

        # Attempt to extract from keyword parameters
        result = SystemLogger.extract_resource_id(expression, func_kwargs, "kwargs")
        if result:
            return result

        # Attempt to encapsulate parameters as objects for extraction
        try:
            if isinstance(func_args, tuple) and func_args:
                func_args_tuple = cast(tuple[object, ...], func_args)
                # Create a dictionary containing all parameters
                params_dict: dict[str, object] = {}

                # Add location parameters
                for i, arg in enumerate(func_args_tuple):
                    params_dict[f"arg_{i}"] = arg

                # Add keyword parameters
                params_dict.update(func_kwargs)

                # Attempt to extract from the dictionary
                return SystemLogger.extract_resource_id(
                    expression, params_dict, "kwargs"
                )
        except Exception:
            pass

        return None

    @staticmethod
    def get_current_user(request: Request | None) -> UserInfoDTO | None:
        """Retrieve current user information from the request"""
        if not request:
            return None
        try:
            current_user = getattr(request.state, "current_user", None)
            if current_user:
                return cast(UserInfoDTO, current_user)
        except Exception:
            pass

        return None

    @staticmethod
    def extract_request_params(request: Request | None) -> str | None:
        """Extract request parameters"""
        if not request:
            return None

        try:
            params: dict[str, object] = {}

            # query parameters
            if request.query_params:
                params["query"] = dict(request.query_params)

            # path parameter
            if request.path_params:
                params["path"] = dict(request.path_params)

            # Head information (sensitive information not recorded)
            headers: dict[str, str] = {}
            for key, value in request.headers.items():
                if key.lower() not in ["authorization", "cookie", "set-cookie"]:
                    headers[key] = value
            if headers:
                params["headers"] = headers

            # Request Body - Only records Content Type and Size
            content_type = request.headers.get("content-type", "")
            content_length = request.headers.get("content-length")
            params["body_info"] = {
                "content_type": content_type,
                "content_length": content_length or "",
            }

            return json.dumps(params, ensure_ascii=False, default=str)

        except Exception:
            return None

    @classmethod
    async def create_log_record(
        cls,
        config: LogConfig,
        status: OperationStatus,
        execution_time: int,
        error_message: str | None = None,
        resource_id: object | list[object] | None = None,
        resource_name: str | None = None,
        request: Request | None = None,
        remark: str | None = None,
        oid: int = -1,
        opt_type_ref: OperationType | None = None,
        resource_info_list: list[dict[str, str]] | None = None,
    ) -> SystemLog | None:
        """Create log records"""
        try:
            # Obtain user information
            user_info = cls.get_current_user(request)
            user_id = user_info.id if user_info else -1
            user_name = user_info.name if user_info else "-1"
            if config.operation_type == OperationType.LOGIN:
                user_id = int(resource_id) if isinstance(resource_id, int) else -1
                user_name = resource_name or "-1"

            # Obtain client information
            client_info = (
                cls.get_client_info(request)
                if request is not None
                else {"ip_address": None, "user_agent": None}
            )
            # Get request parameters
            if config.extract_params:
                _ = cls.extract_request_params(request)

            # Create log object
            log = SystemLog(
                operation_type=opt_type_ref if opt_type_ref else config.operation_type,
                operation_detail=config.operation_detail or "",
                user_id=user_id,
                user_name=user_name,
                oid=user_info.oid if user_info else oid,
                operation_status=status,
                ip_address=client_info.get("ip_address"),
                user_agent=client_info.get("user_agent"),
                execution_time=execution_time,
                error_message=error_message,
                module=config.module,
                resource_id=str(resource_id),
                request_method=request.method if request else None,
                request_path=request.url.path if request else None,
                create_time=datetime.now(),
                remark=remark,
            )

            with Session(engine) as session:
                session.add(log)
                session.commit()
                session.refresh(log)
                # 统一处理不同类型的 resource_id_info
                if isinstance(resource_id, list):
                    resource_id_list = cast(list[object], resource_id)
                    resource_ids = [str(rid) for rid in resource_id_list]
                else:
                    resource_ids = [str(resource_id)]
                # 批量添加 SystemLogsResource
                resource_entries: list[SystemLogsResource] = []
                for resource_id_details in resource_ids:
                    resource_entry = SystemLogsResource(
                        resource_id=resource_id_details,
                        log_id=log.id,
                        module=config.module,
                    )
                    resource_entries.append(resource_entry)
                if resource_entries:
                    session.bulk_save_objects(resource_entries)
                    session.commit()

                if (
                    config.operation_type == OperationType.DELETE
                    and resource_info_list is not None
                ):
                    for resource_info in resource_info_list:
                        rows = session.exec(
                            sqlmodel_select(SystemLogsResource).filter_by(
                                resource_id=resource_info["resource_id"],
                                module=resource_info["module"],
                            )
                        ).all()
                        for row in rows:
                            row.resource_name = resource_info["resource_name"]
                    session.commit()
                return log

        except Exception:
            print(f"[SystemLogger] Failed to create log: {str(traceback.format_exc())}")
            return None


def system_log(
    config: LogConfig | dict[str, object],
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """
    System log annotation decorator, supports extracting resource IDs from returned results

    Usage example:
    @system_log({
    "operation_type": OperationType.CREATE,
    Operation_detail ":" Create User ",
    "module": "user",
    'result_id_expr ':' id '# Extract the id field from the returned result
    })
    """
    # If a dictionary is passed in, convert it to a LogConfig object
    if isinstance(config, dict):
        config = LogConfig.model_validate(config)

    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        @functools.wraps(func)
        async def async_wrapper(*args: object, **kwargs: object) -> object:
            start_time = time.time()
            status = OperationStatus.SUCCESS
            error_message = None
            request = None
            resource_id = None
            resource_name = None
            remark: str | None = None
            oid = -1
            opt_type_ref = None
            resource_info_list = None
            result = None

            try:
                # Get current request
                request = RequestContext.get_request()
                func_signature = inspect.signature(func)
                bound_args = func_signature.bind(*args, **kwargs)
                bound_args.apply_defaults()
                unified_kwargs = cast(dict[str, object], dict(bound_args.arguments))
                func_kwargs = kwargs

                # Step 1: Attempt to extract the resource ID from the parameters
                if config.resource_id_expr:
                    resource_id = SystemLogger.extract_from_function_params(
                        config.resource_id_expr, unified_kwargs, func_kwargs
                    )
                if config.remark_expr:
                    remark_value = SystemLogger.extract_from_function_params(
                        config.remark_expr, unified_kwargs, func_kwargs
                    )
                    if remark_value is not None:
                        remark = str(remark_value)

                if config.operation_type == OperationType.LOGIN:
                    input_account_dec = SystemLogger.extract_from_function_params(
                        "form_data.username",
                        args,
                        func_kwargs,
                    )
                    from common.utils.crypto import sqlbot_decrypt

                    if not isinstance(input_account_dec, str):
                        input_account_dec = ""
                    input_account = await sqlbot_decrypt(input_account_dec)
                    with Session(engine) as session:
                        userInfo = get_user_by_account(
                            session=session, account=input_account
                        )
                        if userInfo is not None:
                            resource_id = userInfo.id
                            resource_name = userInfo.name
                            oid = userInfo.oid
                        else:
                            resource_id = -1
                            oid = -1
                            resource_name = input_account
                if config.operation_type == OperationType.DELETE:
                    with Session(engine) as session:
                        module = config.module or ""
                        resource_info_list = get_resource_name_by_id_and_module(
                            session, resource_id, module
                        )

                if config.operation_type == OperationType.CREATE_OR_UPDATE:
                    opt_type_ref = (
                        OperationType.UPDATE
                        if resource_id is not None
                        else OperationType.CREATE
                    )
                else:
                    opt_type_ref = config.operation_type
                # Execute the original function
                async_func = cast(Callable[..., Awaitable[object]], func)
                result = await async_func(*args, **kwargs)
                # Step 2: If the resource ID is configured to be extracted from the results and has not been extracted before
                if config.result_id_expr and not resource_id and result:
                    resource_id = SystemLogger.extract_resource_id(
                        config.result_id_expr, result, "result"
                    )
                return result

            except Exception as e:
                status = OperationStatus.FAILED
                error_message = str(e)

                # If it is an HTTPException, retrieve the status code
                if isinstance(e, HTTPException):
                    error_message = f"HTTP {e.status_code}: {e.detail}"

                # If configured to ignore errors, mark as successful
                if config.ignore_errors:
                    status = OperationStatus.SUCCESS

                raise e

            finally:
                # If configured to only record on success and the current status is failure, skip
                if not (
                    config.save_on_success_only and status == OperationStatus.FAILED
                ):
                    # Calculate execution time
                    execution_time = int((time.time() - start_time) * 1000)
                    # Asynchronous creation of log records
                    try:
                        _ = await SystemLogger.create_log_record(
                            config=config,
                            status=status,
                            execution_time=execution_time,
                            error_message=error_message,
                            resource_id=resource_id,
                            resource_name=resource_name,
                            remark=remark,
                            request=request,
                            oid=oid,
                            opt_type_ref=opt_type_ref,
                            resource_info_list=resource_info_list,
                        )
                    except Exception as log_error:
                        print(f"[SystemLogger] Log creation failed: {log_error}")

        @functools.wraps(func)
        def sync_wrapper(*args: object, **kwargs: object) -> object:
            start_time = time.time()
            status = OperationStatus.SUCCESS
            error_message = None
            request = None
            resource_id = None
            resource_name = None
            resource_info_list = None
            result = None

            try:
                # Get current request
                request = RequestContext.get_request()
                func_signature = inspect.signature(func)
                bound_args = func_signature.bind(*args, **kwargs)
                bound_args.apply_defaults()
                unified_kwargs = cast(dict[str, object], dict(bound_args.arguments))
                func_kwargs = kwargs

                # Extract resource ID from parameters
                if config.resource_id_expr:
                    resource_id = SystemLogger.extract_from_function_params(
                        config.resource_id_expr, unified_kwargs, func_kwargs
                    )

                # Obtain client information
                if config.operation_type == OperationType.DELETE:
                    with Session(engine) as session:
                        module = config.module or ""
                        resource_info_list = get_resource_name_by_id_and_module(
                            session, resource_id, module
                        )

                # Execute the original function
                result = func(*args, **kwargs)

                # Extract resource ID from the results
                if config.result_id_expr and not resource_id and result:
                    resource_id = SystemLogger.extract_resource_id(
                        config.result_id_expr, result, "result"
                    )

                return result

            except Exception as e:
                status = OperationStatus.FAILED
                error_message = str(e)

                if isinstance(e, HTTPException):
                    error_message = f"HTTP {e.status_code}: {e.detail}"

                if config.ignore_errors:
                    status = OperationStatus.SUCCESS

                raise e

            finally:
                if not (
                    config.save_on_success_only and status == OperationStatus.FAILED
                ):
                    execution_time = int((time.time() - start_time) * 1000)

                    # In the synchronous version, we still create logs asynchronously
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            _ = loop.create_task(
                                SystemLogger.create_log_record(
                                    config=config,
                                    status=status,
                                    execution_time=execution_time,
                                    error_message=error_message,
                                    resource_id=resource_id,
                                    resource_name=resource_name,
                                    request=request,
                                    resource_info_list=resource_info_list,
                                )
                            )
                        else:
                            _ = asyncio.run(
                                SystemLogger.create_log_record(
                                    config=config,
                                    status=status,
                                    execution_time=execution_time,
                                    error_message=error_message,
                                    resource_id=resource_id,
                                    request=request,
                                )
                            )
                    except Exception as log_error:
                        print(f"[SystemLogger] Log creation failed: {log_error}")

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
