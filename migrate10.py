from run import app, db
from sqlalchemy import text

with app.app_context():
    try:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE user ADD COLUMN profile_photo TEXT'))
            conn.commit()
        print('✅ profile_photo column added!')
    except Exception as e:
        print('⚠️  Already exists or error:', e)
