from sqlalchemy import and_, or_
from sqlmodel import col

from common.core.deps import SessionDep

from ..models.datasource import CoreField, FieldObj


def delete_field_by_ds_id(session: SessionDep, id: int) -> None:
    session.query(CoreField).filter(col(CoreField.ds_id) == id).delete(
        synchronize_session=False
    )
    session.commit()


def get_fields_by_table_id(
    session: SessionDep,
    id: int,
    field: FieldObj | None,
) -> list[CoreField]:
    if field and field.fieldName:
        keyword = field.fieldName
        return (
            session.query(CoreField)
            .filter(
                and_(
                    col(CoreField.table_id) == id,
                    or_(
                        col(CoreField.field_name).like(f"%{keyword}%"),
                        col(CoreField.field_name).like(f"%{keyword.lower()}%"),
                        col(CoreField.field_name).like(f"%{keyword.upper()}%"),
                    ),
                )
            )
            .order_by(col(CoreField.field_index).asc())
            .all()
        )
    return (
        session.query(CoreField)
        .filter(col(CoreField.table_id) == id)
        .order_by(col(CoreField.field_index).asc())
        .all()
    )


def update_field(session: SessionDep, item: CoreField) -> None:
    record = session.query(CoreField).filter(col(CoreField.id) == item.id).first()
    if record is None:
        return
    record.checked = item.checked
    record.custom_comment = item.custom_comment
    session.add(record)
    session.commit()
