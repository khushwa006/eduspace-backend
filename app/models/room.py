"""
Room Model - Save to: app/models/room.py
"""
from app import db
from datetime import datetime

class Room(db.Model):
    __tablename__ = "rooms"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    room_type = db.Column(db.String(50))  # Lab, Lecture Hall, Study Pod
    capacity = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.String(10))
    building = db.Column(db.String(50))
    qr_code = db.Column(db.String(500))  # QR code data
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.room_type,
            "capacity": self.capacity,
            "floor": self.floor,
            "building": self.building,
            "qr_code": self.qr_code,
            "is_active": self.is_active
        }
    
    def __repr__(self):
        return f"<Room {self.name}>"

class Occupancy(db.Model):
    __tablename__ = "occupancy"
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    check_out_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    
    room = db.relationship("Room", backref="occupancy_records")
    user = db.relationship("User", backref="occupancy_records")
    
    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
            "check_out_time": self.check_out_time.isoformat() if self.check_out_time else None,
            "duration_minutes": self.duration_minutes
        }
    
    def __repr__(self):
        return f"<Occupancy User {self.user_id} in Room {self.room_id}>"
