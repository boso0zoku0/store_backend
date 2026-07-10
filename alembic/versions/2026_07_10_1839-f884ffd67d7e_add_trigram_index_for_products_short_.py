"""add_trigram_index_for_products_short_name

Revision ID: f884ffd67d7e
Revises: 64663266c456
Create Date: 2026-07-10 18:39:09.801373

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f884ffd67d7e"
down_revision: Union[str, Sequence[str], None] = "64663266c456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_products_short_name_trgm
        ON products USING GIN (short_name gin_trgm_ops);
    """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_products_short_name_trgm;")
