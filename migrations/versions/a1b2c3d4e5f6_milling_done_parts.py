"""Add milling_done_parts for mixed orders

Revision ID: a1b2c3d4e5f6
Revises: fb9b97d5b5db
Create Date: 2025-02-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'fb9b97d5b5db'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('milling_done_parts', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.drop_column('milling_done_parts')
