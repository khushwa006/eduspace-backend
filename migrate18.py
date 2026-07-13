"""
migrate18.py
------------
Creates the new class_attendance table (used by the redesigned
timetable-based attendance system). This is a brand-new table — it does
NOT touch the old Attendance table (booking-based) or any existing data.

HOW TO RUN:
1. Copy this file into D:\\eduspace_backend\\ (same folder as run.py)
2. Make sure you've already replaced run.py with the latest version
3. Open PowerShell in that folder
4. Run: python migrate18.py
5. Restart Flask: python run.py
"""

from run import app, db

def migrate():
    with app.app_context():
        db.create_all()  # only creates tables that don't exist yet — safe
        print("✅ class_attendance table created (or already existed).")

if __name__ == "__main__":
    migrate()
