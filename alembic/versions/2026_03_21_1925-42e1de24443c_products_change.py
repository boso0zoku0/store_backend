"""Products change

Revision ID: 42e1de24443c
Revises: 125b4c3bb6a7
Create Date: 2026-03-21 19:25:38.799361

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42e1de24443c"
down_revision: Union[str, Sequence[str], None] = "125b4c3bb6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    pass
