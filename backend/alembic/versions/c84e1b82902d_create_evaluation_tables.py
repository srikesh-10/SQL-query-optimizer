"""create_evaluation_tables

Revision ID: c84e1b82902d
Revises: b73f82901a1c
Create Date: 2026-10-21 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c84e1b82902d'
down_revision: Union[str, Sequence[str], None] = 'b73f82901a1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add evaluation history table."""
    op.create_table(
        'evaluations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('original_sql', sa.Text(), nullable=False),
        sa.Column('candidate_sql', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('correctness_status', sa.String(length=50), nullable=False),
        sa.Column('is_complete_comparison', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('original_row_count', sa.Integer(), nullable=True),
        sa.Column('candidate_row_count', sa.Integer(), nullable=True),
        sa.Column('original_median_execution_time_ms', sa.Float(), nullable=True),
        sa.Column('candidate_median_execution_time_ms', sa.Float(), nullable=True),
        sa.Column('runtime_difference_ms', sa.Float(), nullable=True),
        sa.Column('percentage_improvement', sa.Float(), nullable=True),
        sa.Column('original_total_cost', sa.Float(), nullable=True),
        sa.Column('candidate_total_cost', sa.Float(), nullable=True),
        sa.Column('performance_assessment', sa.String(length=50), nullable=False),
        sa.Column('recommendation', sa.String(length=50), nullable=False),
        sa.Column('recommendation_rationale', sa.Text(), nullable=False),
        sa.Column('original_benchmark_id', sa.String(length=36), nullable=True),
        sa.Column('candidate_benchmark_id', sa.String(length=36), nullable=True),
        sa.Column('requested_repetitions', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('successful_runs', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('failed_runs', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluations_created_at'), 'evaluations', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema to drop evaluation history table."""
    op.drop_index(op.f('ix_evaluations_created_at'), table_name='evaluations')
    op.drop_table('evaluations')
