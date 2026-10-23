"""add document source_type

Revision ID: 5b1e2c7d9a40
Revises: 092632cfcdfe
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '5b1e2c7d9a40'
down_revision: Union[str, Sequence[str], None] = '092632cfcdfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill existing rows as 'file' (only the corpus CLI wrote rows before this), then drop the default.
    op.add_column('documents', sa.Column('source_type', sa.String(length=16), nullable=False, server_default='file'))
    op.alter_column('documents', 'source_type', server_default=None)
    op.create_index('ix_documents_created_at', 'documents', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_documents_created_at', table_name='documents')
    op.drop_column('documents', 'source_type')
