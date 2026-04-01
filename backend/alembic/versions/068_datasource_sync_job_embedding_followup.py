import sqlalchemy as sa

from alembic import op

revision = "9f6cc6f2a8b1"
down_revision = "d6d1d7a8b2f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasource_sync_job",
        sa.Column(
            "embedding_followup_status",
            sa.String(length=32),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("datasource_sync_job", "embedding_followup_status")
