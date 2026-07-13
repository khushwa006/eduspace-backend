from run import app, db
from sqlalchemy import text

with app.app_context():
    # Add two_fa_enabled column to user table
    try:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE user ADD COLUMN two_fa_enabled BOOLEAN DEFAULT 0'))
            conn.commit()
        print('✅ two_fa_enabled column added!')
    except Exception as e:
        print('⚠️  Already exists or error:', e)

    # Create OTPCode table (and any other missing tables)
    db.create_all()
    print('✅ OTPCode table created!')
