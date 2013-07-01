"""Forum.description is now UnicodeText

Revision ID: 11596c16fcfa
Revises: None
Create Date: 2013-07-01 04:41:38.838820

"""

# revision identifiers, used by Alembic.
revision = '11596c16fcfa'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
	op.alter_column('forums', 'description', type_=sa.UnicodeText)

def downgrade():
	op.alter_column('forums', 'description', type_=sa.Text)
