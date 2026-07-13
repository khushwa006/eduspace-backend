"""
migrate17.py
------------
Adds seat_numbers and group_size columns to the facility_booking table,
needed for individual library seat selection + group study bookings (max 4 seats).

This is ADDITIVE and SAFE — it does not touch or delete any existing data.

HOW TO RUN:
1. Copy this file into D:\\eduspace_backend\\ (same folder as run.py)
2. Stop Flask if it's running (Ctrl+C)
3. Open PowerShell in that folder
4. Run: python migrate17.py
5. Restart Flask: python run.py
"""

import sqlite3
import os

DB_PATH = os.path.join('instance', 'eduspace.db')

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}. Run this from the eduspace_backend folder.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not column_exists(cursor, 'facility_booking', 'seat_numbers'):
        cursor.execute("ALTER TABLE facility_booking ADD COLUMN seat_numbers VARCHAR(50)")
        print("✅ Added column: facility_booking.seat_numbers")
    else:
        print("ℹ️  Column facility_booking.seat_numbers already exists, skipping.")

    if not column_exists(cursor, 'facility_booking', 'group_size'):
        cursor.execute("ALTER TABLE facility_booking ADD COLUMN group_size INTEGER DEFAULT 1")
        print("✅ Added column: facility_booking.group_size")
    else:
        print("ℹ️  Column facility_booking.group_size already exists, skipping.")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete.")

if __name__ == "__main__":
    migrate()
