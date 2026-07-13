"""
seed_facilities.py
-------------------
One-off script to seed sample Sports Facility / Library Seat rooms
so the Sports & Library Booking page has data to show.

HOW TO RUN:
1. Copy this file into D:\\eduspace_backend\\ (same folder as run.py)
2. Open PowerShell in that folder
3. Run: python seed_facilities.py
4. Refresh the Sports & Library Booking page in the browser

This is SAFE and additive — it only adds new Room rows, it does not
touch or delete any existing rooms, bookings, or other data.
"""

from run import app, db, Room

FACILITIES = [
    # Sports facilities
    {"name": "Basketball Court 1",   "room_type": "Sports Facility", "building": "Sports Complex", "floor": 0, "capacity": 10},
    {"name": "Football Ground",      "room_type": "Sports Facility", "building": "Sports Complex", "floor": 0, "capacity": 22},
    {"name": "Badminton Court A",    "room_type": "Sports Facility", "building": "Indoor Stadium",  "floor": 1, "capacity": 4},
    {"name": "Badminton Court B",    "room_type": "Sports Facility", "building": "Indoor Stadium",  "floor": 1, "capacity": 4},
    {"name": "Gym Hall",             "room_type": "Sports Facility", "building": "Sports Complex",  "floor": 0, "capacity": 25},

    # Library seats
    {"name": "Library Seat - Block A", "room_type": "Library Seat", "building": "Central Library", "floor": 1, "capacity": 40},
    {"name": "Library Seat - Block B", "room_type": "Library Seat", "building": "Central Library", "floor": 2, "capacity": 40},
    {"name": "Library Quiet Zone",     "room_type": "Library Seat", "building": "Central Library", "floor": 2, "capacity": 20},
]

def seed():
    with app.app_context():
        added = 0
        for f in FACILITIES:
            exists = Room.query.filter_by(name=f["name"]).first()
            if exists:
                print(f"Skipping (already exists): {f['name']}")
                continue
            room = Room(
                name=f["name"],
                room_type=f["room_type"],
                building=f["building"],
                floor=f["floor"],
                capacity=f["capacity"],
                current_occupancy=0,
            )
            db.session.add(room)
            added += 1
            print(f"Added: {f['name']} ({f['room_type']})")
        db.session.commit()
        print(f"\nDone. {added} new facility room(s) added.")

if __name__ == "__main__":
    seed()
