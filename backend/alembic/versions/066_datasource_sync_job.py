import sqlalchemy as sa

from alembic import op

revision = "2e2d8eb6f1a9"
down_revision = "8ff90df7871d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _ = op.create_table(
        "datasource_sync_job",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("ds_id", sa.BigInteger(), nullable=False),
        sa.Column("oid", sa.BigInteger(), nullable=False),
        sa.Column("create_by", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=True),
        sa.Column("total_tables", sa.BigInteger(), nullable=False),
        sa.Column("completed_tables", sa.BigInteger(), nullable=False),
        sa.Column("failed_tables", sa.BigInteger(), nullable=False),
        sa.Column("skipped_tables", sa.BigInteger(), nullable=False),
        sa.Column("total_fields", sa.BigInteger(), nullable=False),
        sa.Column("completed_fields", sa.BigInteger(), nullable=False),
        sa.Column("current_table_name", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=False), nullable=True),
        sa.Column("finish_time", sa.DateTime(timezone=False), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_datasource_sync_job_create_time",
        "datasource_sync_job",
        ["create_time"],
        unique=False,
    )
    op.create_index(
        "ix_datasource_sync_job_ds_id",
        "datasource_sync_job",
        ["ds_id"],
        unique=False,
    )
    op.create_index(
        "ix_datasource_sync_job_ds_id_status",
        "datasource_sync_job",
        ["ds_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_datasource_sync_job_status",
        "datasource_sync_job",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_datasource_sync_job_status", table_name="datasource_sync_job")
    op.drop_index(
        "ix_datasource_sync_job_ds_id_status", table_name="datasource_sync_job"
    )
    op.drop_index("ix_datasource_sync_job_ds_id", table_name="datasource_sync_job")
    op.drop_index(
        "ix_datasource_sync_job_create_time", table_name="datasource_sync_job"
    )
    op.drop_table("datasource_sync_job")
