"""
seed_indian_holidays_2026.py
-----------------------------
Seeds the holiday table with India's official 2026 Gazetted Holidays
(the mandatory ones observed by Central Government offices — Republic Day,
major festivals, Independence Day, etc.). Source: Govt. of India gazetted
holiday list for 2026.

This is SAFE and additive — it skips any date that's already in the table
(e.g. if you already added something manually for that date), and does not
touch any other data.

After running this, the admin can still add/edit/remove holidays normally
from the Admin → Holidays tab (e.g. to add region-specific or
institution-specific closures on top of this base list).

NOTE: A few 2026 festival dates (Id-ul-Fitr, Id-ul-Zuha/Bakrid, Muharram,
Id-e-Milad) are lunar-calendar based and officially "tentative" — confirm
closer to the date and adjust via the admin UI if the date shifts by a day.

HOW TO RUN:
1. Make sure migrate19.py has already been run (creates the holiday table)
2. Copy this file into D:\\eduspace_backend\\ (same folder as run.py)
3. Open PowerShell in that folder
4. Run: python seed_indian_holidays_2026.py
5. Restart Flask, refresh any Holidays page to see them
"""

from run import app, db, Holiday
from datetime import date

HOLIDAYS_2026 = [
    (date(2026, 1, 26),  "Republic Day"),
    (date(2026, 3, 4),   "Holi"),
    (date(2026, 3, 21),  "Id-ul-Fitr (Tentative)"),
    (date(2026, 3, 26),  "Ram Navami"),
    (date(2026, 3, 31),  "Mahavir Jayanti"),
    (date(2026, 4, 3),   "Good Friday"),
    (date(2026, 5, 1),   "Buddha Purnima"),
    (date(2026, 5, 27),  "Id-ul-Zuha / Bakrid (Tentative)"),
    (date(2026, 6, 26),  "Muharram (Tentative)"),
    (date(2026, 8, 15),  "Independence Day"),
    (date(2026, 8, 26),  "Id-e-Milad (Tentative)"),
    (date(2026, 9, 4),   "Janmashtami"),
    (date(2026, 10, 2),  "Mahatma Gandhi Jayanti"),
    (date(2026, 10, 20), "Dussehra"),
    (date(2026, 11, 8),  "Diwali (Deepavali)"),
    (date(2026, 11, 24), "Guru Nanak Jayanti"),
    (date(2026, 12, 25), "Christmas Day"),
]

def seed():
    with app.app_context():
        added = 0
        for d, name in HOLIDAYS_2026:
            if Holiday.query.filter_by(date=d).first():
                print(f"Skipping (already exists): {d} — {name}")
                continue
            db.session.add(Holiday(date=d, name=name))
            added += 1
            print(f"Added: {d} — {name}")
        db.session.commit()
        print(f"\nDone. {added} new holiday(s) added.")

if __name__ == "__main__":
    seed()
