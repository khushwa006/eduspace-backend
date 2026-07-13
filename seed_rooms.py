"""
Seed sample rooms into database
Save to: seed_rooms.py (in project root: C:\Users\DELL\eduspace_backend\)
Run with: python seed_rooms.py
"""
from app import create_app, db
from app.models.room import Room

app = create_app()

with app.app_context():
    # Clear existing rooms
    Room.query.delete()
    
    # Create sample rooms
    rooms = [
        Room(name="Lab A-101", room_type="Lab", capacity=40, floor="A1", building="Building A"),
        Room(name="Lab B-204", room_type="Lab", capacity=35, floor="B2", building="Building B"),
        Room(name="Hall C-301", room_type="Lecture Hall", capacity=80, floor="C3", building="Building C"),
        Room(name="Hall D-102", room_type="Lecture Hall", capacity=100, floor="D1", building="Building D"),
        Room(name="Study Pod S-01", room_type="Study Pod", capacity=6, floor="S0", building="Study Area"),
        Room(name="Study Pod S-02", room_type="Study Pod", capacity=6, floor="S0", building="Study Area"),
        Room(name="Meeting Room E-205", room_type="Meeting Room", capacity=20, floor="E2", building="Building E"),
        Room(name="Computer Lab F-103", room_type="Lab", capacity=45, floor="F1", building="Building F"),
    ]
    
    for room in rooms:
        db.session.add(room)
    
    db.session.commit()
    print(f"✅ Created {len(rooms)} sample rooms")
