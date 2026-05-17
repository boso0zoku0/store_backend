"""UsersProducts change

Revision ID: ed357894f7e7
Revises: 02abb6cedfcd
Create Date: 2026-03-22 19:09:26.010844

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ed357894f7e7"
down_revision: Union[str, Sequence[str], None] = "02abb6cedfcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Удаляем старый составной первичный ключ
    op.drop_constraint("usersproducts_pkey", "usersproducts", type_="primary")

    # 2. Добавляем новую колонку id
    op.add_column(
        "usersproducts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
    )

    # 3. Добавляем новую колонку quantity
    op.add_column(
        "usersproducts",
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
    )

    # 4. Делаем id первичным ключом
    op.create_primary_key("usersproducts_pkey", "usersproducts", ["id"])


def downgrade() -> None:
    # 1. Удаляем новый первичный ключ
    op.drop_constraint("usersproducts_pkey", "usersproducts", type_="primary")

    # 2. Удаляем колонки
    op.drop_column("usersproducts", "quantity")
    op.drop_column("usersproducts", "id")

    # 3. Восстанавливаем старый составной первичный ключ
    op.create_primary_key(
        "usersproducts_pkey", "usersproducts", ["users_id", "products_id"]
    )
