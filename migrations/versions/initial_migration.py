"""Initial database setup for task tracking

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2023-03-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, ENUM

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types in PostgreSQL
    op.execute(
        "CREATE TYPE task_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')"
    )
    op.execute(
        "CREATE TYPE service_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')"
    )
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('task_id', sa.String(length=36), nullable=False, unique=True),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='task_status'), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_task_id'), 'tasks', ['task_id'], unique=True)
    op.create_index(op.f('ix_tasks_created_at'), 'tasks', ['created_at'], unique=False)
    
    # Create service_requests table
    op.create_table(
        'service_requests',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('service_name', sa.String(length=255), nullable=False),
        sa.Column('scenario_id', sa.String(length=36), nullable=True),
        sa.Column('business_type_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='service_status'), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('request_payload', sa.JSON(), nullable=True),
        sa.Column('response_payload', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.task_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_requests_task_id'), 'service_requests', ['task_id'], unique=False)
    op.create_index(op.f('ix_service_requests_created_at'), 'service_requests', ['created_at'], unique=False)
    op.create_index(op.f('ix_service_requests_service_name'), 'service_requests', ['service_name'], unique=False)
    
    # Create function to update updated_at timestamp
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """)
    
    # Create trigger on tasks table
    op.execute("""
    CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create trigger on service_requests table
    op.execute("""
    CREATE TRIGGER update_service_requests_updated_at
    BEFORE UPDATE ON service_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks")
    op.execute("DROP TRIGGER IF EXISTS update_service_requests_updated_at ON service_requests")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop tables
    op.drop_table('service_requests')
    op.drop_table('tasks')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS service_status")
    op.execute("DROP TYPE IF EXISTS task_status") 