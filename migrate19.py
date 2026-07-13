"""
migrate19.py
------------
Creates the new holiday table (admin-declared non-working dates).
Used by the attendance window calculation to correctly find the
"next working day" deadline — skipping Sundays and any holidays added here.

This is a brand-new table — it does NOT touch any existing data.

HOW TO RUN:
1. Copy this file into D:\\eduspace_backend\\ (same folder as run.py)
2. Make sure you've already replaced run.py with the latest version
3. Open PowerShell in that folder
4. Run: python migrate19.py
5. Restart Flask: python run.py
"""

from run import app, db

def migrate():
    with app.app_context():
        db.create_all()  # only creates tables that don't exist yet — safe
        print("✅ holiday table created (or already existed).")

if __name__ == "__main__":
    migrate()
