"""
Room Routes - Save to: app/routes/rooms.py
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.room import Room, Occupancy
from app.models.user import User
from datetime import datetime

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

# Get all rooms
@rooms_bp.route("", methods=["GET"])
def get_all_rooms():
    try:
        rooms = Room.query.filter_by(is_active=True).all()
        return jsonify({
            "msg": "Rooms retrieved successfully",
            "count": len(rooms),
            "rooms": [room.to_dict() for room in rooms]
        }), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Get single room
@rooms_bp.route("/<int:room_id>", methods=["GET"])
def get_room(room_id):
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({"msg": "Room not found"}), 404
        
        # Get current occupancy
        current_occupancy = Occupancy.query.filter_by(
            room_id=room_id,
            check_out_time=None
        ).count()
        
        room_data = room.to_dict()
        room_data["current_occupancy"] = current_occupancy
        room_data["available_seats"] = room.capacity - current_occupancy
        room_data["occupancy_percentage"] = (current_occupancy / room.capacity * 100) if room.capacity > 0 else 0
        
        return jsonify(room_data), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Check-in to room
@rooms_bp.route("/<int:room_id>/checkin", methods=["POST"])
@jwt_required()
def checkin_room(room_id):
    try:
        user_id = get_jwt_identity()
        
        room = Room.query.get(room_id)
        if not room:
            return jsonify({"msg": "Room not found"}), 404
        
        # Check if user already checked in
        existing = Occupancy.query.filter_by(
            room_id=room_id,
            user_id=user_id,
            check_out_time=None
        ).first()
        
        if existing:
            return jsonify({"msg": "User already checked in to this room"}), 409
        
        # Create check-in record
        occupancy = Occupancy(room_id=room_id, user_id=user_id)
        db.session.add(occupancy)
        db.session.commit()
        
        return jsonify({
            "msg": "Checked in successfully",
            "occupancy": occupancy.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Check-out from room
@rooms_bp.route("/<int:room_id>/checkout", methods=["POST"])
@jwt_required()
def checkout_room(room_id):
    try:
        user_id = get_jwt_identity()
        
        occupancy = Occupancy.query.filter_by(
            room_id=room_id,
            user_id=user_id,
            check_out_time=None
        ).first()
        
        if not occupancy:
            return jsonify({"msg": "No active check-in found"}), 404
        
        # Calculate duration
        occupancy.check_out_time = datetime.utcnow()
        duration = occupancy.check_out_time - occupancy.check_in_time
        occupancy.duration_minutes = int(duration.total_seconds() / 60)
        
        db.session.commit()
        
        return jsonify({
            "msg": "Checked out successfully",
            "occupancy": occupancy.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Get room occupancy
@rooms_bp.route("/<int:room_id>/occupancy", methods=["GET"])
def get_occupancy(room_id):
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({"msg": "Room not found"}), 404
        
        current_occupancy = Occupancy.query.filter_by(
            room_id=room_id,
            check_out_time=None
        ).count()
        
        return jsonify({
            "room_id": room_id,
            "room_name": room.name,
            "capacity": room.capacity,
            "current_occupancy": current_occupancy,
            "available_seats": room.capacity - current_occupancy,
            "occupancy_percentage": round((current_occupancy / room.capacity * 100), 2) if room.capacity > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Get all occupancy records
@rooms_bp.route("/logs/all", methods=["GET"])
def get_occupancy_logs():
    try:
        logs = Occupancy.query.all()
        return jsonify({
            "count": len(logs),
            "logs": [log.to_dict() for log in logs]
        }), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500
