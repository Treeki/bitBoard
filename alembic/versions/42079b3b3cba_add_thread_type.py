"""add thread type

Revision ID: 42079b3b3cba
Revises: 11596c16fcfa
Create Date: 2013-07-14 05:54:40.543954

"""

# revision identifiers, used by Alembic.
revision = '42079b3b3cba'
down_revision = '11596c16fcfa'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

def get_temp_table():
	return sql.table('threads',
		sql.column('type', sa.Integer),
		sql.column('is_private', sa.Boolean)
		)


def upgrade():
	op.add_column(u'threads',
		sa.Column('type', sa.Integer(), server_default='1', nullable=False))

	temp_table = get_temp_table()

	op.execute(
		temp_table.update().\
		where(temp_table.c.is_private == True).\
		values({'type': op.inline_literal(2)})
		)

	op.drop_column(u'threads', u'is_private')


def downgrade():
	op.add_column(u'threads',
		sa.Column(u'is_private', sa.Boolean(), nullable=True))

	temp_table = get_temp_table()

	op.execute(
		temp_table.update().\
			values({'is_private': op.inline_literal(False)})
		)

	op.execute(
		temp_table.update().\
			where(temp_table.c.type == op.inline_literal(2)).\
			values({'is_private': op.inline_literal(True)})
		)

	op.drop_column(u'threads', 'type')
