"""Add user_login_attempts table

Revision ID: 1234567890ab
Revises: <previous_migration_id>
Create Date: 2025-09-04 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = '<previous_migration_id>'
depends_on = None

def upgrade() -> None:
    # Create user_login_attempts table
    op.create_table(
        'user_login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempt_time', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index(op.f('ix_user_login_attempts_user_id'), 'user_login_attempts', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_login_attempts_attempt_time'), 'user_login_attempts', ['attempt_time'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_login_attempts_attempt_time'), table_name='user_login_attempts')
    op.drop_index(op.f('ix_user_login_attempts_user_id'), table_name='user_login_attempts')
    op.drop_table('user_login_attempts')
