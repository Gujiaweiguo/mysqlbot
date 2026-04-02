import sqlalchemy as sa

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "9f6cc6f2a8b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
                "uq_ds_one_active_sync_job ON datasource_sync_job (ds_id) "
                "WHERE status IN ('pending', 'running', 'finalizing')"
            )
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            sa.text("DROP INDEX CONCURRENTLY IF EXISTS uq_ds_one_active_sync_job")
        )
