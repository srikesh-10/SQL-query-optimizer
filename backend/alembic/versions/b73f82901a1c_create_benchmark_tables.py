"""create_benchmark_tables

Revision ID: b73f82901a1c
Revises: 461c50813f0a
Create Date: 2026-10-21 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b73f82901a1c'
down_revision: Union[str, Sequence[str], None] = '461c50813f0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add benchmark history tables."""
    op.create_table(
        'benchmarks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sql', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('requested_repetitions', sa.Integer(), nullable=False),
        sa.Column('successful_runs', sa.Integer(), nullable=False),
        sa.Column('failed_runs', sa.Integer(), nullable=False),
        sa.Column('median_execution_time_ms', sa.Float(), nullable=True),
        sa.Column('median_planning_time_ms', sa.Float(), nullable=True),
        sa.Column('estimated_total_cost', sa.Float(), nullable=True),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmarks_created_at'), 'benchmarks', ['created_at'], unique=False)

    op.create_table(
        'benchmark_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('benchmark_id', sa.String(length=36), nullable=False),
        sa.Column('run_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.Column('planning_time_ms', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('plan_rows', sa.Float(), nullable=True),
        sa.Column('actual_rows', sa.Float(), nullable=True),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['benchmark_id'], ['benchmarks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_runs_benchmark_id'), 'benchmark_runs', ['benchmark_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema to drop benchmark history tables."""
    op.drop_index(op.f('ix_benchmark_runs_benchmark_id'), table_name='benchmark_runs')
    op.drop_table('benchmark_runs')
    op.drop_index(op.f('ix_benchmarks_created_at'), table_name='benchmarks')
    op.drop_table('benchmarks')
