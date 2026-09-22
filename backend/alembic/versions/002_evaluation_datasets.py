"""Add versioned evaluation datasets table if it does not already exist."""
from alembic import op

revision = "002_evaluation_datasets"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluation_datasets (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(128) NOT NULL,
            version VARCHAR(64) NOT NULL,
            task_type VARCHAR(64) NOT NULL,
            description TEXT,
            sample_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_project_id "
        "ON evaluation_datasets(project_id)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS evaluation_datasets")
