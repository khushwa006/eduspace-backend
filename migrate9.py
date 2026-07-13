from run import app, db
from sqlalchemy import text

with app.app_context():
    cols = [
        'ALTER TABLE user ADD COLUMN enrollment_no VARCHAR(50)',
        'ALTER TABLE user ADD COLUMN program VARCHAR(100)',
        'ALTER TABLE user ADD COLUMN batch_year VARCHAR(20)',
        'ALTER TABLE user ADD COLUMN section VARCHAR(10)',
        'ALTER TABLE user ADD COLUMN bio TEXT',
    ]
    with db.engine.connect() as conn:
        for col in cols:
            try:
                conn.execute(text(col))
                conn.commit()
                print(f'✅ {col.split("COLUMN ")[1].split(" ")[0]} added')
            except Exception as e:
                print(f'⚠️  Already exists: {e}')
    print('Done!')