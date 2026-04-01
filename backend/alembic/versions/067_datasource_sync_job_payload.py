import sqlalchemy as sa

from alembic import op

revision = "d6d1d7a8b2f0"
down_revision = "2e2d8eb6f1a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasource_sync_job",
        sa.Column(
            "requested_tables",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("datasource_sync_job", "requested_tables")
