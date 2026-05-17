"""Products change; add field status product

Revision ID: c3154e775dd7
Revises: 6867fe002307
Create Date: 2026-03-30 18:02:18.498713

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3154e775dd7"
down_revision: Union[str, Sequence[str], None] = "6867fe002307"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Сначала создаём ENUM тип
    op.execute(
        "CREATE TYPE product_status AS ENUM('processing', 'moving', 'completed', 'cancelled', 'none')"
    )

    # 2. Теперь добавляем колонку с этим типом
    op.add_column(
        "usersproducts",
        sa.Column(
            "status",
            postgresql.ENUM(
                "processing",
                "moving",
                "completed",
                "cancelled",
                "none",
                name="product_status",
                create_type=False,
            ),
            nullable=True,
        ),
    )


def downgrade():
    # Удаляем колонку
    op.drop_column("usersproducts", "status")
    # Удаляем ENUM тип
    op.execute("DROP TYPE product_status")
