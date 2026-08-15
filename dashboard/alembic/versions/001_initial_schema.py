"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('api_key_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('api_key_hash')
    )

    # 2. traces table
    op.create_table(
        'traces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('timestamp_start', sa.String(), nullable=False),
        sa.Column('timestamp_end', sa.String(), nullable=False),
        sa.Column('inputs', sa.Text(), nullable=True),
        sa.Column('outputs', sa.Text(), nullable=True),
        sa.Column('tool_name', sa.String(), nullable=True),
        sa.Column('tool_args', sa.Text(), nullable=True),
        sa.Column('tool_result', sa.Text(), nullable=True),
        sa.Column('retrieved_docs', sa.Text(), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('parent_node_ids', sa.Text(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'node_id', 'attempt_number', name='uq_session_node_attempt')
    )

    # 3. eval_cache table
    op.create_table(
        'eval_cache',
        sa.Column('input_hash', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('result_json', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('input_hash')
    )

    # 4. session_links table
    op.create_table(
        'session_links',
        sa.Column('child_session_id', sa.String(), nullable=False),
        sa.Column('parent_session_id', sa.String(), nullable=False),
        sa.Column('link_reason', sa.String(), nullable=True),
        sa.Column('timestamp', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('child_session_id', 'parent_session_id')
    )

def downgrade() -> None:
    op.drop_table('session_links')
    op.drop_table('eval_cache')
    op.drop_table('traces')
    op.drop_table('users')
