"""
add_missing_slots.py  (fixed)
------------------------------
Adds the missing time slots to the time_slot table:
  - 8:00 AM - 9:00 AM
  - 12:00 PM - 1:00 PM
  - 1:00 PM - 2:00 PM

FIX: the time_slot table requires start_time and end_time (NOT NULL),
which the previous version of this script didn't provide. This version
sets all three fields.

This is SAFE and additive — it only adds new TimeSlot rows (skipping any
that already exist by name), it does not touch existing timetable entries,
bookings, or any other data. If you already ran the previous version and
got the "8:00 AM - 9:00 AM" slot partially added before it crashed, this
script will detect it already exists and skip it (no duplicate).

HOW TO RUN:
1. Copy this file into D:\\eduspace_backend\\ (overwrite the old one)
2. Open PowerShell in that folder
3. Run: python add_missing_slots.py
4. Refresh the Timetable Manager page — the new slots will appear in the dropdown
"""

from run import app, db, TimeSlot

NEW_SLOTS = [
    ('8:00 AM',  '9:00 AM',  '8:00 AM - 9:00 AM'),
    ('12:00 PM', '1:00 PM',  '12:00 PM - 1:00 PM'),
    ('1:00 PM',  '2:00 PM',  '1:00 PM - 2:00 PM'),
]

def seed():
    with app.app_context():
        added = 0
        for start, end, name in NEW_SLOTS:
            exists = TimeSlot.query.filter_by(slot_name=name).first()
            if exists:
                print(f"Skipping (already exists): {name}")
                continue
            db.session.add(TimeSlot(start_time=start, end_time=end, slot_name=name))
            added += 1
            print(f"Added: {name}")
        db.session.commit()
        print(f"\nDone. {added} new time slot(s) added.")

if __name__ == "__main__":
    seed()
