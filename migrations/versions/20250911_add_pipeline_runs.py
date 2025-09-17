"""add pipeline_runs table

Revision ID: add_pipeline_runs_20250911
Revises: cc2476739bd5
Create Date: 2025-09-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_pipeline_runs_20250911'
down_revision = 'cc2476739bd5'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('query', sa.String(500), nullable=False),
        sa.Column('locations', sa.JSON(), nullable=True),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('stage', sa.String(50), nullable=False, server_default='discover'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('counts', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(1000), nullable=True),
        sa.Column('task_id', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pipeline_runs_task_id', 'pipeline_runs', ['task_id'])
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])

def downgrade():
    op.drop_index('ix_pipeline_runs_task_id', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_status', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')
