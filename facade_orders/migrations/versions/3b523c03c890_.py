"""Добавлены facade_type и area, обновлены типы колонок

Revision ID: 3b523c03c890
Revises: ab7a97b6a040
Create Date: 2025-07-25 23:07:04.725382
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b523c03c890'
down_revision = 'ab7a97b6a040'
branch_labels = None
depends_on = None


def upgrade():
    # Добавление новых полей
    op.add_column('order', sa.Column('facade_type', sa.String(length=32), nullable=False))
    op.add_column('order', sa.Column('area', sa.Float(), nullable=False))
    op.add_column('order', sa.Column('filenames', sa.Text(), nullable=True))
    op.add_column('order', sa.Column('filepaths', sa.Text(), nullable=True))

    # Изменение типов колонок
    op.alter_column('order', 'order_id',
        existing_type=sa.String(length=50),
        type_=sa.String(length=64),
        existing_nullable=False)

    op.alter_column('order', 'client',
        existing_type=sa.String(length=100),
        type_=sa.String(length=128),
        existing_nullable=False)

    # Удаление устаревших колонок
    op.drop_column('order', 'filename')
    op.drop_column('order', 'filepath')

    op.alter_column('user', 'username',
        existing_type=sa.String(length=80),
        type_=sa.String(length=64),
        existing_nullable=False)

    op.alter_column('user', 'password',
        existing_type=sa.String(length=200),
        type_=sa.String(length=128),
        existing_nullable=False)

    op.alter_column('user', 'role',
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False)


def downgrade():
    # Восстановление старых колонок
    op.add_column('order', sa.Column('filename', sa.String(length=200), nullable=True))
    op.add_column('order', sa.Column('filepath', sa.String(length=300), nullable=True))

    # Откат типов колонок
    op.alter_column('order', 'client',
        existing_type=sa.String(length=128),
        type_=sa.String(length=100),
        existing_nullable=False)

    op.alter_column('order', 'order_id',
        existing_type=sa.String(length=64),
        type_=sa.String(length=50),
        existing_nullable=False)

    op.drop_column('order', 'filepaths')
    op.drop_column('order', 'filenames')
    op.drop_column('order', 'area')
    op.drop_column('order', 'facade_type')

    op.alter_column('user', 'username',
        existing_type=sa.String(length=64),
        type_=sa.String(length=80),
        existing_nullable=False)

    op.alter_column('user', 'password',
        existing_type=sa.String(length=128),
        type_=sa.String(length=200),
        existing_nullable=False)

    op.alter_column('user', 'role',
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False)
