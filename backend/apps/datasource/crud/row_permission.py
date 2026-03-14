# Author: Junjun
# Date: 2025/6/25

from typing import Any

from sqlmodel import col

from apps.datasource.models.datasource import CoreDatasource, CoreField
from apps.db.constant import DB
from apps.system.models.system_variable_model import SystemVariable
from common.core.deps import CurrentUser, SessionDep


def transFilterTree(
    session: SessionDep,
    current_user: CurrentUser,
    tree_list: list[Any] | None,
    ds: CoreDatasource,
) -> str | None:
    if tree_list is None:
        return None
    res: list[str] = []
    for dto in tree_list:
        tree = dto.get("tree") if isinstance(dto, dict) else getattr(dto, "tree", None)
        if tree is None:
            continue
        tree_exp = transTreeToWhere(session, current_user, tree, ds)
        if tree_exp is not None:
            res.append(tree_exp)
    return " AND ".join(res)


def transTreeToWhere(
    session: SessionDep,
    current_user: CurrentUser,
    tree: dict[str, Any] | None,
    ds: CoreDatasource,
) -> str | None:
    if tree is None:
        return None
    logic = str(tree.get("logic", "AND"))

    items = tree.get("items")
    expressions: list[str] = []
    if items is not None:
        for item in items:
            if not isinstance(item, dict):
                continue
            exp: str | None = None
            if item.get("type") == "item":
                exp = transTreeItem(session, current_user, item, ds)
            elif item.get("type") == "tree":
                sub_tree = item.get("sub_tree")
                exp = transTreeToWhere(
                    session,
                    current_user,
                    sub_tree if isinstance(sub_tree, dict) else None,
                    ds,
                )

            if exp is not None:
                expressions.append(exp)
    return "(" + f" {logic} ".join(expressions) + ")" if expressions else None


def transTreeItem(
    session: SessionDep,
    current_user: CurrentUser,
    item: dict[str, Any],
    ds: CoreDatasource,
) -> str | None:
    res: str | None = None
    field_id = item.get("field_id")
    if field_id is None:
        return None
    field = session.query(CoreField).filter(col(CoreField.id) == int(field_id)).first()
    if field is None:
        return None

    db = DB.get_db(ds.type)
    whereName = db.prefix + field.field_name + db.suffix
    term = str(item.get("term", ""))
    whereTerm = transFilterTerm(term)

    if item.get("filter_type") == "enum":
        enum_values_raw = item.get("enum_value")
        enum_values = enum_values_raw if isinstance(enum_values_raw, list) else []
        if len(enum_values) > 0:
            if ds.type == "sqlServer" and (
                field.field_type == "nchar"
                or field.field_type == "NCHAR"
                or field.field_type == "nvarchar"
                or field.field_type == "NVARCHAR"
            ):
                normalized = [str(v) for v in enum_values]
                res = "(" + whereName + " IN (N'" + "',N'".join(normalized) + "'))"
            else:
                normalized = [str(v) for v in enum_values]
                res = "(" + whereName + " IN ('" + "','".join(normalized) + "'))"
    else:
        # if system variable, do check and get value
        # new field: value_type(variable or normal), variable_id
        value_type = item.get("value_type")
        if value_type and value_type == "variable":
            # get system variable
            variable_id = item.get("variable_id")
            if variable_id is not None:
                sys_variable = (
                    session.query(SystemVariable)
                    .filter(col(SystemVariable.id) == int(variable_id))
                    .first()
                )
                if sys_variable is None:
                    return None
                # do inner system variable
                if sys_variable.type == "system":
                    res = (
                        whereName
                        + whereTerm
                        + getSysVariableValue(sys_variable, current_user)
                    )
                else:
                    # check user variable
                    user_variables = current_user.system_variables
                    if (
                        user_variables is None
                        or len(user_variables) == 0
                        or not userHaveVariable(user_variables, sys_variable)
                    ):
                        return None
                    else:
                        # get user variable
                        u_variable = None
                        for u in user_variables:
                            if u.get("variableId") == sys_variable.id:
                                u_variable = u
                                break
                        if u_variable is None:
                            return None

                        # check value
                        values = u_variable.get("variableValues")
                        if not isinstance(values, list) or len(values) == 0:
                            return None
                        if sys_variable.var_type == "text":
                            set_sys = set(sys_variable.value)
                            values = [x for x in values if x in set_sys]
                            if values is None or len(values) == 0:
                                return None
                        elif sys_variable.var_type == "number":
                            if (
                                sys_variable.value[0] is not None
                                and values[0] < sys_variable.value[0]
                            ) or (
                                sys_variable.value[1] is not None
                                and values[0] > sys_variable.value[1]
                            ):
                                return None
                        elif sys_variable.var_type == "datetime":
                            if (
                                sys_variable.value[0] is not None
                                and values[0] < sys_variable.value[0]
                            ) or (
                                sys_variable.value[1] is not None
                                and values[0] > sys_variable.value[1]
                            ):
                                return None

                        # build exp
                        whereValue = ""
                        if term == "null":
                            whereValue = ""
                        elif term == "not_null":
                            whereValue = ""
                        elif term == "empty":
                            whereValue = "''"
                        elif term == "not_empty":
                            whereValue = "''"
                        elif term == "in" or term == "not in":
                            if ds.type == "sqlServer" and (
                                field.field_type == "nchar"
                                or field.field_type == "NCHAR"
                                or field.field_type == "nvarchar"
                                or field.field_type == "NVARCHAR"
                            ):
                                whereValue = (
                                    "(N'"
                                    + "', N'".join([str(v) for v in values])
                                    + "')"
                                )
                            else:
                                whereValue = (
                                    "('" + "', '".join([str(v) for v in values]) + "')"
                                )
                        elif term == "like" or term == "not like":
                            if ds.type == "sqlServer" and (
                                field.field_type == "nchar"
                                or field.field_type == "NCHAR"
                                or field.field_type == "nvarchar"
                                or field.field_type == "NVARCHAR"
                            ):
                                whereValue = f"N'%{values[0]}%'"
                            else:
                                whereValue = f"'%{values[0]}%'"
                        else:
                            if ds.type == "sqlServer" and (
                                field.field_type == "nchar"
                                or field.field_type == "NCHAR"
                                or field.field_type == "nvarchar"
                                or field.field_type == "NVARCHAR"
                            ):
                                whereValue = f"N'{values[0]}'"
                            else:
                                whereValue = f"'{values[0]}'"

                        res = whereName + whereTerm + whereValue
            else:
                return None
        else:
            value = str(item.get("value", ""))
            whereValue = ""

            if term == "null":
                whereValue = ""
            elif term == "not_null":
                whereValue = ""
            elif term == "empty":
                whereValue = "''"
            elif term == "not_empty":
                whereValue = "''"
            elif term == "in" or term == "not in":
                if ds.type == "sqlServer" and (
                    field.field_type == "nchar"
                    or field.field_type == "NCHAR"
                    or field.field_type == "nvarchar"
                    or field.field_type == "NVARCHAR"
                ):
                    whereValue = "(N'" + "', N'".join(value.split(",")) + "')"
                else:
                    whereValue = "('" + "', '".join(value.split(",")) + "')"
            elif term == "like" or term == "not like":
                if ds.type == "sqlServer" and (
                    field.field_type == "nchar"
                    or field.field_type == "NCHAR"
                    or field.field_type == "nvarchar"
                    or field.field_type == "NVARCHAR"
                ):
                    whereValue = f"N'%{value}%'"
                else:
                    whereValue = f"'%{value}%'"
            else:
                if ds.type == "sqlServer" and (
                    field.field_type == "nchar"
                    or field.field_type == "NCHAR"
                    or field.field_type == "nvarchar"
                    or field.field_type == "NVARCHAR"
                ):
                    whereValue = f"N'{value}'"
                else:
                    whereValue = f"'{value}'"

            res = whereName + whereTerm + whereValue
    return res


def transFilterTerm(term: str) -> str:
    if term == "eq":
        return " = "
    if term == "not_eq":
        return " <> "
    if term == "lt":
        return " < "
    if term == "le":
        return " <= "
    if term == "gt":
        return " > "
    if term == "ge":
        return " >= "
    if term == "in":
        return " IN "
    if term == "not in":
        return " NOT IN "
    if term == "like":
        return " LIKE "
    if term == "not like":
        return " NOT LIKE "
    if term == "null":
        return " IS NULL "
    if term == "not_null":
        return " IS NOT NULL "
    if term == "empty":
        return " = "
    if term == "not_empty":
        return " <> "
    if term == "between":
        return " BETWEEN "
    return ""


def userHaveVariable(
    user_variables: list[dict[str, Any]], sys_variable: SystemVariable
) -> bool:
    for u in user_variables:
        if sys_variable.id == u.get("variableId"):
            return True
    return False


def getSysVariableValue(sys_variable: SystemVariable, current_user: CurrentUser) -> str:
    variable_value = sys_variable.value
    if not isinstance(variable_value, list) or len(variable_value) == 0:
        return ""
    key = str(variable_value[0])
    if key == "name":
        return current_user.name
    if key == "account":
        return current_user.account
    if key == "email":
        return current_user.email
    return ""
