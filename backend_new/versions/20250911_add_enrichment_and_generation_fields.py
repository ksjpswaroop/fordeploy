"""add enrichment and generation fields to scraped_jobs

Revision ID: add_enrichment_fields_20250911
Revises: add_pipeline_runs_20250911
Create Date: 2025-09-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_enrichment_fields_20250911'
# Chain after scraped_jobs migration
down_revision = '4d9aa2b1b6d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('scraped_jobs') as batch:
        batch.add_column(sa.Column('recruiter_name', sa.String(length=255), nullable=True))
        batch.add_column(sa.Column('recruiter_email', sa.String(length=255), nullable=True))
        batch.add_column(sa.Column('enriched_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('cover_letter', sa.Text(), nullable=True))
        batch.add_column(sa.Column('resume_custom', sa.Text(), nullable=True))
        batch.add_column(sa.Column('generated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('scraped_jobs') as batch:
        batch.drop_column('generated_at')
        batch.drop_column('resume_custom')
        batch.drop_column('cover_letter')
        batch.drop_column('enriched_at')
        batch.drop_column('recruiter_email')
        batch.drop_column('recruiter_name')
