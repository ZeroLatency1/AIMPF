"""Add persisted experiment result payload.

Revision ID: 003_experiment_results
Revises: 002_evaluation_datasets
"""
from alembic import op
import sqlalchemy as sa

revision = "003_experiment_results"
down_revision = "002_evaluation_datasets"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("experiments")}
    if "result_json" not in columns:
        op.add_column("experiments", sa.Column("result_json", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("experiments")}
    if "result_json" in columns:
        op.drop_column("experiments", "result_json")
