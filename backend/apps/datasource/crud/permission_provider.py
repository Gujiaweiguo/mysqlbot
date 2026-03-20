import json

from apps.datasource.models.permission import DsPermission, DsRules
from common.core.deps import SessionDep


def get_ds_permission_model() -> type[DsPermission]:
    return DsPermission


def get_ds_rules_model() -> type[DsRules]:
    return DsRules


def trans_record_to_dto(_session: SessionDep, permission: object) -> dict[str, object]:
    expression_tree = getattr(permission, "expression_tree", None)
    permission_id = getattr(permission, "id", 0)
    tree = None
    if isinstance(expression_tree, str) and expression_tree:
        parsed = json.loads(expression_tree)
        if isinstance(parsed, dict):
            tree = parsed
    return {"id": permission_id if isinstance(permission_id, int) else 0, "tree": tree}
