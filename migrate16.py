from run import app, db
from sqlalchemy import text

with app.app_context():
    cols = [
        'ALTER TABLE user ADD COLUMN security_failed_attempts INTEGER DEFAULT 0',
        'ALTER TABLE user ADD COLUMN security_lockout_until DATETIME',
        'ALTER TABLE user ADD COLUMN security_locked BOOLEAN DEFAULT 0',
    ]
    with db.engine.connect() as conn:
        for col in cols:
            try:
                conn.execute(text(col))
                conn.commit()
                print(f'✅ {col.split("COLUMN ")[1].split(" ")[0]} added')
            except Exception as e:
                print(f'⚠️  Already exists or error: {e}')
    print('Done!')
