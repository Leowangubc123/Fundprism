"""fix tags schema

Revision ID: 3cfabecc9c3a
Revises: 3e4014ca9bad
Create Date: 2026-08-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cfabecc9c3a'
down_revision: Union[str, None] = '3e4014ca9bad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect != 'postgresql':
        return

    op.execute(sa.text("""
        ALTER TABLE tags
        ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_tags_category ON tags(category);
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS fund_tags (
            fund_id UUID NOT NULL,
            tag_id UUID NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (fund_id, tag_id),
            CONSTRAINT fk_fund_tags_fund_id FOREIGN KEY (fund_id) REFERENCES funds(id),
            CONSTRAINT fk_fund_tags_tag_id FOREIGN KEY (tag_id) REFERENCES tags(id),
            CONSTRAINT uq_fund_tag UNIQUE (fund_id, tag_id)
        );
    """))


def downgrade() -> None:
    pass
