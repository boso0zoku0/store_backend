"""transferring data to the filters_new column and then deleting the old filters column

Revision ID: b3ebfca91757
Revises: f884ffd67d7e
Create Date: 2026-07-18 16:24:35.244094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b3ebfca91757'
down_revision: Union[str, Sequence[str], None] = 'f884ffd67d7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Добавляем новую колонку
    op.add_column('products', sa.Column('filters_new', JSONB(), nullable=True))

    # 2. Переносим данные из filters в filters_new
    op.execute(text("""
        UPDATE products
        SET filters_new = jsonb_build_object(
            'category', COALESCE(filters->'categories'->>0, ''),
            'colors', COALESCE(filters->'colors'->>0, ''),
            'volume', CASE
                WHEN filters->'volume' IS NOT NULL
                     AND filters->'volume'->>0 IS NOT NULL
                THEN (filters->'volume'->>0)::integer
                ELSE NULL
            END,
            'in_stock', CASE
                WHEN filters->'in_stock' IS NOT NULL
                THEN (filters->>'in_stock')::boolean
                ELSE NULL
            END
        )
        WHERE filters IS NOT NULL;
    """))

    # 3. Удаляем старую колонку
    op.drop_column('products', 'filters')

    # 4. Переименовываем новую колонку в filters
    op.alter_column('products', 'filters_new', new_column_name='filters')


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Переименовываем обратно
    op.alter_column('products', 'filters', new_column_name='filters_old')

    # 2. Создаём старую колонку filters
    op.add_column('products', sa.Column('filters', sa.JSON(), nullable=True))

    # 3. Восстанавливаем данные (приблизительно)
    op.execute(text("""
        UPDATE products
        SET filters = jsonb_build_object(
            'categories', jsonb_build_array(filters_old->>'category'),
            'colors', jsonb_build_array(filters_old->>'colors'),
            'price_range', jsonb_build_array(0, 50000),
            'volume', CASE
                WHEN filters_old->'volume' IS NOT NULL
                THEN jsonb_build_array(filters_old->>'volume', 0)
                ELSE jsonb_build_array(0, 0)
            END,
            'in_stock', COALESCE((filters_old->>'in_stock')::boolean, true)
        )
        WHERE filters_old IS NOT NULL;
    """))

    # 4. Удаляем временную колонку
    op.drop_column('products', 'filters_old')
