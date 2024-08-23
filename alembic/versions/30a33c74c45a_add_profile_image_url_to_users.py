"""Add profile_image_url to users

Revision ID: 30a33c74c45a
Revises: 773fb373ab23
Create Date: 2024-08-22 02:56:55.979086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30a33c74c45a'
down_revision: Union[str, None] = '773fb373ab23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('profile_image_url', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'profile_image_url')

