"""Add Clerk integration fields to users table

Revision ID: add_clerk_fields
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_clerk_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add Clerk integration fields to users table."""
    # Add new columns for Clerk integration
    op.add_column('users', sa.Column('clerk_user_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('clerk_tenant_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('external_auth_provider', sa.String(50), nullable=True, default='clerk'))
    
    # Create indexes for better performance
    op.create_index('ix_users_clerk_user_id', 'users', ['clerk_user_id'], unique=True)
    op.create_index('ix_users_clerk_tenant_id', 'users', ['clerk_tenant_id'])
    
    # Update existing users to have clerk as default auth provider
    op.execute("UPDATE users SET external_auth_provider = 'clerk' WHERE external_auth_provider IS NULL")


def downgrade():
    """Remove Clerk integration fields from users table."""
    # Drop indexes
    op.drop_index('ix_users_clerk_tenant_id', 'users')
    op.drop_index('ix_users_clerk_user_id', 'users')
    
    # Drop columns
    op.drop_column('users', 'external_auth_provider')
    op.drop_column('users', 'clerk_tenant_id')
    op.drop_column('users', 'clerk_user_id')