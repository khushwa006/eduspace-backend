from flask import Flask
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