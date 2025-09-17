"""add scraped_jobs table

Revision ID: 4d9aa2b1b6d0
Revises: 3101a4c2b9ab
Create Date: 2025-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = '4d9aa2b1b6d0'
down_revision = '3101a4c2b9ab'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scraped_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('job_id_ext', sa.String(200), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), nullable=True),
        sa.Column('hash', sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['pipeline_runs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scraped_jobs_run_id', 'scraped_jobs', ['run_id'])
    op.create_index('ix_scraped_jobs_source', 'scraped_jobs', ['source'])
    op.create_index('ix_scraped_jobs_hash', 'scraped_jobs', ['hash'])
    op.create_index('ix_scraped_jobs_company', 'scraped_jobs', ['company'])
    op.create_index('ix_scraped_jobs_title', 'scraped_jobs', ['title'])


def downgrade():
    op.drop_table('scraped_jobs')
