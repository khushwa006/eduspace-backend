from run import app, db
with app.app_context():
    db.create_all()
    print('✅ Notification tables created!')