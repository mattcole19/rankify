"""Add category versioning fields.

Revision ID: 20260506_01
Revises: 20260428_01
Create Date: 2026-05-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260506_01'
down_revision: str | None = '20260428_01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'categories',
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'categories',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='published'),
    )

    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=False)
    op.create_unique_constraint(
        'uq_categories_slug_version',
        'categories',
        ['slug', 'version_number'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_categories_slug_version', 'categories', type_='unique')
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)

    op.drop_column('categories', 'status')
    op.drop_column('categories', 'version_number')
