from alembic import op
from app.db.session import Base
import app.models  # noqa: F401
revision='001_initial'; down_revision=None; branch_labels=None; depends_on=None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
