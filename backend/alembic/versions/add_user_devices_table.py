"""Add user_devices table

Revision ID: 1234567890ab
Revises: head
Create Date: 2025-09-04 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = 'head'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_devices table
    op.create_table(
        'user_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=False, index=True),
        sa.Column('push_token', sa.String(length=255), nullable=True, index=True),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('os', sa.String(length=50), nullable=True),
        sa.Column('os_version', sa.String(length=50), nullable=True),
        sa.Column('browser', sa.String(length=100), nullable=True),
        sa.Column('browser_version', sa.String(length=50), nullable=True),
        sa.Column('last_ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_used_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on user_id for faster lookups
    op.create_index(op.f('ix_user_devices_user_id'), 'user_devices', ['user_id'], unique=False)
    
    # Add comment to the table
    op.execute("COMMENT ON TABLE user_devices IS 'Stores information about user devices for 2FA push notifications'")


def downgrade():
    # Drop the table and its indexes
    op.drop_index(op.f('ix_user_devices_user_id'), table_name='user_devices')
    op.drop_table('user_devices')
