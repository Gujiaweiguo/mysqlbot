"""070_openclaw_external_session_key

Revision ID: 70f0a1f0c1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-17 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "70f0a1f0c1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat",
        sa.Column("external_session_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_chat_create_by_oid_external_session_key",
        "chat",
        ["create_by", "oid", "external_session_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_create_by_oid_external_session_key", table_name="chat")
    op.drop_column("chat", "external_session_key")
