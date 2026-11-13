"""phase3_agent_and_academic_schema

Revision ID: c85ad759c2dc
Revises: 6c35c15ef630
Create Date: 2026-11-13 21:52:21.224613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c85ad759c2dc'
down_revision: Union[str, Sequence[str], None] = '6c35c15ef630'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('academic_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('institution', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('assessment_type', sa.String(length=100), server_default='assessment', nullable=False))
        batch_op.add_column(sa.Column('marks_obtained', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('max_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('result_status', sa.String(length=30), server_default='available', nullable=False))
        batch_op.add_column(sa.Column('assessment_date', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('provenance', sa.JSON(), nullable=True))
        batch_op.alter_column('term',
               existing_type=sa.VARCHAR(length=50),
               server_default='Current',
               nullable=False)
        batch_op.drop_constraint('uq_academic_record_entry', type_='unique')
        batch_op.create_unique_constraint('uq_academic_record_entry', ['user_id', 'subject_code', 'term', 'assessment_type'])
        batch_op.drop_column('score')
        batch_op.drop_column('raw_source')
        batch_op.drop_column('component')
        batch_op.drop_column('max_score')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('academic_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_score', sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column('component', sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(sa.Column('raw_source', sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column('score', sa.FLOAT(), nullable=True))
        batch_op.drop_constraint('uq_academic_record_entry', type_='unique')
        batch_op.create_unique_constraint('uq_academic_record_entry', ['user_id', 'subject_code', 'term', 'component'])
        batch_op.alter_column('term',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
        batch_op.drop_column('provenance')
        batch_op.drop_column('source')
        batch_op.drop_column('assessment_date')
        batch_op.drop_column('result_status')
        batch_op.drop_column('max_marks')
        batch_op.drop_column('marks_obtained')
        batch_op.drop_column('assessment_type')
        batch_op.drop_column('institution')
