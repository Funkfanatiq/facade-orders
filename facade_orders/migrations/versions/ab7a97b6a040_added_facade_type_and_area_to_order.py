"""Added facade_type and area to Order

Revision ID: ab7a97b6a040
Revises: c9c51bcd82f6
Create Date: 2025-07-25 00:39:39.376922
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ab7a97b6a040'
down_revision = 'c9c51bcd82f6'
branch_labels = None
depends_on = None


def upgrade():
    # Изменения в таблице order
    op.add_column('order', sa.Column('facade_type', sa.String(length=32), nullable=True))
    op.add_column('order', sa.Column('area', sa.Float(), nullable=True))

    op.alter_column('order', 'order_id',
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=64),
        existing_nullable=False)

    op.alter_column('order', 'client',
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=128),
        existing_nullable=False)

    op.alter_column('order', 'days',
        existing_type=sa.INTEGER(),
        existing_nullable=False)

    op.alter_column('order', 'due_date',
        existing_type=sa.DATE(),
        existing_nullable=False)

    # Изменения в таблице user
    op.alter_column('user', 'username',
        existing_type=sa.VARCHAR(length=80),
        type_=sa.String(length=64),
        existing_nullable=False)

    op.alter_column('user', 'password',
        existing_type=sa.VARCHAR(length=200),
        type_=sa.String(length=128),
        existing_nullable=False)

    op.alter_column('user', 'role',
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=32),
        existing_nullable=False)


def downgrade():
    # Восстанавливаем поля
    op.drop_column('order', 'area')
    op.drop_column('order', 'facade_type')

    op.alter_column('order', 'due_date',
        existing_type=sa.DATE(),
        existing_nullable=True)

    op.alter_column('order', 'days',
        existing_type=sa.INTEGER(),
        existing_nullable=True)

    op.alter_column('order', 'client',
        existing_type=sa.String(length=128),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True)

    op.alter_column('order', 'order_id',
        existing_type=sa.String(length=64),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True)

    op.alter_column('user', 'username',
        existing_type=sa.String(length=64),
        type_=sa.VARCHAR(length=80),
        existing_nullable=True)

    op.alter_column('user', 'password',
        existing_type=sa.String(length=128),
        type_=sa.VARCHAR(length=200),
        existing_nullable=True)

    op.alter_column('user', 'role',
        existing_type=sa.String(length=32),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True)

    # Восстанавливаем таблицу task
    op.create_table('task',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('title', sa.VARCHAR(length=100), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('due_date', sa.DATE(), nullable=True),
        sa.Column('status', sa.VARCHAR(length=50), nullable=True),
        sa.Column('created_at', sa.DATETIME(), nullable=True),
        sa.Column('updated_at', sa.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
