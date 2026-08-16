"""ensure tags and fund_tags tables

Revision ID: 3e4014ca9bad
Revises: f43c4fe4707c
Create Date: 2026-08-16 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '3e4014ca9bad'
down_revision: Union[str, None] = 'f43c4fe4707c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names())

    if 'tags' not in existing:
        op.create_table(
            'tags',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('category', sa.String(length=32), nullable=False),
            sa.Column('sort_order', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
        )
        op.create_index(
            op.f('ix_tags_category'),
            'tags',
            ['category'],
            unique=False,
        )

    if 'fund_tags' not in existing:
        op.create_table(
            'fund_tags',
            sa.Column('fund_id', sa.UUID(), nullable=False),
            sa.Column('tag_id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['fund_id'], ['funds.id']),
            sa.ForeignKeyConstraint(['tag_id'], ['tags.id']),
            sa.PrimaryKeyConstraint('fund_id', 'tag_id'),
            sa.UniqueConstraint('fund_id', 'tag_id', name='uq_fund_tag'),
        )


def downgrade() -> None:
    op.drop_table('fund_tags')
    op.drop_index(op.f('ix_tags_category'), table_name='tags')
    op.drop_table('tags')
