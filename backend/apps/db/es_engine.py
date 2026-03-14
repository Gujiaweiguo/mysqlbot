# Author: Junjun
# Date: 2025/9/9

import json
from base64 import b64encode
from urllib.request import Request, urlopen

from elasticsearch import Elasticsearch

from apps.datasource.models.datasource import DatasourceConf
from common.error import SingleMessageError


def get_es_auth(conf: DatasourceConf) -> dict[str, str]:
    username = f"{conf.username}"
    password = f"{conf.password}"

    credentials = f"{username}:{password}"
    encoded_credentials = b64encode(credentials.encode()).decode()

    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}",
    }


def get_es_connect(conf: DatasourceConf) -> Elasticsearch:
    es_client = Elasticsearch(
        [conf.host],  # ES address
        basic_auth=(conf.username, conf.password),
        verify_certs=False,
        compatibility_mode=True,
        headers=get_es_auth(conf),
    )
    return es_client


# get tables
def get_es_index(conf: DatasourceConf) -> list[tuple[str, str]]:
    es_client = get_es_connect(conf)
    indices = es_client.cat.indices(format="json")
    res: list[tuple[str, str]] = []
    if indices is not None:
        for idx in indices:
            if not isinstance(idx, dict):
                continue
            index_name = idx.get("index")
            if not isinstance(index_name, str):
                continue
            desc = ""
            # get mapping
            mapping = es_client.indices.get_mapping(index=index_name)
            mapping_item = mapping.get(index_name)
            if isinstance(mapping_item, dict):
                mappings = mapping_item.get("mappings")
                if isinstance(mappings, dict):
                    meta = mappings.get("_meta")
                    if isinstance(meta, dict):
                        meta_desc = meta.get("description")
                        if isinstance(meta_desc, str):
                            desc = meta_desc
            res.append((index_name, desc))
    return res


# get fields
def get_es_fields(conf: DatasourceConf, table_name: str) -> list[tuple[str, str, str]]:
    es_client = get_es_connect(conf)
    index_name = table_name
    mapping = es_client.indices.get_mapping(index=index_name)
    mapping_item = mapping.get(index_name)
    properties: dict[str, object] | None = None
    if isinstance(mapping_item, dict):
        mappings = mapping_item.get("mappings")
        if isinstance(mappings, dict):
            raw_properties = mappings.get("properties")
            if isinstance(raw_properties, dict):
                properties = raw_properties
    res: list[tuple[str, str, str]] = []
    if properties is not None:
        for field, config in properties.items():
            if not isinstance(config, dict):
                continue
            field_type = config.get("type")
            desc = ""
            meta = config.get("_meta")
            if isinstance(meta, dict):
                meta_desc = meta.get("description")
                if isinstance(meta_desc, str):
                    desc = meta_desc

            if isinstance(field_type, str) and field_type:
                res.append((field, field_type, desc))
            else:
                # object、nested...
                res.append((field, ",".join(list(config.keys())), desc))
    return res


# def get_es_data(conf: DatasourceConf, sql: str, table_name: str):
#     r = requests.post(f"{conf.host}/_sql/translate", json={"query": sql})
#     if r.json().get('error'):
#         print(json.dumps(r.json()))
#
#     es_client = get_es_connect(conf)
#     response = es_client.search(
#         index=table_name,
#         body=json.dumps(r.json())
#     )
#
#     # print(response)
#     fields = get_es_fields(conf, table_name)
#     res = []
#     for hit in response.get('hits').get('hits'):
#         item = []
#         if 'fields' in hit:
#             result = hit.get('fields')  # {'title': ['Python'], 'age': [30]}
#             for field in fields:
#                 v = result.get(field[0])
#                 item.append(v[0]) if v else item.append(None)
#             res.append(tuple(item))
#             # print(hit['fields']['title'][0])
#         # elif '_source' in hit:
#         #     print(hit.get('_source'))
#     return res, fields


def get_es_data_by_http(
    conf: DatasourceConf, sql: str
) -> tuple[list[list[object]], list[dict[str, object]]]:
    url = conf.host
    while url.endswith("/"):
        url = url[:-1]

    host = f"{url}/_sql?format=json"

    request = Request(
        url=host,
        data=json.dumps({"query": sql}).encode("utf-8"),
        headers=get_es_auth(conf),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")

    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")

    res = json.loads(body)
    if res.get("error"):
        raise SingleMessageError(json.dumps(res))
    fields = res.get("columns")
    result = res.get("rows")
    if not isinstance(fields, list):
        fields = []
    if not isinstance(result, list):
        result = []
    return result, fields
