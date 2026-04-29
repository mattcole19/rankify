"""Create MVP ranking schema.

Revision ID: 20260428_01
Revises:
Create Date: 2026-04-28 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260428_01'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)

    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_items_category_id'), 'items', ['category_id'], unique=False)

    op.create_table(
        'ranking_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('anon_id', sa.String(length=80), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_ranking_submissions_category_id'),
        'ranking_submissions',
        ['category_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_ranking_submissions_anon_id'), 'ranking_submissions', ['anon_id'], unique=False
    )

    op.create_table(
        'ranking_entries',
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_id'], ['ranking_submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('submission_id', 'item_id'),
        sa.UniqueConstraint('submission_id', 'rank', name='uq_ranking_entries_submission_rank'),
    )


def downgrade() -> None:
    op.drop_table('ranking_entries')
    op.drop_index(op.f('ix_ranking_submissions_anon_id'), table_name='ranking_submissions')
    op.drop_index(op.f('ix_ranking_submissions_category_id'), table_name='ranking_submissions')
    op.drop_table('ranking_submissions')
    op.drop_index(op.f('ix_items_category_id'), table_name='items')
    op.drop_table('items')
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.drop_table('categories')
