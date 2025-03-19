from app.database import sync_engine
import sqlalchemy as sa

def main():
    with sync_engine.connect() as conn:
        try:
            result = conn.execute(sa.text('SELECT * FROM tasks'))
            rows = result.fetchall()
            if rows:
                print(f"Found {len(rows)} tasks:")
                for row in rows:
                    print(f"  - Task ID: {row.task_id}, Name: {row.task_name}, Status: {row.status}")
            else:
                print('No tasks found')
                
            # Check if the table exists
            result = conn.execute(sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tasks')"))
            table_exists = result.scalar()
            print(f"Tasks table exists: {table_exists}")
            
        except Exception as e:
            print(f"Error querying database: {str(e)}")

if __name__ == "__main__":
    main() 