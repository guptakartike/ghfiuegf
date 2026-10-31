"""create matched hourly observations table

Revision ID: 371342e15e05
Revises: 00147372cffd
Create Date: 2026-10-31 02:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '371342e15e05'
down_revision: Union[str, Sequence[str], None] = '00147372cffd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'matched_hourly_observations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('delivery_time', sa.DateTime(timezone=True), nullable=False, comment='Start of the delivery hour in UTC'),
        sa.Column('forecast_publish_time', sa.DateTime(timezone=True), nullable=False, comment='Publication timestamp of the selected forecast version in UTC'),
        sa.Column('forecast_generation', sa.Float(), nullable=False, comment='Forecast wind generation in MW'),
        sa.Column('actual_generation', sa.Float(), nullable=False, comment='Aggregated hourly average actual wind generation in MW'),
        sa.Column('forecast_error', sa.Float(), nullable=False, comment='Forecast error in MW: forecast_generation - actual_generation'),
        sa.Column('cutoff_time', sa.DateTime(timezone=True), nullable=False, comment='Decision cutoff timestamp applied for version eligibility in UTC'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('delivery_time', 'cutoff_time', name='uq_matched_delivery_cutoff'),
    )
    op.create_index('ix_matched_delivery_cutoff', 'matched_hourly_observations', ['delivery_time', 'cutoff_time'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_matched_delivery_cutoff', table_name='matched_hourly_observations')
    op.drop_table('matched_hourly_observations')
