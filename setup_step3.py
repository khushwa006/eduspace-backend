"""
STEP 3 Complete Setup
Save as: C:\Users\DELL\eduspace_backend\setup_step3.py
Run with: python setup_step3.py
"""
import os
import sys

print("\n" + "="*60)
print("STEP 3 SETUP - Creating Room Models & Occupancy Tracking")
print("="*60)

# Step 1: Create rooms.py
print("\n[1/4] Creating app/routes/rooms.py...")
rooms_code = '''from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.room import Room, Occupancy
from datetime import datetime, timedelta
import jwt

rooms_bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

# Configuration Secret Key mirroring default system variables
QR_SECRET = "dev-secret-key"

@rooms_bp.route("", methods=["GET"])
def get_all_rooms():
    try:
        rooms = Room.query.filter_by(is_active=True).all()
        return jsonify({"msg": "Rooms retrieved successfully", "count": len(rooms), "rooms": [r.to_dict() for r in rooms]}), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@rooms_bp.route("/<int:room_id>", methods=["GET"])
def get_room(room_id):
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({"msg": "Room not found"}), 404
        current = Occupancy.query.filter_by(room_id=room_id, check_out_time=None).count()
        room_data = room.to_dict()
        room_data["current_occupancy"] = current
        room_data["available_seats"] = room.capacity - current
        return jsonify(room_data), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@rooms_bp.route("/<int:room_id>/generate-qr", methods=["GET"])
@jwt_required()
def generate_room_qr_token(room_id):
    """Faculty/Admin side secure temporal stamp utility token generation endpoint"""
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"msg": "Room coordinates missing"}), 404
    payload = {
        "room_id": room.id,
        "room_name": room.name,
        "exp": datetime.utcnow() + timedelta(seconds=60)
    }
    qr_token = jwt.encode(payload, QR_SECRET, algorithm="HS256")
    return jsonify({
        "room_id": room.id,
        "room_name": room.name,
        "qr_token": qr_token
    }), 200

@rooms_bp.route("/verify-qr-checkin", methods=["POST"])
@jwt_required()
def verify_qr_checkin():
    """Validates real-time webcam captures against target signatures securely"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        token = data.get("qr_token")
        if not token:
            return jsonify({"msg": "Missing verification parameters"}), 400
            
        payload = jwt.decode(token, QR_SECRET, algorithms=["HS256"])
        room_id = payload["room_id"]
        
        existing = Occupancy.query.filter_by(room_id=room_id, user_id=user_id, check_out_time=None).first()
        if existing:
            return jsonify({"msg": "Presence already actively registered"}), 409
            
        occupancy = Occupancy(room_id=room_id, user_id=user_id)
        db.session.add(occupancy)
        db.session.commit()
        
        return jsonify({"msg": "QR Check-in authenticated successfully", "occupancy": occupancy.to_dict()}), 201
    except jwt.ExpiredSignatureError:
        return jsonify({"msg": "Scanning lifecycle window lapsed. Try scanning the live feed again."}), 400
    except jwt.InvalidTokenError:
        return jsonify({"msg": "Corrupted digital footprint parsed."}), 400
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@rooms_bp.route("/<int:room_id>/checkin", methods=["POST"])
@jwt_required()
def checkin_room(room_id):
    try:
        user_id = get_jwt_identity()
        room = Room.query.get(room_id)
        if not room:
            return jsonify({"msg": "Room not found"}), 404
        existing = Occupancy.query.filter_by(room_id=room_id, user_id=user_id, check_out_time=None).first()
        if existing:
            return jsonify({"msg": "User already checked in to this room"}), 409
        occupancy = Occupancy(room_id=room_id, user_id=user_id)
        db.session.add(occupancy)
        db.session.commit()
        return jsonify({"msg": "Checked in successfully", "occupancy": occupancy.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@rooms_bp.route("/<int:room_id>/checkout", methods=["POST"])
@jwt_required()
def checkout_room(room_id):
    try:
        user_id = get_jwt_identity()
        occupancy = Occupancy.query.filter_by(room_id=room_id, user_id=user_id, check_out_time=None).first()
        if not occupancy:
            return jsonify({"msg": "No active check-in found"}), 404
        occupancy.check_out_time = datetime.utcnow()
        duration = occupancy.check_out_time - occupancy.check_in_time
        occupancy.duration_minutes = int(duration.total_seconds() / 60)
        db.session.commit()
        return jsonify({"msg": "Checked out successfully", "occupancy": occupancy.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@rooms_bp.route("/<int:room_id>/occupancy", methods=["GET"])
def get_occupancy(room_id):
    try:
        room = Room.query.get(room_id)
        if not room:
            return jsonify({"msg": "Room not found"}), 404
        current = Occupancy.query.filter_by(room_id=room_id, check_out_time=None).count()
        return jsonify({
            "room_id": room_id,
            "room_name": room.name,
            "capacity": room.capacity,
            "current_occupancy": current,
            "available_seats": room.capacity - current,
            "occupancy_percentage": round((current / room.capacity * 100), 2) if room.capacity > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

@rooms_bp.route("/logs/all", methods=["GET"])
def get_occupancy_logs():
    try:
        logs = Occupancy.query.all()
        return jsonify({"count": len(logs), "logs": [log.to_dict() for log in logs]}), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500
'''

try:
    os.makedirs('app/routes', exist_ok=True)
    with open('app/routes/rooms.py', 'w') as f:
        f.write(rooms_code)
    print("✅ rooms.py created")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Step 2: Update __init__.py
print("[2/4] Updating app/__init__.py...")
init_code = '''from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv

load_dotenv()
db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///eduspace.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = "dev-secret-key"
    
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)
    socketio.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    @app.route("/health")
    def health():
        return {"status": "Server is running"}, 200
    
    try:
        from app.routes.auth import auth_bp
        app.register_blueprint(auth_bp)
        print("✅ Auth blueprint registered")
    except Exception as e:
        print(f"Auth error: {e}")
    
    try:
        from app.routes.rooms import rooms_bp
        app.register_blueprint(rooms_bp)
        print("✅ Rooms blueprint registered")
    except Exception as e:
        print(f"Rooms error: {e}")
    
    return app
'''

try:
    with open('app/__init__.py', 'w') as f:
        f.write(init_code)
    print("✅ __init__.py updated")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Step 3: Seed database
print("[3/4] Seeding database with 8 sample rooms...")
try:
    from app import create_app, db
    from app.models.room import Room
    
    app = create_app()
    
    with app.app_context():
        Room.query.delete()
        
        rooms_data = [
            ('Lab A-101', 'Lab', 40, 'A1', 'Building A'),
            ('Lab B-204', 'Lab', 35, 'B2', 'Building B'),
            ('Hall C-301', 'Lecture Hall', 80, 'C3', 'Building C'),
            ('Hall D-102', 'Lecture Hall', 100, 'D1', 'Building D'),
            ('Study Pod S-01', 'Study Pod', 6, 'S0', 'Study Area'),
            ('Study Pod S-02', 'Study Pod', 6, 'S0', 'Study Area'),
            ('Meeting Room E-205', 'Meeting Room', 20, 'E2', 'Building E'),
            ('Computer Lab F-103', 'Lab', 45, 'F1', 'Building F'),
        ]
        
        for name, room_type, capacity, floor, building in rooms_data:
            room = Room(name=name, room_type=room_type, capacity=capacity, floor=floor, building=building)
            db.session.add(room)
        
        db.session.commit()
        count = Room.query.count()
        print(f"✅ Created {count} sample rooms")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Step 4: Test endpoints
print("[4/4] Testing API endpoints...")
try:
    import requests
    
    # Test 1: Get all rooms
    r1 = requests.get('http://localhost:5000/api/rooms')
    print(f"  GET /api/rooms: Status {r1.status_code}, Count: {r1.json().get('count', 0)} rooms")
    
    # Test 2: Get single room
    r2 = requests.get('http://localhost:5000/api/rooms/1')
    if r2.status_code == 200:
        data = r2.json()
        print(f"  GET /api/rooms/1: {data.get('name')} (Capacity: {data.get('capacity')})")
    
    # Test 3: Get occupancy
    r3 = requests.get('http://localhost:5000/api/rooms/1/occupancy')
    if r3.status_code == 200:
        data = r3.json()
        print(f"  GET /api/rooms/1/occupancy: {data.get('current_occupancy')} / {data.get('capacity')} occupied")
    
except Exception as e:
    print(f"  Testing skipped (Flask may not be running): {e}")

print("\n" + "="*60)
print("✅ STEP 3 SETUP COMPLETE!")
print("="*60)
print("\nNEXT STEPS:")
print("1. Make sure Flask is running: python run.py")
print("2. Check endpoints at http://localhost:5000/api/rooms")
print("\n")