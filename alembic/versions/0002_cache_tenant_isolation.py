"""cache tenant isolation

Revision ID: 0002_cache_tenant_isolation
Revises: 0001_initial_schema
Create Date: 2026-08-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_cache_tenant_isolation"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("eval_cache") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(), nullable=True))

    op.execute("UPDATE eval_cache SET user_id = '__public__' WHERE user_id IS NULL OR user_id = ''")
    op.create_index("ix_eval_cache_user_id", "eval_cache", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_eval_cache_user_id", table_name="eval_cache")
    with op.batch_alter_table("eval_cache") as batch_op:
        batch_op.drop_column("user_id")

