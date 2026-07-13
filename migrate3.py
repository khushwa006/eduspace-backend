from run import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(text('DROP TABLE IF EXISTS lost_found_item'))
        conn.commit()
    db.create_all()
    print('✅ Done!')