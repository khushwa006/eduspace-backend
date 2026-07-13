"""
migrate20.py
------------
Creates the new login_activity and activity_log tables, used for the
"last login / login history / recent activity" feature on the account page.

These are brand-new tables — they do NOT touch any existing data.

HOW TO RUN:
1. Copy this file into D:\\eduspace_backend\\ (same folder as run.py)
2. Make sure you've already replaced run.py with the latest version
3. Open PowerShell in that folder
4. Run: python migrate20.py
5. Restart Flask: python run.py
"""

from run import app, db

def migrate():
    with app.app_context():
        db.create_all()  # only creates tables that don't exist yet — safe
        print("✅ login_activity and activity_log tables created (or already existed).")

if __name__ == "__main__":
    migrate()
