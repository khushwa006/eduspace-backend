from run import app, db

with app.app_context():
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE student_feedback ADD COLUMN feedback_type VARCHAR(50) DEFAULT "general_suggestion"'))
            conn.execute(db.text('ALTER TABLE student_feedback ADD COLUMN is_anonymous BOOLEAN DEFAULT 0'))
            conn.commit()
        print('✅ Columns added successfully!')
    except Exception as e:
        print('ℹ️ Result:', e)