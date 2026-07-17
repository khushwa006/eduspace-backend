from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import jwt
import random
import os

import re
import math
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── LOAD ENV ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MAIL_EMAIL    = os.getenv('MAIL_EMAIL', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_SERVER   = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT     = int(os.getenv('MAIL_PORT', '587'))
import os
from threading import Thread

def validate_password(password):
    """Ensure password meets strength requirements"""
    if len(password) < 8:
        return 'Password must be at least 8 characters'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter'
    if not re.search(r'[a-z]', password):
        return 'Password must contain at least one lowercase letter'
    if not re.search(r'[0-9]', password):
        return 'Password must contain at least one number'
    if not re.search(r'[^A-Za-z0-9]', password):
        return 'Password must contain at least one special character (!@#$...)'
    return None

app = Flask(__name__)
# ── EMAIL CONFIG ──────────────────────────────────────────────
MAIL_USER = os.environ.get('MAIL_EMAIL', 'sptradersraju@gmail.com')
MAIL_PASS = os.environ.get('MAIL_APP_PASSWORD', 'yeyoqpcrxlbsmusu')


def _send_async(app, msg):
    with app.app_context():
        try: mail.send(msg)
        except Exception as e: print(f'Email error: {e}')

def send_email(subject, recipients, html_body):
    if not recipients: return
    to = recipients if isinstance(recipients, list) else [recipients]
    msg = Message(subject, recipients=to)
    msg.html = html_body
    msg.body  = subject
    Thread(target=_send_async, args=(app, msg)).start()

def email_wrap(title, body):
    return (
        '<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">'
        '<div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);border-radius:12px 12px 0 0;padding:24px;text-align:center">'
        '<h1 style="color:#fff;margin:0;font-size:22px">&#127979; EduSpace</h1>'
        '<p style="color:rgba(255,255,255,0.75);margin:4px 0 0;font-size:13px">Campus Management Platform</p>'
        '</div>'
        '<div style="background:#fff;border-radius:0 0 12px 12px;padding:28px;border:1px solid #e2e8f0;border-top:none">'
        f'<h2 style="color:#1e293b;font-size:18px;margin:0 0 16px">{title}</h2>'
        f'{body}'
        '<hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">'
        '<p style="color:#94a3b8;font-size:11px;text-align:center;margin:0">EduSpace &mdash; Amity University Campus Platform</p>'
        '</div></div>'
    )

database_url = os.environ.get("DATABASE_URL")

if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///eduspace.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = 'dev-secret-key'
app.config['JWT_EXPIRY_DAYS'] = 30

db = SQLAlchemy(app)
CORS(app)  # Allow all origins for development

# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, faculty, admin
    phone         = db.Column(db.String(20))
    department    = db.Column(db.String(120))
    enrollment_no = db.Column(db.String(50))
    program       = db.Column(db.String(100))   # e.g. B.Tech CSE
    batch_year    = db.Column(db.String(20))    # e.g. 2023-27
    section       = db.Column(db.String(10))    # e.g. A, B
    bio           = db.Column(db.Text)          # Short about me
    profile_photo = db.Column(db.Text, nullable=True)  # base64 encoded image
    two_fa_enabled = db.Column(db.Boolean, default=False)
    security_question = db.Column(db.String(200), nullable=True)
    security_answer_hash = db.Column(db.String(255), nullable=True)
    security_failed_attempts = db.Column(db.Integer, default=0)
    security_lockout_until = db.Column(db.DateTime, nullable=True)
    security_locked = db.Column(db.Boolean, default=False)  # permanently locked — admin must reset
    is_approved  = db.Column(db.Boolean, default=True)  # False for pending faculty
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    room_type = db.Column(db.String(50))
    building = db.Column(db.String(50))
    floor = db.Column(db.Integer)
    capacity = db.Column(db.Integer, nullable=False)
    current_occupancy = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    slot_name = db.Column(db.String(50))

def slot_sort_key(slot):
    """Returns minutes-since-midnight for a slot's start time, for chronological sorting.
    Parses from slot_name (e.g. '9:00 AM - 10:00 AM') since that's the reliably-populated field.
    Falls back to start_time, then to a large number (sorts last) if neither parses."""
    text = (slot.slot_name or slot.start_time or '').split('-')[0].strip()
    try:
        t = datetime.strptime(text, '%I:%M %p')
        return t.hour * 60 + t.minute
    except (ValueError, TypeError):
        return 9999

def sorted_time_slots():
    return sorted(TimeSlot.query.all(), key=slot_sort_key)

class BookingRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    class_name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    number_of_students = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='PENDING')
    admin_notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    faculty = db.relationship('User', foreign_keys=[faculty_id], backref='booking_requests')
    room = db.relationship('Room', backref='booking_requests')
    time_slot = db.relationship('TimeSlot', backref='booking_requests')
    approver = db.relationship('User', foreign_keys=[approved_by])

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('booking_request.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    class_name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    status = db.Column(db.String(20), default='ACTIVE')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    request = db.relationship('BookingRequest', backref='booking')
    faculty = db.relationship('User', foreign_keys=[faculty_id])
    room = db.relationship('Room', backref='bookings')
    time_slot = db.relationship('TimeSlot', backref='bookings')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='ABSENT')  # PRESENT, ABSENT, LATE
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    booking = db.relationship('Booking', backref='attendances')
    student = db.relationship('User', foreign_keys=[student_id])
    marker = db.relationship('User', foreign_keys=[marked_by])

class StudentFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)  # optional
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_type = db.Column(db.String(50), nullable=False, default='general_suggestion')
    # feedback_type: room_condition | booking_process | faculty_experience | technical_issue | general_suggestion
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship('Booking', backref='feedbacks', foreign_keys=[booking_id])
    student = db.relationship('User', foreign_keys=[student_id])

class LostFoundItem(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    reported_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title        = db.Column(db.String(120), nullable=False)
    category     = db.Column(db.String(50), nullable=False, default='other')
    # category: books | electronics | bags | documents | clothing | keys | other
    description  = db.Column(db.Text, nullable=True)
    location     = db.Column(db.String(200), nullable=True)
    item_type    = db.Column(db.String(10), nullable=False, default='lost')
    # item_type: lost | found
    status       = db.Column(db.String(20), nullable=False, default='open')
    # status: open | claimed | resolved
    contact_info = db.Column(db.String(200), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    reporter = db.relationship('User', foreign_keys=[reported_by])



class CampusConfig(db.Model):
    """Stores campus GPS boundary — only one row needed"""
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), default='Main Campus')
    latitude   = db.Column(db.Float, nullable=False, default=28.622902)
    longitude  = db.Column(db.Float, nullable=False, default=77.050226)
    radius_m   = db.Column(db.Integer, default=500)   # metres
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class GeofenceLog(db.Model):
    """Records every GPS check-in attempt"""
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id    = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    latitude      = db.Column(db.Float, nullable=False)
    longitude     = db.Column(db.Float, nullable=False)
    distance_m    = db.Column(db.Float, nullable=False)   # distance from campus centre
    is_within     = db.Column(db.Boolean, nullable=False)  # within boundary?
    override_by   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # faculty override
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    student  = db.relationship('User', foreign_keys=[student_id])
    override = db.relationship('User', foreign_keys=[override_by])


class Notification(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(120), nullable=False)
    message       = db.Column(db.Text, nullable=False)
    notif_type    = db.Column(db.String(20), default='info')
    # notif_type: info | event | warning | urgent
    target_role   = db.Column(db.String(20), default='all')
    # target_role: all | student | faculty
    created_by    = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    author        = db.relationship('User', foreign_keys=[created_by])

class NotificationRead(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'))
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id'))
    read_at         = db.Column(db.DateTime, default=datetime.utcnow)

class Skill(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(80), nullable=False, unique=True)
    category = db.Column(db.String(40), nullable=False)
    # category: Programming | Music | Arts | Languages | Science | Sports | Other

class UserSkill(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id    = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    skill_type  = db.Column(db.String(10), nullable=False)  # teach | learn
    proficiency = db.Column(db.String(15), default='intermediate')  # beginner|intermediate|expert
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user  = db.relationship('User',  foreign_keys=[user_id])
    skill = db.relationship('Skill', foreign_keys=[skill_id])

class TeamPost(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    posted_by       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title           = db.Column(db.String(120), nullable=False)
    event_name      = db.Column(db.String(120), nullable=False)
    event_date      = db.Column(db.String(20), nullable=True)
    description     = db.Column(db.Text, nullable=True)
    required_skills = db.Column(db.Text, nullable=True)
    team_size       = db.Column(db.Integer, default=4)
    status          = db.Column(db.String(10), default='open')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    poster = db.relationship('User', foreign_keys=[posted_by])

class TeamApplication(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    post_id      = db.Column(db.Integer, db.ForeignKey('team_post.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message      = db.Column(db.Text, nullable=True)
    status       = db.Column(db.String(10), default='pending')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    applicant = db.relationship('User', foreign_keys=[applicant_id])
    post      = db.relationship('TeamPost', foreign_keys=[post_id])

class Grievance(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    student_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category     = db.Column(db.String(30), nullable=False)   # hostel|academic|facility|ragging|harassment|other
    priority     = db.Column(db.String(10), default='medium') # low|medium|high|urgent
    subject      = db.Column(db.String(150), nullable=False)
    description  = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    status       = db.Column(db.String(15), default='pending')  # pending|in_progress|resolved|rejected
    admin_reply  = db.Column(db.Text, nullable=True)
    resolved_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student  = db.relationship('User', foreign_keys=[student_id])
    resolver = db.relationship('User', foreign_keys=[resolved_by])

class TimetableEntry(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(10), nullable=False)   # Monday..Saturday
    time_slot_id= db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    subject_name= db.Column(db.String(120), nullable=False)
    faculty_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    room_id     = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)
    program     = db.Column(db.String(100), nullable=False)  # e.g. B.Tech CSE
    batch_year  = db.Column(db.String(20), nullable=False)   # e.g. 2023-27
    section     = db.Column(db.String(10), nullable=False)   # e.g. A
    created_by  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    time_slot = db.relationship('TimeSlot', foreign_keys=[time_slot_id])
    faculty   = db.relationship('User', foreign_keys=[faculty_id])
    room      = db.relationship('Room', foreign_keys=[room_id])

class ClassAttendance(db.Model):
    """Attendance marked against an actual scheduled Timetable class (not a Booking)."""
    id                 = db.Column(db.Integer, primary_key=True)
    timetable_entry_id = db.Column(db.Integer, db.ForeignKey('timetable_entry.id'), nullable=False)
    student_id         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_date         = db.Column(db.Date, nullable=False)
    status             = db.Column(db.String(20), default='absent')  # present | absent | out_of_campus
    auto_status        = db.Column(db.String(20), nullable=True)     # what was auto-suggested before override
    override_reason    = db.Column(db.Text, nullable=True)
    marked_by          = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    marked_at          = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('timetable_entry_id', 'student_id', 'class_date', name='uq_class_attendance'),)

    timetable_entry = db.relationship('TimetableEntry', foreign_keys=[timetable_entry_id])
    student          = db.relationship('User', foreign_keys=[student_id])
    marker           = db.relationship('User', foreign_keys=[marked_by])

class Holiday(db.Model):
    """Admin-declared non-working dates (festivals, breaks, etc.) — used to
    correctly compute the attendance window's 'next working day' deadline."""
    id     = db.Column(db.Integer, primary_key=True)
    date   = db.Column(db.Date, nullable=False, unique=True)
    name   = db.Column(db.String(100), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class LoginActivity(db.Model):
    """Tracks every successful login, for the user's own 'last login / login history' view."""
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    logged_in_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    """General activity trail — what a user did, for their own account history."""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action      = db.Column(db.String(50), nullable=False)    # short machine tag, e.g. 'booking_request'
    description = db.Column(db.String(255), nullable=False)   # human-readable, e.g. 'Requested Class A101 for 28 Jun'
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

def log_activity(user_id, action, description):
    """Best-effort activity logger — never lets a logging failure break the calling request."""
    try:
        db.session.add(ActivityLog(user_id=user_id, action=action, description=description))
        db.session.commit()
    except Exception:
        db.session.rollback()

class OTPCode(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code       = db.Column(db.String(6), nullable=False)
    purpose    = db.Column(db.String(20), default='login')   # login | enable_2fa
    is_used    = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', foreign_keys=[user_id])

class FacilityBooking(db.Model):
    """Instant self-service booking for sports facilities and library seats."""
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id     = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    time_slot_id= db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    status      = db.Column(db.String(15), default='confirmed')  # confirmed | cancelled
    seat_numbers= db.Column(db.String(50), nullable=True)   # e.g. "3,4,5,6" — Library Seat only
    group_size  = db.Column(db.Integer, default=1)          # number of seats reserved by this booking
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    student   = db.relationship('User', foreign_keys=[student_id])
    room      = db.relationship('Room', foreign_keys=[room_id])
    time_slot = db.relationship('TimeSlot', foreign_keys=[time_slot_id])


# ═══════════════════════════════════════════════════════════════
# EMAIL HELPERS
# ═══════════════════════════════════════════════════════════════

def send_email(to, subject, html_body):
    """Send email via Gmail SMTP. Fails silently so app keeps running."""
    if not MAIL_EMAIL or not MAIL_PASSWORD:
        print(f"[EMAIL] Skipped (no credentials): {subject} -> {to}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[EduSpace] {subject}"
        msg["From"]    = f"EduSpace <{MAIL_EMAIL}>"
        msg["To"]      = to
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(MAIL_EMAIL, MAIL_PASSWORD)
            srv.sendmail(MAIL_EMAIL, to, msg.as_string())
        print(f"[EMAIL] Sent: {subject} -> {to}")
        return True
    except Exception as exc:
        print(f"[EMAIL] Failed: {exc}")
        return False

def make_email(title, body, btn_text=None, btn_link="#"):
    btn_html = ""
    if btn_text:
        btn_html = (
            '<a href="' + btn_link + '" style="display:inline-block;margin-top:20px;'
            'padding:12px 28px;background:#3b82f6;color:#fff;border-radius:8px;'
            'text-decoration:none;font-weight:700;font-size:15px;">' + btn_text + "</a>"
        )
    return (
        '<div style="font-family:Inter,Arial,sans-serif;background:#141926;padding:40px 0;">'
        '<div style="max-width:560px;margin:0 auto;background:#1e2433;border-radius:14px;'
        'border:1px solid #2e3a52;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);padding:28px 32px;">'
        '<h1 style="margin:0;color:#fff;font-size:22px;">&#127EB; EduSpace</h1>'
        '<p style="margin:6px 0 0;color:rgba(255,255,255,0.7);font-size:13px;">Smart Campus Management</p>'
        "</div>"
        '<div style="padding:32px;">'
        '<h2 style="margin:0 0 16px;color:#e2e8f0;font-size:20px;">' + title + "</h2>"
        '<div style="color:#94a3b8;font-size:14px;line-height:1.8;">' + body + "</div>"
        + btn_html +
        "</div>"
        '<div style="padding:16px 32px;border-top:1px solid #2e3a52;text-align:center;">'
        '<p style="margin:0;color:#64748b;font-size:12px;">EduSpace &middot; Do not reply to this email</p>'
        "</div></div></div>"
    )


# ═══════════════════════════════════════════════════════════════
# JWT HELPERS
# ═══════════════════════════════════════════════════════════════

def generate_token(user_id, user_role):
    payload = {
        'user_id': user_id,
        'role': user_role,
        'exp': datetime.utcnow() + timedelta(days=app.config['JWT_EXPIRY_DAYS'])
    }
    token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
    return token

def generate_pre_auth_token(user_id):
    """Short-lived token (5 min) issued after password check, before OTP verification."""
    payload = {
        'user_id': user_id,
        'pre_auth': True,
        'exp': datetime.utcnow() + timedelta(minutes=5)
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

def generate_reset_token(user_id):
    """Short-lived token (10 min) issued after security question is answered correctly."""
    payload = {
        'user_id': user_id,
        'pwd_reset': True,
        'exp': datetime.utcnow() + timedelta(minutes=10)
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
        return payload
    except:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        
        try:
            token = token.split(' ')[1]
        except:
            return jsonify({'error': 'Invalid token format'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token has expired'}), 401
        
        request.user_id = payload['user_id']
        request.user_role = payload['role'].lower()  # normalize to lowercase
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user_role.lower() != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

def faculty_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user_role.lower() not in ['faculty', 'admin']:
            return jsonify({'error': 'Faculty access required'}), 403
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user_role.lower() not in ['student', 'admin']:
            return jsonify({'error': 'Student access required'}), 403
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/pending-students', methods=['GET'])
@token_required
@admin_required
def get_pending_students():
    pending = User.query.filter_by(role='student', is_approved=False).all()
    return jsonify([{
        'id': u.id,
        'full_name': f"{u.first_name} {u.last_name}",
        'email': u.email,
        'department': u.department or 'Not set',
        'created_at': u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else ''
    } for u in pending]), 200

@app.route('/api/admin/approve-student/<int:user_id>', methods=['POST'])
@token_required
@admin_required
def approve_student(user_id):
    user = User.query.get(user_id)
    if not user or user.role.lower() != 'student':
        return jsonify({'error': 'Student not found'}), 404
    user.is_approved = True
    db.session.commit()
    send_email(
        'EduSpace: Your Student Account Has Been Approved! ✅',
        [user.email],
        email_wrap(
            f'Welcome to EduSpace, {user.first_name}!',
            f'<div style="background:#dcfce7;border-left:4px solid #10b981;border-radius:8px;padding:14px;margin:16px 0">'
            f'<p style="margin:0;color:#166534"><strong>&#9989; Account Approved</strong><br>'
            f'Your EduSpace Student account is now active!</p></div>'
            f'<p style="color:#374151">You can now log in and access rooms, attendance, skill sharing, and more.</p>'
            f'<p style="color:#374151">Visit <a href="http://localhost:5173" style="color:#3b82f6">EduSpace</a> to get started.</p>'
        )
    )
    return jsonify({'message': f'{user.first_name} {user.last_name} approved!'}), 200

@app.route('/api/admin/reject-student/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def reject_student(user_id):
    user = User.query.get(user_id)
    if not user or user.role.lower() != 'student':
        return jsonify({'error': 'Student not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Student account rejected and removed'}), 200


@app.route('/api/admin/pending-faculty', methods=['GET'])
@token_required
@admin_required
def get_pending_faculty():
    """Admin: list all faculty awaiting approval"""
    pending = User.query.filter_by(role='faculty', is_approved=False).all()
    return jsonify([{
        'id': u.id,
        'full_name': f"{u.first_name} {u.last_name}",
        'email': u.email,
        'department': u.department or 'Not set',
        'created_at': u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else ''
    } for u in pending]), 200


@app.route('/api/admin/approve-faculty/<int:user_id>', methods=['POST'])
@token_required
@admin_required
def approve_faculty(user_id):
    """Admin: approve a pending faculty account"""
    user = User.query.get(user_id)
    if not user or user.role.lower() != 'faculty':
        return jsonify({'error': 'Faculty not found'}), 404
    user.is_approved = True
    db.session.commit()
    send_email(
        'EduSpace: Your Account Has Been Approved! ✅',
        [user.email],
        email_wrap(
            f'Welcome aboard, {user.first_name}! Your account is approved.',
            f'<div style="background:#dcfce7;border-left:4px solid #10b981;border-radius:8px;padding:14px;margin:16px 0">'
            f'<p style="margin:0;color:#166534"><strong>&#9989; Account Approved</strong><br>'
            f'Your EduSpace {user.role.capitalize()} account is now active. You can log in immediately.</p></div>'
            f'<p style="color:#374151">Visit <a href="http://localhost:5173" style="color:#3b82f6">EduSpace</a> and login with your registered email.</p>'
        )
    )
    return jsonify({'message': f'{user.first_name} {user.last_name} approved successfully'}), 200

@app.route('/api/admin/reject-faculty/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def reject_faculty(user_id):
    """Admin: reject and delete a pending faculty account"""
    user = User.query.get(user_id)
    if not user or user.role.lower() != 'faculty':
        return jsonify({'error': 'Faculty not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Faculty account rejected and removed'}), 200

@app.route('/api/admin/all-faculty', methods=['GET'])
@token_required
@admin_required
def get_all_faculty():
    """Admin: list all approved faculty"""
    faculty = User.query.filter_by(role='faculty', is_approved=True).all()
    return jsonify([{
        'id': u.id,
        'full_name': f"{u.first_name} {u.last_name}",
        'email': u.email,
        'department': u.department or 'Not set',
    } for u in faculty]), 200


# ═══════════════════════════════════════════════════════════════
# LOST & FOUND
# ═══════════════════════════════════════════════════════════════

CATEGORIES = ['electronics','books','clothing','accessories','id_cards','sports','other']

def lf_serialize(item, current_user_id=None):
    return {
        'id':          item.id,
        'title': item.title,
        'category':    item.category,
        'description': item.description or '',
        'location':    item.location or 'Not specified',
        'status':      item.status,
        'contact':     item.contact or '',
        'reported_by': item.reported_by,
        'reporter_name': f"{item.reporter.first_name} {item.reporter.last_name}",
        'is_mine':     item.reported_by == current_user_id,
        'created_at':  item.created_at.strftime('%d %b %Y'),
    }

@app.route('/api/lost-found', methods=['GET'])
@token_required
def list_lost_found():
    status   = request.args.get('status', 'all')
    category = request.args.get('category', 'all')
    query    = LostFoundItem.query
    if status   != 'all': query = query.filter_by(status=status)
    if category != 'all': query = query.filter_by(category=category)
    items = query.order_by(LostFoundItem.created_at.desc()).all()
    uid = request.user_id
    return jsonify([lf_serialize(i, uid) for i in items]), 200

@app.route('/api/lost-found', methods=['POST'])
@token_required
def report_lost_found():
    data = request.json or {}
    if not data.get('title','').strip():
        return jsonify({'error': 'Item name is required'}), 400
    if not data.get('status') in ['lost','found']:
        return jsonify({'error': 'Status must be lost or found'}), 400
    item = LostFoundItem(
        reported_by = request.user_id,
        title        = data['title'].strip(),
        category    = data.get('category','other'),
        description = data.get('description','').strip(),
        location    = data.get('location','').strip(),
        status      = data['status'],
        contact     = data.get('contact','').strip(),
    )
    db.session.add(item)
    db.session.commit()
    log_activity(request.user_id, 'lost_found', f'Reported "{item.title}" as {item.status}')
    return jsonify({'message': 'Item reported successfully!', 'id': item.id}), 201

@app.route('/api/lost-found/<int:item_id>/claim', methods=['POST'])
@token_required
def claim_item(item_id):
    item = LostFoundItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if item.status == 'claimed':
        return jsonify({'error': 'Item already claimed'}), 400
    if item.reported_by == request.user_id:
        return jsonify({'error': 'You cannot claim your own item'}), 400
    item.status    = 'claimed'
    item.claimed_by = request.user_id
    db.session.commit()
    return jsonify({'message': 'Item marked as claimed! Please contact the reporter.'}), 200

@app.route('/api/lost-found/<int:item_id>', methods=['DELETE'])
@token_required
def delete_lost_found(item_id):
    item = LostFoundItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    if item.reported_by != request.user_id and request.user_role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item removed'}), 200



# ═══════════════════════════════════════════════════════════════
# GEOFENCED ATTENDANCE
# ═══════════════════════════════════════════════════════════════

def haversine(lat1, lon1, lat2, lon2):
    """Distance in metres between two GPS points"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

@app.route('/api/campus-config', methods=['GET'])
@token_required
def get_campus_config():
    cfg = CampusConfig.query.first()
    if not cfg:
        cfg = CampusConfig(); db.session.add(cfg); db.session.commit()
    return jsonify({'name':cfg.name,'latitude':cfg.latitude,'longitude':cfg.longitude,'radius_m':cfg.radius_m}), 200

@app.route('/api/admin/campus-config', methods=['POST'])
@token_required
@admin_required
def update_campus_config():
    data = request.json or {}
    cfg = CampusConfig.query.first()
    if not cfg:
        cfg = CampusConfig(); db.session.add(cfg)
    if 'name'      in data: cfg.name      = data['name']
    if 'latitude'  in data: cfg.latitude  = float(data['latitude'])
    if 'longitude' in data: cfg.longitude = float(data['longitude'])
    if 'radius_m'  in data: cfg.radius_m  = int(data['radius_m'])
    cfg.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Campus location updated!'}), 200

@app.route('/api/attendance/geofence', methods=['POST'])
@token_required
@student_required
def geofence_checkin():
    """Student submits GPS — backend checks if within campus"""
    data = request.json or {}
    lat = data.get('latitude')
    lon = data.get('longitude')
    if lat is None or lon is None:
        return jsonify({'error': 'GPS coordinates required'}), 400

    cfg = CampusConfig.query.first()
    if not cfg:
        cfg = CampusConfig(); db.session.add(cfg); db.session.commit()

    distance = haversine(lat, lon, cfg.latitude, cfg.longitude)
    is_within = distance <= cfg.radius_m

    log = GeofenceLog(
        student_id = request.user_id,
        booking_id = data.get('booking_id'),
        latitude   = float(lat),
        longitude  = float(lon),
        distance_m = round(distance, 1),
        is_within  = is_within
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'is_within'  : is_within,
        'distance_m' : round(distance, 1),
        'radius_m'   : cfg.radius_m,
        'campus_name': cfg.name,
        'message'    : 'Attendance marked!' if is_within else f'You are {round(distance)}m from campus ({cfg.radius_m}m radius required)',
        'log_id'     : log.id
    }), 200

@app.route('/api/faculty/attendance/override', methods=['POST'])
@token_required
@faculty_required
def faculty_override():
    """Faculty manually marks a student as present"""
    data = request.json or {}
    student_id = data.get('student_id')
    booking_id = data.get('booking_id')
    if not student_id:
        return jsonify({'error': 'student_id required'}), 400

    log = GeofenceLog(
        student_id = student_id,
        booking_id = booking_id,
        latitude   = 0.0,
        longitude  = 0.0,
        distance_m = 0.0,
        is_within  = True,
        override_by= request.user_id
    )
    db.session.add(log)
    db.session.commit()
    student = User.query.get(student_id)
    return jsonify({'message': f'{student.first_name} {student.last_name} marked present (manual override)'}), 200

@app.route('/api/admin/geofence-logs', methods=['GET'])
@token_required
@admin_required
def get_geofence_logs():
    logs = GeofenceLog.query.order_by(GeofenceLog.created_at.desc()).limit(100).all()
    return jsonify([{
        'id'         : l.id,
        'student'    : f"{l.student.first_name} {l.student.last_name}",
        'distance_m' : l.distance_m,
        'is_within'  : l.is_within,
        'override'   : f"{l.override.first_name} {l.override.last_name}" if l.override else None,
        'created_at' : l.created_at.strftime('%d %b %Y, %H:%M')
    } for l in logs]), 200


# ═══════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications():
    role = request.user_role.lower()
    notifs = Notification.query.filter(
        Notification.is_active == True,
        db.or_(Notification.target_role == 'all', Notification.target_role == role)
    ).order_by(Notification.created_at.desc()).all()

    read_ids = {r.notification_id for r in
                NotificationRead.query.filter_by(user_id=request.user_id).all()}

    return jsonify([{
        'id':         n.id,
        'title':      n.title,
        'message':    n.message,
        'notif_type': n.notif_type,
        'target_role':n.target_role,
        'author':     f"{n.author.first_name} {n.author.last_name}" if n.author else 'Admin',
        'is_read':    n.id in read_ids,
        'created_at': n.created_at.strftime('%d %b %Y, %H:%M'),
        'days_ago':   (datetime.utcnow() - n.created_at).days
    } for n in notifs]), 200

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@token_required
def mark_read(notif_id):
    existing = NotificationRead.query.filter_by(
        notification_id=notif_id, user_id=request.user_id).first()
    if not existing:
        db.session.add(NotificationRead(notification_id=notif_id, user_id=request.user_id))
        db.session.commit()
    return jsonify({'message': 'Marked as read'}), 200

@app.route('/api/notifications/read-all', methods=['POST'])
@token_required
def mark_all_read():
    role = request.user_role.lower()
    notifs = Notification.query.filter(
        Notification.is_active == True,
        db.or_(Notification.target_role == 'all', Notification.target_role == role)
    ).all()
    read_ids = {r.notification_id for r in
                NotificationRead.query.filter_by(user_id=request.user_id).all()}
    for n in notifs:
        if n.id not in read_ids:
            db.session.add(NotificationRead(notification_id=n.id, user_id=request.user_id))
    db.session.commit()
    return jsonify({'message': 'All marked as read'}), 200

@app.route('/api/admin/notifications', methods=['POST'])
@token_required
@admin_required
def create_notification():
    data = request.json or {}
    if not data.get('title','').strip() or not data.get('message','').strip():
        return jsonify({'error': 'Title and message are required'}), 400
    notif = Notification(
        title       = data['title'].strip(),
        message     = data['message'].strip(),
        notif_type  = data.get('notif_type', 'info'),
        target_role = data.get('target_role', 'all'),
        created_by  = request.user_id
    )
    db.session.add(notif)
    db.session.commit()
    return jsonify({'message': 'Notification sent!', 'id': notif.id}), 201

@app.route('/api/admin/notifications', methods=['GET'])
@token_required
@admin_required
def get_all_notifications():
    notifs = Notification.query.order_by(Notification.created_at.desc()).all()
    return jsonify([{
        'id': n.id, 'title': n.title, 'message': n.message,
        'notif_type': n.notif_type, 'target_role': n.target_role,
        'is_active': n.is_active,
        'read_count': NotificationRead.query.filter_by(notification_id=n.id).count(),
        'created_at': n.created_at.strftime('%d %b %Y, %H:%M')
    } for n in notifs]), 200

@app.route('/api/admin/notifications/<int:notif_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_notification(notif_id):
    notif = Notification.query.get(notif_id)
    if not notif: return jsonify({'error': 'Not found'}), 404
    notif.is_active = False
    db.session.commit()
    return jsonify({'message': 'Notification removed'}), 200


@app.route('/api/student/my-attendance', methods=['GET'])
@token_required
@student_required
def my_attendance():
    """Student views their full attendance history + stats"""
    records = Attendance.query.filter_by(student_id=request.user_id)        .order_by(Attendance.marked_at.desc()).all()

    gps_logs = GeofenceLog.query.filter_by(student_id=request.user_id)        .order_by(GeofenceLog.created_at.desc()).limit(20).all()

    total   = len(records)
    present = sum(1 for r in records if r.status.upper() == 'PRESENT')
    late    = sum(1 for r in records if r.status.upper() == 'LATE')
    absent  = sum(1 for r in records if r.status.upper() == 'ABSENT')
    pct     = round((present + late) / total * 100, 1) if total > 0 else 0

    return jsonify({
        'stats': {
            'total': total, 'present': present,
            'late': late, 'absent': absent, 'percentage': pct
        },
        'records': [{
            'id':          r.id,
            'class_name':  r.booking.class_name if r.booking else 'N/A',
            'room':        r.booking.room.name  if r.booking and r.booking.room else 'N/A',
            'date':        r.booking.date       if r.booking else '',
            'time_slot':   r.booking.time_slot.slot_name if r.booking and r.booking.time_slot else '',
            'faculty':     f"{r.booking.faculty.first_name} {r.booking.faculty.last_name}" if r.booking and r.booking.faculty else '',
            'status':      r.status.upper(),
            'marked_at':   r.marked_at.strftime('%d %b %Y, %H:%M'),
        } for r in records],
        'gps_logs': [{
            'id':         g.id,
            'distance_m': g.distance_m,
            'is_within':  g.is_within,
            'override':   g.override.first_name if g.override else None,
            'created_at': g.created_at.strftime('%d %b %Y, %H:%M')
        } for g in gps_logs]
    }), 200


# ═══════════════════════════════════════════════════════════════
# STUDENT — MY ATTENDANCE
# ═══════════════════════════════════════════════════════════════

@app.route('/api/student/my-geofence-logs', methods=['GET'])
@token_required
@student_required
def my_geofence_logs():
    logs = GeofenceLog.query.filter_by(student_id=request.user_id)        .order_by(GeofenceLog.created_at.desc()).limit(50).all()
    return jsonify([{
        'id':         l.id,
        'is_within':  l.is_within,
        'distance_m': l.distance_m,
        'override':   bool(l.override_by),
        'created_at': l.created_at.strftime('%d %b %Y, %H:%M'),
    } for l in logs]), 200


# ═══════════════════════════════════════════════════════════════
# SKILL SHARING MATRIX
# ═══════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════

@app.route('/api/skills', methods=['GET'])
@token_required
def get_skills():
    skills = Skill.query.order_by(Skill.category, Skill.name).all()
    return jsonify([{'id':s.id,'name':s.name,'category':s.category} for s in skills]), 200

@app.route('/api/skills/my', methods=['GET'])
@token_required
def get_my_skills():
    mine = UserSkill.query.filter_by(user_id=request.user_id).all()
    return jsonify([{
        'id':u.id,'skill_id':u.skill_id,'skill_name':u.skill.name,
        'category':u.skill.category,'skill_type':u.skill_type,'proficiency':u.proficiency
    } for u in mine]), 200

@app.route('/api/skills/my', methods=['POST'])
@token_required
def add_my_skill():
    data = request.json or {}
    skill_id   = data.get('skill_id')
    skill_type = data.get('skill_type','teach')
    if not skill_id: return jsonify({'error':'skill_id required'}), 400
    existing = UserSkill.query.filter_by(user_id=request.user_id, skill_id=skill_id, skill_type=skill_type).first()
    if existing: return jsonify({'error':'Already added'}), 400
    us = UserSkill(user_id=request.user_id, skill_id=skill_id,
                   skill_type=skill_type, proficiency=data.get('proficiency','intermediate'))
    db.session.add(us)
    db.session.commit()
    return jsonify({'message':'Skill added!','id':us.id}), 201

@app.route('/api/skills/my/<int:us_id>', methods=['DELETE'])
@token_required
def remove_my_skill(us_id):
    us = UserSkill.query.get(us_id)
    if not us or us.user_id != request.user_id: return jsonify({'error':'Not found'}), 404
    db.session.delete(us)
    db.session.commit()
    return jsonify({'message':'Removed'}), 200

@app.route('/api/skills/matches', methods=['GET'])
@token_required
def get_skill_matches():
    """Return users who can teach skills I want to learn"""
    want_skills = [u.skill_id for u in UserSkill.query.filter_by(user_id=request.user_id, skill_type='learn').all()]
    if not want_skills:
        return jsonify([]), 200
    teachers = UserSkill.query.filter(
        UserSkill.skill_id.in_(want_skills),
        UserSkill.skill_type == 'teach',
        UserSkill.user_id != request.user_id
    ).all()
    result = {}
    for t in teachers:
        uid = t.user_id
        if uid not in result:
            result[uid] = {
                'user_id':uid,'name':f"{t.user.first_name} {t.user.last_name}",
                'email':t.user.email,'skills':[]
            }
        result[uid]['skills'].append({'skill':t.skill.name,'category':t.skill.category,'proficiency':t.proficiency})
    return jsonify(list(result.values())), 200

@app.route('/api/skills/directory', methods=['GET'])
@token_required
def skills_directory():
    """All users + their teach skills"""
    teachers = UserSkill.query.filter_by(skill_type='teach').all()
    result = {}
    for t in teachers:
        uid = t.user_id
        if uid not in result:
            result[uid] = {
                'user_id':uid,'name':f"{t.user.first_name} {t.user.last_name}",
                'email':t.user.email,'skills':[]
            }
        result[uid]['skills'].append({'skill_id':t.skill_id,'skill':t.skill.name,'category':t.skill.category,'proficiency':t.proficiency})
    return jsonify(list(result.values())), 200

# ── TEAM POSTS ────────────────────────────────────────────────

@app.route('/api/teams', methods=['GET'])
@token_required
def get_teams():
    posts = TeamPost.query.filter_by(status='open').order_by(TeamPost.created_at.desc()).all()
    return jsonify([{
        'id':p.id,'title':p.title,'event_name':p.event_name,'event_date':p.event_date,
        'description':p.description,'required_skills':p.required_skills,
        'team_size':p.team_size,'status':p.status,
        'poster':f"{p.poster.first_name} {p.poster.last_name}",'poster_email':p.poster.email,
        'posted_by':p.posted_by,
        'applicant_count':TeamApplication.query.filter_by(post_id=p.id).count(),
        'created_at':p.created_at.strftime('%d %b %Y')
    } for p in posts]), 200

@app.route('/api/teams', methods=['POST'])
@token_required
def create_team():
    data = request.json or {}
    if not data.get('title') or not data.get('event_name'):
        return jsonify({'error':'Title and event name are required'}), 400
    post = TeamPost(
        posted_by=request.user_id, title=data['title'].strip(),
        event_name=data['event_name'].strip(), event_date=data.get('event_date',''),
        description=data.get('description','').strip(),
        required_skills=data.get('required_skills',''),
        team_size=int(data.get('team_size',4))
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'message':'Team post created!','id':post.id}), 201

@app.route('/api/teams/<int:post_id>/apply', methods=['POST'])
@token_required
def apply_team(post_id):
    existing = TeamApplication.query.filter_by(post_id=post_id, applicant_id=request.user_id).first()
    if existing: return jsonify({'error':'Already applied'}), 400
    data = request.json or {}
    app_obj = TeamApplication(post_id=post_id, applicant_id=request.user_id,
                              message=data.get('message','').strip())
    db.session.add(app_obj)
    db.session.commit()
    return jsonify({'message':'Application sent!'}), 201

@app.route('/api/teams/my', methods=['GET'])
@token_required
def my_teams():
    posts = TeamPost.query.filter_by(posted_by=request.user_id).order_by(TeamPost.created_at.desc()).all()
    result = []
    for p in posts:
        apps = TeamApplication.query.filter_by(post_id=p.id).all()
        result.append({
            'id':p.id,'title':p.title,'event_name':p.event_name,'status':p.status,
            'applicants':[{
                'id':a.id,'name':f"{a.applicant.first_name} {a.applicant.last_name}",
                'email':a.applicant.email,'message':a.message,'status':a.status
            } for a in apps]
        })
    return jsonify(result), 200

@app.route('/api/teams/applications/<int:app_id>', methods=['POST'])
@token_required
def respond_application(app_id):
    appl = TeamApplication.query.get(app_id)
    if not appl: return jsonify({'error':'Not found'}), 404
    post = TeamPost.query.get(appl.post_id)
    if post.posted_by != request.user_id: return jsonify({'error':'Not authorized'}), 403
    data = request.json or {}
    appl.status = data.get('status','pending')
    db.session.commit()
    return jsonify({'message':f'Application {appl.status}'}), 200


# ═══════════════════════════════════════════════════════════════
# ADMIN — ROOM MANAGEMENT (CRUD)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/rooms', methods=['POST'])
@token_required
@admin_required
def create_room():
    data = request.json or {}
    if not data.get('name','').strip():
        return jsonify({'error': 'Room name is required'}), 400
    if Room.query.filter_by(name=data['name'].strip()).first():
        return jsonify({'error': 'A room with this name already exists'}), 400
    room = Room(
        name        = data['name'].strip(),
        room_type   = data.get('room_type', 'Classroom'),
        building    = data.get('building', '').strip(),
        floor       = int(data.get('floor', 1)),
        capacity    = int(data.get('capacity', 30))
    )
    db.session.add(room)
    db.session.commit()
    return jsonify({'message': f'Room "{room.name}" created!', 'id': room.id}), 201

@app.route('/api/admin/rooms/<int:room_id>', methods=['PUT'])
@token_required
@admin_required
def update_room(room_id):
    room = Room.query.get(room_id)
    if not room: return jsonify({'error': 'Room not found'}), 404
    data = request.json or {}
    if 'name'      in data: room.name      = data['name'].strip()
    if 'room_type' in data: room.room_type = data['room_type']
    if 'building'  in data: room.building  = data['building'].strip()
    if 'floor'     in data: room.floor     = int(data['floor'])
    if 'capacity'  in data: room.capacity  = int(data['capacity'])
    db.session.commit()
    return jsonify({'message': f'Room "{room.name}" updated!'}), 200

@app.route('/api/admin/rooms/<int:room_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_room(room_id):
    room = Room.query.get(room_id)
    if not room: return jsonify({'error': 'Room not found'}), 404
    # Check if room has active bookings
    active = Booking.query.filter_by(room_id=room_id).count()
    if active > 0:
        return jsonify({'error': f'Cannot delete — room has {active} booking(s). Remove bookings first.'}), 400
    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': f'Room "{room.name}" deleted!'}), 200

# ═══════════════════════════════════════════════════════════════
# API ROUTES - AUTHENTICATION
# ═══════════════════════════════════════════════════════════════

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'User already exists'}), 400
    
    # Validate password strength
    pw_error = validate_password(data.get('password', ''))
    if pw_error:
        return jsonify({'error': pw_error}), 400

    if not data.get('security_question') or not data.get('security_answer'):
        return jsonify({'error': 'Please select a security question and provide an answer'}), 400

    role = data.get('role', 'student').lower()

    # Block anyone trying to register as admin via API
    if role == 'admin':
        return jsonify({'error': 'Admin accounts cannot be self-registered'}), 403

    # Faculty and Students require admin approval before they can log in
    is_approved = False if role in ['faculty', 'student'] else True

    user = User(
        email=data['email'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        role=role,
        phone=data.get('phone'),
        department=data.get('department'),
        is_approved=is_approved,
        security_question=data['security_question'].strip(),
        security_answer_hash=generate_password_hash(data['security_answer'].strip().lower())
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    if role in ['faculty', 'student']:
        # Email to new user
        send_email(user.email, "Registration Received — Pending Approval",
            make_email(
                f"Thanks for Registering, {user.first_name}!",
                f"<p>Your <strong>{role.capitalize()}</strong> account on EduSpace has been submitted and is <strong>pending admin approval</strong>.</p>"
                "<p>You will receive another email once your account is approved. This usually takes less than 24 hours.</p>",
                "Learn More", "http://localhost:5173"
            ))
        # Email to all admins
        for adm in User.query.filter(User.role.ilike('admin')).all():
            send_email(adm.email, f"New {role.capitalize()} Account Pending Approval",
                make_email(
                    f"New {role.capitalize()} Needs Your Approval",
                    f"<p><strong>{user.first_name} {user.last_name}</strong> ({user.email}) has registered as <strong>{role.capitalize()}</strong> and is waiting for your approval.</p>",
                    "Go to Admin Dashboard", "http://localhost:5173"
                ))
        return jsonify({
            'message': f'Registration submitted! Your {role} account is pending admin approval. You will be able to login once approved.',
            'pending': True,
            'role': role
        }), 201

    token = generate_token(user.id, user.role)
    return jsonify({'token': token, 'user': {'id': user.id, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name, 'role': user.role}}), 201

# ═══════════════════════════════════════════════════════════════
# FORGOT PASSWORD — SECURITY QUESTION FLOW
# ═══════════════════════════════════════════════════════════════

SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What is your mother's maiden name?",
    "What city were you born in?",
    "What was the name of your first school?",
    "What is your favorite teacher's name?",
    "What was your childhood nickname?",
]

@app.route('/api/auth/security-questions', methods=['GET'])
def get_security_questions():
    return jsonify({'questions': SECURITY_QUESTIONS}), 200

@app.route('/api/auth/forgot-password/question', methods=['POST'])
def forgot_password_get_question():
    data = request.json or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.security_question:
        return jsonify({'error': 'No account found with this email, or no security question is set up.'}), 404

    if user.security_locked:
        return jsonify({'error': 'This account is locked after too many failed attempts. Please contact your admin to reset your password.'}), 403

    if user.security_lockout_until and user.security_lockout_until > datetime.utcnow():
        remaining = int((user.security_lockout_until - datetime.utcnow()).total_seconds())
        return jsonify({'error': f'Too many failed attempts. Please try again in {remaining}s.', 'cooldown_seconds': remaining}), 429

    return jsonify({'security_question': user.security_question}), 200

@app.route('/api/auth/forgot-password/verify', methods=['POST'])
def forgot_password_verify_answer():
    data = request.json or {}
    email = data.get('email', '').strip()
    answer = data.get('security_answer', '').strip().lower()

    if not email or not answer:
        return jsonify({'error': 'Email and answer are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.security_answer_hash:
        return jsonify({'error': 'No account found with this email, or no security question is set up.'}), 404

    # Hard lock — only admin can reset
    if user.security_locked:
        return jsonify({'error': 'This account is locked after too many failed attempts. Please contact your admin to reset your password.'}), 403

    # Active cooldown
    if user.security_lockout_until and user.security_lockout_until > datetime.utcnow():
        remaining = int((user.security_lockout_until - datetime.utcnow()).total_seconds())
        return jsonify({'error': f'Too many failed attempts. Please try again in {remaining}s.', 'cooldown_seconds': remaining}), 429

    # Correct answer — reset everything and issue token
    if check_password_hash(user.security_answer_hash, answer):
        user.security_failed_attempts = 0
        user.security_lockout_until = None
        db.session.commit()
        return jsonify({
            'message': 'Answer verified! You can now set a new password.',
            'reset_token': generate_reset_token(user.id)
        }), 200

    # ── Wrong answer — increment and evaluate thresholds ──────
    user.security_failed_attempts = (user.security_failed_attempts or 0) + 1
    attempts = user.security_failed_attempts

    if attempts >= 10:
        user.security_locked = True
        user.security_lockout_until = None
        db.session.commit()
        send_email(user.email, "Account Locked — Too Many Failed Attempts",
            make_email(
                "Security Alert: Account Locked",
                f"<p>Hi <strong>{user.first_name}</strong>,</p>"
                "<p>Your account's password recovery has been <strong>locked</strong> after repeated "
                "incorrect security question answers.</p>"
                "<p>Please contact your admin to have your password reset manually.</p>"
            ))
        return jsonify({'error': 'Too many failed attempts. This account is now locked. Please contact your admin to reset your password.'}), 403

    if attempts == 5:
        user.security_lockout_until = datetime.utcnow() + timedelta(seconds=60)
        db.session.commit()
        return jsonify({'error': 'Too many failed attempts. Please try again in 60s.', 'cooldown_seconds': 60}), 429

    db.session.commit()
    remaining_in_batch = (5 - attempts) if attempts < 5 else (10 - attempts)
    return jsonify({'error': f'Incorrect answer. {remaining_in_batch} attempt(s) remaining before a cooldown.'}), 401

@app.route('/api/auth/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    data = request.json or {}
    reset_token = data.get('reset_token', '')
    new_password = data.get('new_password', '')

    try:
        payload = jwt.decode(reset_token, app.config['JWT_SECRET'], algorithms=['HS256'])
        if not payload.get('pwd_reset'):
            return jsonify({'error': 'Invalid reset token'}), 401
        user_id = payload['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'This reset link expired. Please start over.'}), 401
    except Exception:
        return jsonify({'error': 'Invalid or expired reset token. Please start over.'}), 401

    pw_error = validate_password(new_password)
    if pw_error:
        return jsonify({'error': pw_error}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.set_password(new_password)
    db.session.commit()

    send_email(user.email, "Your Password Has Been Reset",
        make_email(
            "Password Reset Successful",
            f"<p>Hi <strong>{user.first_name}</strong>,</p>"
            "<p>Your EduSpace account password was just reset using your security question.</p>"
            "<p>If you did not make this change, please contact admin immediately.</p>"
        ))

    return jsonify({'message': 'Password reset successfully! You can now log in with your new password.'}), 200

@app.route('/api/admin/locked-accounts', methods=['GET'])
@token_required
@admin_required
def get_locked_accounts():
    locked = User.query.filter_by(security_locked=True).all()
    return jsonify([{
        'id': u.id,
        'full_name': f"{u.first_name} {u.last_name}",
        'email': u.email,
        'role': u.role,
        'failed_attempts': u.security_failed_attempts
    } for u in locked]), 200

@app.route('/api/admin/reset-user-password', methods=['POST'])
@token_required
@admin_required
def admin_reset_user_password():
    data = request.json or {}
    target_email = data.get('email', '').strip()
    new_password = data.get('new_password', '')

    if not target_email or not new_password:
        return jsonify({'error': 'Email and new password are required'}), 400

    pw_error = validate_password(new_password)
    if pw_error:
        return jsonify({'error': pw_error}), 400

    user = User.query.filter_by(email=target_email).first()
    if not user:
        return jsonify({'error': 'No user found with this email'}), 404

    user.set_password(new_password)
    # Unlock and clear all lockout state
    user.security_locked = False
    user.security_failed_attempts = 0
    user.security_lockout_until = None
    db.session.commit()

    send_email(user.email, "Your Password Was Reset by Admin",
        make_email(
            "Password Reset by Administrator",
            f"<p>Hi <strong>{user.first_name}</strong>,</p>"
            "<p>Your EduSpace account password has been reset by an administrator, "
            "and any account lockout has been cleared.</p>"
            "<p>If you did not request this, please contact admin immediately.</p>"
        ))

    return jsonify({'message': f'Password for {user.email} reset and account unlocked successfully!'}), 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Block unapproved faculty and students
    if user.role.lower() in ['faculty', 'student'] and not user.is_approved:
        return jsonify({'error': 'Your account is pending admin approval. You will be notified once approved.'}), 403

    # ── 2FA CHECK ───────────────────────────────────────────
    if user.two_fa_enabled:
        code = f"{random.randint(0, 999999):06d}"
        otp = OTPCode(
            user_id=user.id, code=code, purpose='login',
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.session.add(otp)
        db.session.commit()

        send_email(user.email, "Your EduSpace Login Code",
            make_email(
                "Your One-Time Login Code",
                f"<p>Hi <strong>{user.first_name}</strong>, use the code below to complete your login:</p>"
                f"<p style='font-size:32px;font-weight:800;letter-spacing:6px;color:#3b82f6;text-align:center;"
                f"padding:16px;background:#1e2433;border-radius:10px;'>{code}</p>"
                "<p>This code expires in <strong>5 minutes</strong>. If you didn't try to log in, you can ignore this email.</p>"
            ))

        return jsonify({
            'requires_2fa': True,
            'pre_auth_token': generate_pre_auth_token(user.id),
            'message': f'A 6-digit code has been sent to {user.email}'
        }), 200

    token = generate_token(user.id, user.role)
    db.session.add(LoginActivity(
        user_id=user.id, ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:255]
    ))
    db.session.commit()
    return jsonify({'token': token, 'user': {'id': user.id, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name, 'role': user.role}}), 200

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_login_otp():
    data = request.json or {}
    pre_auth_token = data.get('pre_auth_token', '')
    code = data.get('code', '').strip()

    try:
        payload = jwt.decode(pre_auth_token, app.config['JWT_SECRET'], algorithms=['HS256'])
        if not payload.get('pre_auth'):
            return jsonify({'error': 'Invalid token'}), 401
        user_id = payload['user_id']
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'This login attempt expired. Please log in again.'}), 401
    except Exception:
        return jsonify({'error': 'Invalid or expired token. Please log in again.'}), 401

    otp = OTPCode.query.filter_by(user_id=user_id, code=code, purpose='login', is_used=False)\
        .order_by(OTPCode.created_at.desc()).first()

    if not otp:
        return jsonify({'error': 'Invalid code'}), 400
    if otp.expires_at < datetime.utcnow():
        return jsonify({'error': 'This code has expired. Please request a new one.'}), 400

    otp.is_used = True
    db.session.commit()

    user = User.query.get(user_id)
    token = generate_token(user.id, user.role)
    db.session.add(LoginActivity(
        user_id=user.id, ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:255]
    ))
    db.session.commit()
    return jsonify({'token': token, 'user': {'id': user.id, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name, 'role': user.role}}), 200

@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_login_otp():
    data = request.json or {}
    pre_auth_token = data.get('pre_auth_token', '')

    try:
        payload = jwt.decode(pre_auth_token, app.config['JWT_SECRET'], algorithms=['HS256'])
        if not payload.get('pre_auth'):
            return jsonify({'error': 'Invalid token'}), 401
        user_id = payload['user_id']
    except Exception:
        return jsonify({'error': 'This login attempt expired. Please log in again.'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    code = f"{random.randint(0, 999999):06d}"
    otp = OTPCode(user_id=user.id, code=code, purpose='login', expires_at=datetime.utcnow() + timedelta(minutes=5))
    db.session.add(otp)
    db.session.commit()

    send_email(user.email, "Your New EduSpace Login Code",
        make_email(
            "Your One-Time Login Code",
            f"<p>Hi <strong>{user.first_name}</strong>, here's your new code:</p>"
            f"<p style='font-size:32px;font-weight:800;letter-spacing:6px;color:#3b82f6;text-align:center;"
            f"padding:16px;background:#1e2433;border-radius:10px;'>{code}</p>"
            "<p>This code expires in <strong>5 minutes</strong>.</p>"
        ))

    return jsonify({'message': f'A new code has been sent to {user.email}'}), 200

@app.route('/api/auth/2fa/toggle', methods=['POST'])
@token_required
def toggle_2fa():
    data = request.json or {}
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not data.get('password') or not user.check_password(data['password']):
        return jsonify({'error': 'Incorrect password'}), 401

    enable = bool(data.get('enable'))
    user.two_fa_enabled = enable
    db.session.commit()

    send_email(user.email, f"2FA {'Enabled' if enable else 'Disabled'} on Your Account",
        make_email(
            f"Two-Factor Authentication {'Enabled' if enable else 'Disabled'}",
            f"<p>Hi <strong>{user.first_name}</strong>, two-factor authentication has been "
            f"<strong>{'enabled' if enable else 'disabled'}</strong> on your EduSpace account.</p>"
            + ("<p>You'll now receive a login code by email each time you sign in.</p>" if enable else
               "<p>If you didn't make this change, please contact admin immediately and reset your password.</p>")
        ))

    return jsonify({'message': f"2FA {'enabled' if enable else 'disabled'} successfully!", 'two_fa_enabled': enable}), 200

@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile():
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id':           user.id,
        'email':        user.email,
        'first_name':   user.first_name,
        'last_name':    user.last_name,
        'role':         user.role,
        'phone':        user.phone        or '',
        'department':   user.department   or '',
        'enrollment_no':user.enrollment_no or '',
        'program':      user.program      or '',
        'batch_year':   user.batch_year   or '',
        'section':      user.section      or '',
        'bio':           user.bio          or '',
        'profile_photo': user.profile_photo  or '',
        'two_fa_enabled': user.two_fa_enabled or False,
        'member_since':  user.created_at.strftime('%b %Y') if user.created_at else 'N/A'
    }), 200

@app.route('/api/auth/profile', methods=['PUT'])
@token_required
def update_profile():
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.json
    # Validate phone if provided
    phone = data.get('phone', '')
    if phone:
        import re as _re
        digits = _re.sub(r'[\s\-\(\)]', '', phone).lstrip('+').lstrip('91').lstrip('0')
        if not _re.match(r'^[6-9]\d{9}$', digits):
            return jsonify({'error': 'Invalid phone number. Must be a 10-digit Indian mobile number.'}), 400
        data['phone'] = digits  # store normalised

    user.first_name    = data.get('first_name',    user.first_name)
    user.last_name     = data.get('last_name',     user.last_name)
    user.phone         = data.get('phone',         user.phone)
    user.department    = data.get('department',    user.department)
    user.enrollment_no = data.get('enrollment_no', user.enrollment_no)
    user.program       = data.get('program',       user.program)
    user.batch_year    = data.get('batch_year',    user.batch_year)
    user.section       = data.get('section',       user.section)
    user.bio           = data.get('bio',           user.bio)
    db.session.commit()
    log_activity(user.id, 'profile_update', 'Updated profile details')
    # Return updated profile
    return jsonify({
        'message': 'Profile updated successfully!',
        'profile': {
            'first_name': user.first_name, 'last_name': user.last_name,
            'phone': user.phone, 'department': user.department,
            'enrollment_no': user.enrollment_no, 'program': user.program,
            'batch_year': user.batch_year, 'section': user.section,
            'bio': user.bio, 'role': user.role, 'email': user.email,
            'member_since': user.created_at.strftime('%b %Y') if user.created_at else 'N/A'
        }
    }), 200


@app.route('/api/auth/profile/photo', methods=['POST'])
@token_required
def upload_profile_photo():
    data = request.json or {}
    photo = data.get('photo', '')
    if not photo:
        return jsonify({'error': 'No photo provided'}), 400
    # Limit size to ~2MB base64
    if len(photo) > 2_800_000:
        return jsonify({'error': 'Image too large. Please use an image under 2MB.'}), 400
    user = User.query.get(request.user_id)
    user.profile_photo = photo
    db.session.commit()
    return jsonify({'message': 'Photo updated!'}), 200

@app.route('/api/auth/profile/photo', methods=['DELETE'])
@token_required
def remove_profile_photo():
    user = User.query.get(request.user_id)
    user.profile_photo = None
    db.session.commit()
    return jsonify({'message': 'Photo removed'}), 200

@app.route('/api/auth/change-password', methods=['POST'])
@token_required
def change_password():
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.json
    if not user.check_password(data.get('old_password', '')):
        return jsonify({'error': 'Current password is incorrect'}), 400
    user.set_password(data['new_password'])
    db.session.commit()
    log_activity(user.id, 'password_change', 'Changed account password')
    return jsonify({'message': 'Password changed'}), 200

@app.route('/api/account/activity', methods=['GET'])
@token_required
def get_account_activity():
    """Returns the current user's last login, recent login history, and recent activity trail."""
    logins = LoginActivity.query.filter_by(user_id=request.user_id)\
        .order_by(LoginActivity.logged_in_at.desc()).limit(10).all()
    activity = ActivityLog.query.filter_by(user_id=request.user_id)\
        .order_by(ActivityLog.created_at.desc()).limit(30).all()

    last_login = logins[1].logged_in_at if len(logins) > 1 else None  # [0] is the current session

    return jsonify({
        'last_login': last_login.strftime('%d %b %Y, %I:%M %p') if last_login else 'This is your first login',
        'login_history': [{
            'id': l.id, 'logged_in_at': l.logged_in_at.strftime('%d %b %Y, %I:%M %p'),
            'ip_address': l.ip_address, 'user_agent': l.user_agent
        } for l in logins],
        'recent_activity': [{
            'id': a.id, 'action': a.action, 'description': a.description,
            'created_at': a.created_at.strftime('%d %b %Y, %I:%M %p')
        } for a in activity]
    }), 200

# ═══════════════════════════════════════════════════════════════
# ROOMS & TIME SLOTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/rooms', methods=['GET'])
@token_required
def get_rooms():
    rooms = Room.query.all()
    return jsonify([{'id': room.id, 'name': room.name, 'type': room.room_type, 'building': room.building, 'floor': room.floor, 'capacity': room.capacity, 'current_occupancy': room.current_occupancy} for room in rooms]), 200

@app.route('/api/rooms/<int:room_id>', methods=['GET'])
@token_required
def get_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    return jsonify({'id': room.id, 'name': room.name, 'type': room.room_type, 'building': room.building, 'floor': room.floor, 'capacity': room.capacity, 'current_occupancy': room.current_occupancy}), 200

@app.route('/api/rooms/<int:room_id>/checkin', methods=['POST'])
@token_required
def checkin(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    if room.current_occupancy < room.capacity:
        room.current_occupancy += 1
        db.session.commit()
        return jsonify({'message': 'Checked in', 'occupancy': room.current_occupancy}), 200
    else:
        return jsonify({'error': 'Room is full'}), 400

@app.route('/api/rooms/<int:room_id>/checkout', methods=['POST'])
@token_required
def checkout(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    if room.current_occupancy > 0:
        room.current_occupancy -= 1
        db.session.commit()
        return jsonify({'message': 'Checked out', 'occupancy': room.current_occupancy}), 200
    else:
        return jsonify({'error': 'No one to checkout'}), 400

@app.route('/api/time-slots', methods=['GET'])
@token_required
def get_time_slots():
    slots = sorted_time_slots()
    return jsonify([{'id': slot.id, 'start_time': slot.start_time, 'end_time': slot.end_time, 'slot_name': slot.slot_name} for slot in slots]), 200

# ═══════════════════════════════════════════════════════════════
# BOOKING REQUESTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/booking-requests', methods=['POST'])
@token_required
@faculty_required
def create_booking_request():
    data = request.json
    room = Room.query.get(data.get('room_id'))
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    time_slot = TimeSlot.query.get(data.get('time_slot_id'))
    if not time_slot:
        return jsonify({'error': 'Time slot not found'}), 404
    conflict = BookingRequest.query.filter_by(
        room_id=data.get('room_id'), date=data.get('date'), time_slot_id=data.get('time_slot_id')
    ).filter(BookingRequest.status.in_(['PENDING', 'APPROVED'])).first()
    if conflict:
        msg = 'Room already booked for this time slot' if conflict.status == 'APPROVED' \
            else 'Another faculty member already has a pending request for this room and time slot. Please wait for admin to decide, or choose another slot.'
        return jsonify({'error': msg}), 400
    
    request_obj = BookingRequest(faculty_id=request.user_id, room_id=data.get('room_id'), class_name=data.get('class_name'), date=datetime.strptime(data.get('date'), '%Y-%m-%d').date(), time_slot_id=data.get('time_slot_id'), number_of_students=data.get('number_of_students'))
    db.session.add(request_obj)
    db.session.commit()
    log_activity(request.user_id, 'booking_request', f'Requested {room.name} for {data.get("class_name")} on {request_obj.date}')
    return jsonify({'id': request_obj.id, 'status': request_obj.status, 'message': 'Booking request submitted'}), 201

@app.route('/api/my-booking-requests', methods=['GET'])
@token_required
@faculty_required
def get_my_booking_requests():
    requests = BookingRequest.query.filter_by(faculty_id=request.user_id).order_by(BookingRequest.created_at.desc()).all()
    return jsonify([{'id': r.id, 'class_name': r.class_name, 'room_name': r.room.name, 'date': r.date.strftime('%Y-%m-%d'), 'time_slot': r.time_slot.slot_name, 'status': r.status, 'number_of_students': r.number_of_students, 'rejection_reason': r.rejection_reason, 'admin_notes': r.admin_notes, 'created_at': r.created_at.isoformat()} for r in requests]), 200

@app.route('/api/my-bookings', methods=['GET'])
@token_required
def get_my_bookings():
    if request.user_role.lower() == 'faculty':
        bookings = Booking.query.filter_by(faculty_id=request.user_id).all()
    else:
        bookings = Booking.query.all()
    return jsonify([{'id': b.id, 'class_name': b.class_name, 'room_name': b.room.name, 'room_id': b.room.id, 'date': b.date.strftime('%Y-%m-%d'), 'time_slot': b.time_slot.slot_name, 'faculty_name': b.faculty.first_name + ' ' + b.faculty.last_name, 'status': b.status} for b in bookings]), 200

@app.route('/api/admin/pending-requests', methods=['GET'])
@token_required
@admin_required
def get_pending_requests():
    requests = BookingRequest.query.filter_by(status='PENDING').order_by(BookingRequest.created_at.asc()).all()
    return jsonify([{'id': r.id, 'class_name': r.class_name, 'faculty_name': r.faculty.first_name + ' ' + r.faculty.last_name, 'faculty_email': r.faculty.email, 'room_name': r.room.name, 'room_capacity': r.room.capacity, 'date': r.date.strftime('%Y-%m-%d'), 'time_slot': r.time_slot.slot_name, 'number_of_students': r.number_of_students, 'created_at': r.created_at.isoformat()} for r in requests]), 200

@app.route('/api/admin/booking-request/<int:request_id>/approve', methods=['POST'])
@token_required
@admin_required
def approve_booking_request(request_id):
    booking_request = BookingRequest.query.get(request_id)
    if not booking_request:
        return jsonify({'error': 'Request not found'}), 404
    if booking_request.status != 'PENDING':
        return jsonify({'error': 'Request is not pending'}), 400

    clash = Booking.query.filter_by(
        room_id=booking_request.room_id, date=booking_request.date,
        time_slot_id=booking_request.time_slot_id, status='ACTIVE'
    ).first()
    if clash:
        return jsonify({'error': f'Cannot approve — {booking_request.room.name} is already booked for this date and time slot (approved for another class). Reject this request or ask the faculty to choose another slot.'}), 400

    data = request.json
    booking = Booking(request_id=booking_request.id, faculty_id=booking_request.faculty_id, room_id=booking_request.room_id, class_name=booking_request.class_name, date=booking_request.date, time_slot_id=booking_request.time_slot_id)
    booking_request.status = 'APPROVED'
    booking_request.approved_at = datetime.utcnow()
    booking_request.approved_by = request.user_id
    booking_request.admin_notes = data.get('notes', '')
    db.session.add(booking)
    db.session.commit()
    # Send email to faculty
    faculty = User.query.get(booking_request.faculty_id)
    if faculty:
        send_email(faculty.email, "Booking Request Approved",
            make_email(
                "Your Room Booking is Confirmed!",
                f"<p>Hi <strong>{faculty.first_name}</strong>,</p>"
                f"<p>Your booking request for <strong>{booking_request.class_name}</strong> has been <strong>approved</strong>.</p>"
                f"<p>Room: <strong>{booking_request.room.name if booking_request.room else 'N/A'}</strong><br>"
                f"Date: <strong>{booking_request.date}</strong></p>",
                "View My Bookings", "http://localhost:5173"
            ))
    return jsonify({'message': 'Booking approved', 'booking_id': booking.id}), 200

@app.route('/api/admin/booking-request/<int:request_id>/reject', methods=['POST'])
@token_required
@admin_required
def reject_booking_request(request_id):
    booking_request = BookingRequest.query.get(request_id)
    if not booking_request:
        return jsonify({'error': 'Request not found'}), 404
    if booking_request.status != 'PENDING':
        return jsonify({'error': 'Request is not pending'}), 400
    data = request.json
    booking_request.status = 'REJECTED'
    booking_request.rejection_reason = data.get('reason', '')
    db.session.commit()
    # Send email to faculty
    faculty = User.query.get(booking_request.faculty_id)
    if faculty:
        send_email(faculty.email, "Booking Request Update",
            make_email(
                "Booking Request Rejected",
                f"<p>Hi <strong>{faculty.first_name}</strong>,</p>"
                f"<p>Your booking request for <strong>{booking_request.class_name}</strong> was <strong>rejected</strong>.</p>"
                f"<p>Reason: <em>{data.get('reason', 'No reason provided')}</em></p>"
                "<p>Please submit a new request with adjusted details.</p>",
                "Submit New Request", "http://localhost:5173"
            ))
    return jsonify({'message': 'Booking rejected'}), 200

@app.route('/api/admin/all-bookings', methods=['GET'])
@token_required
@admin_required
def get_all_bookings():
    bookings = Booking.query.order_by(Booking.date.asc()).all()
    return jsonify([{'id': b.id, 'class_name': b.class_name, 'faculty_name': b.faculty.first_name + ' ' + b.faculty.last_name, 'room_name': b.room.name, 'date': b.date.strftime('%Y-%m-%d'), 'time_slot': b.time_slot.slot_name, 'status': b.status} for b in bookings]), 200

# ═══════════════════════════════════════════════════════════════
# ATTENDANCE TRACKING
# ═══════════════════════════════════════════════════════════════

@app.route('/api/booking/<int:booking_id>/attendance', methods=['GET'])
@token_required
@faculty_required
def get_attendance(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    if booking.faculty_id != request.user_id and request.user_role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    attendance = Attendance.query.filter_by(booking_id=booking_id).all()
    return jsonify([{'id': a.id, 'student_id': a.student_id, 'student_name': a.student.first_name + ' ' + a.student.last_name, 'student_email': a.student.email, 'status': a.status, 'marked_at': a.marked_at.isoformat() if a.marked_at else None} for a in attendance]), 200

@app.route('/api/booking/<int:booking_id>/mark-attendance', methods=['POST'])
@token_required
@faculty_required
def mark_attendance(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    if booking.faculty_id != request.user_id and request.user_role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    student_id = data.get('student_id')
    status = data.get('status')
    if status not in ['PRESENT', 'ABSENT', 'LATE']:
        return jsonify({'error': 'Invalid status'}), 400
    attendance = Attendance.query.filter_by(booking_id=booking_id, student_id=student_id).first()
    if not attendance:
        attendance = Attendance(booking_id=booking_id, student_id=student_id, status=status, marked_by=request.user_id)
        db.session.add(attendance)
    else:
        attendance.status = status
        attendance.marked_by = request.user_id
        attendance.marked_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Attendance marked'}), 200

@app.route('/api/booking/<int:booking_id>/attendance-summary', methods=['GET'])
@token_required
@faculty_required
def get_attendance_summary(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    if booking.faculty_id != request.user_id and request.user_role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    attendance = Attendance.query.filter_by(booking_id=booking_id).all()
    present = len([a for a in attendance if a.status == 'PRESENT'])
    absent = len([a for a in attendance if a.status == 'ABSENT'])
    late = len([a for a in attendance if a.status == 'LATE'])
    total = len(attendance)
    return jsonify({'total_students': total, 'present': present, 'absent': absent, 'late': late, 'attendance_percentage': round((present / total * 100) if total > 0 else 0, 2)}), 200

# ═══════════════════════════════════════════════════════════════
# STUDENT FEEDBACK
# ═══════════════════════════════════════════════════════════════

FEEDBACK_TYPES = ['room_condition','booking_process','faculty_experience','technical_issue','general_suggestion']

@app.route('/api/feedback', methods=['POST'])
@token_required
@student_required
def submit_feedback():
    """Students submit general or booking-linked feedback"""
    import json as json_lib
    data = request.json or {}
    rating = data.get('rating')
    if not rating or not (1 <= float(rating) <= 5):
        return jsonify({'error': 'Rating between 1-5 is required'}), 400
    if not data.get('comment', '').strip():
        return jsonify({'error': 'Please write a comment'}), 400
    fb_type = data.get('feedback_type', 'general_suggestion')
    if fb_type not in FEEDBACK_TYPES:
        fb_type = 'general_suggestion'
    feedback = StudentFeedback(
        student_id=request.user_id,
        booking_id=data.get('booking_id'),
        feedback_type=fb_type,
        rating=float(rating),
        comment=data.get('comment', '').strip(),
        is_anonymous=bool(data.get('is_anonymous', False)),
    )
    db.session.add(feedback)
    db.session.commit()
    return jsonify({'message': 'Thank you for your feedback!', 'id': feedback.id}), 201

@app.route('/api/feedback/my', methods=['GET'])
@token_required
@student_required
def my_feedback():
    """Students view their own submitted feedback"""
    feedbacks = StudentFeedback.query.filter_by(student_id=request.user_id)        .order_by(StudentFeedback.created_at.desc()).all()
    return jsonify([{
        'id': f.id, 'feedback_type': f.feedback_type, 'rating': f.rating,
        'comment': f.comment, 'is_anonymous': f.is_anonymous,
        'created_at': f.created_at.strftime('%d %b %Y, %H:%M')
    } for f in feedbacks]), 200

@app.route('/api/admin/all-feedback', methods=['GET'])
@token_required
@admin_required
def get_all_feedback():
    """Admin only - view all student feedback"""
    feedback = StudentFeedback.query.order_by(StudentFeedback.created_at.desc()).all()
    result = []
    for f in feedback:
        student_name = 'Anonymous' if f.is_anonymous else f'{f.student.first_name} {f.student.last_name}'
        student_email = '' if f.is_anonymous else f.student.email
        result.append({
            'id': f.id, 'feedback_type': f.feedback_type, 'rating': f.rating,
            'comment': f.comment, 'is_anonymous': f.is_anonymous,
            'student_name': student_name, 'student_email': student_email,
            'booking_id': f.booking_id,
            'created_at': f.created_at.strftime('%d %b %Y, %H:%M')
        })
    return jsonify(result), 200

@app.route('/api/faculty/feedback', methods=['GET'])
@token_required
@faculty_required
def faculty_feedback():
    """Faculty views feedback on their bookings"""
    my_booking_ids = [b.id for b in Booking.query.filter_by(faculty_id=request.user_id).all()]
    feedbacks = StudentFeedback.query.filter(
        StudentFeedback.booking_id.in_(my_booking_ids)
    ).order_by(StudentFeedback.created_at.desc()).all()
    return jsonify([{
        'id': f.id, 'feedback_type': f.feedback_type, 'rating': f.rating,
        'comment': f.comment,
        'student_name': 'Anonymous' if f.is_anonymous else f'{f.student.first_name} {f.student.last_name}',
        'created_at': f.created_at.strftime('%d %b %Y, %H:%M')
    } for f in feedbacks]), 200

@app.route('/api/admin/feedback-summary', methods=['GET'])
@token_required
@admin_required
def get_feedback_summary():
    """Admin only - feedback statistics"""
    feedback = StudentFeedback.query.all()
    if not feedback:
        return jsonify({'total_feedback': 0, 'average_rating': 0, 'rating_distribution': {}}), 200
    ratings = [f.rating for f in feedback]
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[i] = len([r for r in ratings if r == i])
    return jsonify({'total_feedback': len(feedback), 'average_rating': round(sum(ratings) / len(ratings), 2), 'rating_distribution': rating_dist}), 200

# ═══════════════════════════════════════════════════════════════


@app.route('/api/students', methods=['GET'])
@token_required
def get_all_students():
    """Faculty/Admin: get list of all registered students"""
    students = User.query.filter(User.role.ilike('student')).all()
    return jsonify([{
        'id': s.id,
        'first_name': s.first_name,
        'last_name': s.last_name,
        'email': s.email,
        'full_name': f"{s.first_name} {s.last_name}"
    } for s in students]), 200

@app.route('/api/admin/faculty-list', methods=['GET'])
@token_required
@admin_required
def get_faculty_list():
    """Admin: get list of all approved faculty for dropdowns"""
    faculty = User.query.filter(User.role.ilike('faculty'), User.is_approved == True).all()
    return jsonify([{
        'id': f.id,
        'full_name': f"{f.first_name} {f.last_name}",
        'email': f.email
    } for f in faculty]), 200

# ═══════════════════════════════════════════════════════════════
# ANALYTICS DASHBOARD
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/analytics', methods=['GET'])
@token_required
@admin_required
def get_analytics():
    from sqlalchemy import func, case

    # ── USER STATS ────────────────────────────────────────────
    total_users    = User.query.count()
    total_students = User.query.filter(User.role.ilike('student'), User.is_approved==True).count()
    total_faculty  = User.query.filter(User.role.ilike('faculty'), User.is_approved==True).count()
    pending_approvals = User.query.filter(User.is_approved==False).count()

    # New users per month (last 6 months)
    from datetime import timedelta
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_users = {}
    for i in range(5, -1, -1):
        month_start = (datetime.utcnow().replace(day=1) - timedelta(days=30*i))
        month_key   = month_start.strftime('%b %Y')
        count = User.query.filter(
            User.created_at >= month_start,
            User.created_at < month_start + timedelta(days=31)
        ).count()
        monthly_users[month_key] = count

    # ── BOOKING STATS ─────────────────────────────────────────
    total_bookings  = Booking.query.count()
    total_requests  = BookingRequest.query.count()
    approved_reqs   = BookingRequest.query.filter_by(status='approved').count()
    rejected_reqs   = BookingRequest.query.filter_by(status='rejected').count()
    pending_reqs    = BookingRequest.query.filter_by(status='pending').count()
    approval_rate   = round(approved_reqs / total_requests * 100, 1) if total_requests > 0 else 0

    # Bookings by day of week
    day_counts = {d: 0 for d in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']}
    for b in Booking.query.all():
        try:
            day = datetime.strptime(str(b.date), '%Y-%m-%d').strftime('%a')
            day_counts[day] = day_counts.get(day, 0) + 1
        except: pass

    # ── ROOM STATS ────────────────────────────────────────────
    rooms = Room.query.all()
    room_usage = []
    for r in rooms:
        count = Booking.query.filter_by(room_id=r.id).count()
        room_usage.append({'room': r.name, 'bookings': count, 'capacity': r.capacity, 'type': r.room_type})
    room_usage.sort(key=lambda x: x['bookings'], reverse=True)

    # ── ATTENDANCE STATS ──────────────────────────────────────
    total_att     = Attendance.query.count()
    present_count = Attendance.query.filter_by(status='PRESENT').count()
    absent_count  = Attendance.query.filter_by(status='ABSENT').count()
    late_count    = Attendance.query.filter_by(status='LATE').count()
    att_pct       = round((present_count + late_count*0.5) / total_att * 100, 1) if total_att > 0 else 0

    # ── GEOFENCE STATS ────────────────────────────────────────
    total_geo     = GeofenceLog.query.count()
    on_campus     = GeofenceLog.query.filter_by(is_within=True).count()
    off_campus    = total_geo - on_campus

    # ── FEEDBACK STATS ────────────────────────────────────────
    total_feedback = StudentFeedback.query.count()
    avg_rating     = db.session.query(func.avg(StudentFeedback.rating)).scalar()
    avg_rating     = round(float(avg_rating), 1) if avg_rating else 0

    # Feedback by type
    fb_by_type = {}
    for f in StudentFeedback.query.all():
        fb_by_type[f.feedback_type] = fb_by_type.get(f.feedback_type, 0) + 1

    # ── LOST & FOUND STATS ────────────────────────────────────
    lf_total   = LostFoundItem.query.count()
    lf_lost    = LostFoundItem.query.filter_by(item_type='lost',  status='open').count()
    lf_found   = LostFoundItem.query.filter_by(item_type='found', status='open').count()
    lf_claimed = LostFoundItem.query.filter_by(status='claimed').count()

    return jsonify({
        'users': {
            'total': total_users, 'students': total_students,
            'faculty': total_faculty, 'pending': pending_approvals,
            'monthly': monthly_users
        },
        'bookings': {
            'total': total_bookings, 'requests': total_requests,
            'approved': approved_reqs, 'rejected': rejected_reqs,
            'pending': pending_reqs, 'approval_rate': approval_rate,
            'by_day': day_counts
        },
        'rooms': room_usage,
        'attendance': {
            'total': total_att, 'present': present_count,
            'absent': absent_count, 'late': late_count,
            'percentage': att_pct
        },
        'geofence': {'total': total_geo, 'on_campus': on_campus, 'off_campus': off_campus},
        'feedback': {'total': total_feedback, 'avg_rating': avg_rating, 'by_type': fb_by_type},
        'lost_found': {'total': lf_total, 'lost': lf_lost, 'found': lf_found, 'claimed': lf_claimed}
    }), 200


# ═══════════════════════════════════════════════════════════════
# GRIEVANCE / COMPLAINT SYSTEM
# ═══════════════════════════════════════════════════════════════

GRIEVANCE_CATEGORIES = ['hostel', 'academic', 'facility', 'ragging', 'harassment', 'other']
GRIEVANCE_PRIORITIES  = ['low', 'medium', 'high', 'urgent']

def grievance_to_dict(g, viewer_role='student'):
    is_admin_view = viewer_role == 'admin'
    return {
        'id': g.id,
        'category': g.category,
        'priority': g.priority,
        'subject': g.subject,
        'description': g.description,
        'is_anonymous': g.is_anonymous,
        'status': g.status,
        'admin_reply': g.admin_reply,
        'student_name': 'Anonymous' if (g.is_anonymous and not is_admin_view) else f"{g.student.first_name} {g.student.last_name}",
        'student_email': None if (g.is_anonymous and not is_admin_view) else g.student.email,
        'resolved_by': f"{g.resolver.first_name} {g.resolver.last_name}" if g.resolver else None,
        'created_at': g.created_at.strftime('%d %b %Y, %H:%M'),
        'updated_at': g.updated_at.strftime('%d %b %Y, %H:%M'),
    }

@app.route('/api/grievances', methods=['POST'])
@token_required
def create_grievance():
    data = request.json or {}
    category = data.get('category', '')
    subject  = data.get('subject', '').strip()
    description = data.get('description', '').strip()

    if category not in GRIEVANCE_CATEGORIES:
        return jsonify({'error': 'Invalid category'}), 400
    if not subject or not description:
        return jsonify({'error': 'Subject and description are required'}), 400

    priority = data.get('priority', 'medium')
    if priority not in GRIEVANCE_PRIORITIES:
        priority = 'medium'

    g = Grievance(
        student_id=request.user_id,
        category=category,
        priority=priority,
        subject=subject,
        description=description,
        is_anonymous=bool(data.get('is_anonymous', False)),
    )
    db.session.add(g)
    db.session.commit()
    log_activity(request.user_id, 'grievance', f'Submitted a {category} grievance: "{subject}"')

    # Notify admins
    for adm in User.query.filter(User.role.ilike('admin')).all():
        send_email(adm.email, f"New Grievance Submitted — {priority.upper()} Priority",
            make_email(
                "New Grievance Needs Attention",
                f"<p>A new <strong>{category.capitalize()}</strong> grievance has been submitted with "
                f"<strong>{priority.capitalize()}</strong> priority.</p>"
                f"<p><strong>Subject:</strong> {subject}</p>",
                "View Grievances", "http://localhost:5173"
            ))

    return jsonify({'message': 'Grievance submitted successfully!', 'id': g.id}), 201

@app.route('/api/grievances/my', methods=['GET'])
@token_required
def my_grievances():
    items = Grievance.query.filter_by(student_id=request.user_id).order_by(Grievance.created_at.desc()).all()
    return jsonify([grievance_to_dict(g, 'student') for g in items]), 200

@app.route('/api/admin/grievances', methods=['GET'])
@token_required
@admin_required
def all_grievances():
    status_filter   = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    priority_filter = request.args.get('priority', '')

    q = Grievance.query
    if status_filter:   q = q.filter_by(status=status_filter)
    if category_filter: q = q.filter_by(category=category_filter)
    if priority_filter: q = q.filter_by(priority=priority_filter)

    items = q.order_by(Grievance.created_at.desc()).all()
    return jsonify([grievance_to_dict(g, 'admin') for g in items]), 200

@app.route('/api/admin/grievances/<int:grievance_id>', methods=['PUT'])
@token_required
@admin_required
def update_grievance(grievance_id):
    g = Grievance.query.get(grievance_id)
    if not g:
        return jsonify({'error': 'Grievance not found'}), 404

    data = request.json or {}
    new_status = data.get('status')
    if new_status and new_status not in ['pending', 'in_progress', 'resolved', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400

    if new_status:
        g.status = new_status
        g.resolved_by = request.user_id
    if 'admin_reply' in data:
        g.admin_reply = data['admin_reply'].strip()

    db.session.commit()

    # Notify student of status change (skip if anonymous, since email is still on file but be safe)
    student = User.query.get(g.student_id)
    if student and new_status:
        status_labels = {
            'pending': 'Pending', 'in_progress': 'In Progress',
            'resolved': 'Resolved', 'rejected': 'Rejected'
        }
        send_email(student.email, f"Grievance Update — {status_labels.get(new_status, new_status)}",
            make_email(
                "Your Grievance Has Been Updated",
                f"<p>Your grievance <strong>'{g.subject}'</strong> status has changed to "
                f"<strong>{status_labels.get(new_status, new_status)}</strong>.</p>"
                + (f"<p><strong>Admin Reply:</strong> {g.admin_reply}</p>" if g.admin_reply else ""),
                "View My Grievances", "http://localhost:5173"
            ))

    return jsonify({'message': 'Grievance updated successfully!'}), 200

@app.route('/api/admin/grievances/stats', methods=['GET'])
@token_required
@admin_required
def grievance_stats():
    total      = Grievance.query.count()
    pending    = Grievance.query.filter_by(status='pending').count()
    in_progress= Grievance.query.filter_by(status='in_progress').count()
    resolved   = Grievance.query.filter_by(status='resolved').count()
    rejected   = Grievance.query.filter_by(status='rejected').count()
    urgent     = Grievance.query.filter_by(priority='urgent').filter(Grievance.status != 'resolved').count()
    return jsonify({
        'total': total, 'pending': pending, 'in_progress': in_progress,
        'resolved': resolved, 'rejected': rejected, 'urgent_open': urgent
    }), 200


# ═══════════════════════════════════════════════════════════════
# TIMETABLE MANAGER
# ═══════════════════════════════════════════════════════════════

DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

def timetable_to_dict(t):
    return {
        'id': t.id,
        'day_of_week': t.day_of_week,
        'time_slot_id': t.time_slot_id,
        'time_slot': t.time_slot.slot_name if t.time_slot else '',
        'start_time': t.time_slot.start_time if t.time_slot else '',
        'end_time': t.time_slot.end_time if t.time_slot else '',
        'subject_name': t.subject_name,
        'faculty_id': t.faculty_id,
        'faculty_name': f"{t.faculty.first_name} {t.faculty.last_name}" if t.faculty else 'TBA',
        'room_id': t.room_id,
        'room_name': t.room.name if t.room else 'TBA',
        'program': t.program,
        'batch_year': t.batch_year,
        'section': t.section,
    }

@app.route('/api/admin/timetable', methods=['GET'])
@token_required
@admin_required
def get_all_timetable():
    program    = request.args.get('program', '')
    batch_year = request.args.get('batch_year', '')
    section    = request.args.get('section', '')

    q = TimetableEntry.query
    if program:    q = q.filter_by(program=program)
    if batch_year: q = q.filter_by(batch_year=batch_year)
    if section:    q = q.filter_by(section=section)

    entries = q.order_by(TimetableEntry.day_of_week, TimetableEntry.time_slot_id).all()
    return jsonify([timetable_to_dict(t) for t in entries]), 200

@app.route('/api/admin/timetable', methods=['POST'])
@token_required
@admin_required
def create_timetable_entry():
    data = request.json or {}
    day = data.get('day_of_week', '')
    if day not in DAYS_OF_WEEK:
        return jsonify({'error': 'Invalid day of week'}), 400
    if not data.get('time_slot_id') or not data.get('subject_name') or not data.get('program') \
       or not data.get('batch_year') or not data.get('section'):
        return jsonify({'error': 'time_slot_id, subject_name, program, batch_year and section are required'}), 400

    # Prevent duplicate class for same program/batch/section/day/slot
    clash = TimetableEntry.query.filter_by(
        day_of_week=day, time_slot_id=data['time_slot_id'],
        program=data['program'], batch_year=data['batch_year'], section=data['section']
    ).first()
    if clash:
        return jsonify({'error': f'A class already exists for this slot on {day} for this batch/section'}), 400

    entry = TimetableEntry(
        day_of_week=day,
        time_slot_id=data['time_slot_id'],
        subject_name=data['subject_name'].strip(),
        faculty_id=data.get('faculty_id') or None,
        room_id=data.get('room_id') or None,
        program=data['program'].strip(),
        batch_year=data['batch_year'].strip(),
        section=data['section'].strip().upper(),
        created_by=request.user_id
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({'message': 'Timetable entry created!', 'id': entry.id}), 201

@app.route('/api/admin/timetable/<int:entry_id>', methods=['PUT'])
@token_required
@admin_required
def update_timetable_entry(entry_id):
    entry = TimetableEntry.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    data = request.json or {}

    if 'day_of_week' in data:
        if data['day_of_week'] not in DAYS_OF_WEEK:
            return jsonify({'error': 'Invalid day of week'}), 400
        entry.day_of_week = data['day_of_week']
    if 'time_slot_id' in data:  entry.time_slot_id  = data['time_slot_id']
    if 'subject_name' in data:  entry.subject_name  = data['subject_name'].strip()
    if 'faculty_id' in data:    entry.faculty_id    = data['faculty_id'] or None
    if 'room_id' in data:       entry.room_id       = data['room_id'] or None
    if 'program' in data:       entry.program       = data['program'].strip()
    if 'batch_year' in data:    entry.batch_year    = data['batch_year'].strip()
    if 'section' in data:       entry.section       = data['section'].strip().upper()

    db.session.commit()
    return jsonify({'message': 'Timetable entry updated!'}), 200

@app.route('/api/admin/timetable/<int:entry_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_timetable_entry(entry_id):
    entry = TimetableEntry.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'Timetable entry deleted!'}), 200

@app.route('/api/timetable/my', methods=['GET'])
@token_required
def my_timetable():
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role and user.role.lower() == 'faculty':
        entries = TimetableEntry.query.filter_by(faculty_id=user.id)\
            .order_by(TimetableEntry.day_of_week, TimetableEntry.time_slot_id).all()
    else:
        # Student — filter by their own program/batch_year/section
        if not user.program or not user.batch_year or not user.section:
            return jsonify({
                'entries': [],
                'profile_incomplete': True,
                'message': 'Please complete your Program, Batch Year and Section in My Account to see your timetable.'
            }), 200
        entries = TimetableEntry.query.filter_by(
            program=user.program, batch_year=user.batch_year, section=user.section
        ).order_by(TimetableEntry.day_of_week, TimetableEntry.time_slot_id).all()

    return jsonify({'entries': [timetable_to_dict(t) for t in entries], 'profile_incomplete': False}), 200

@app.route('/api/timetable/filters', methods=['GET'])
@token_required
@admin_required
def timetable_filter_options():
    programs = [p[0] for p in db.session.query(User.program).filter(User.program.isnot(None)).distinct().all() if p[0]]
    batches  = [b[0] for b in db.session.query(User.batch_year).filter(User.batch_year.isnot(None)).distinct().all() if b[0]]
    sections = [s[0] for s in db.session.query(User.section).filter(User.section.isnot(None)).distinct().all() if s[0]]
    return jsonify({'programs': programs, 'batch_years': batches, 'sections': sections}), 200


# ═══════════════════════════════════════════════════════════════
# HOLIDAYS (admin-managed, affects attendance window calculation)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/holidays', methods=['GET'])
@token_required
def list_holidays():
    holidays = Holiday.query.order_by(Holiday.date).all()
    return jsonify([{'id': h.id, 'date': h.date.strftime('%Y-%m-%d'), 'name': h.name} for h in holidays]), 200

@app.route('/api/admin/holidays', methods=['POST'])
@token_required
@admin_required
def add_holiday():
    data = request.json or {}
    date_str = data.get('date', '')
    name = (data.get('name') or '').strip()
    if not date_str or not name:
        return jsonify({'error': 'date and name are required'}), 400
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    if Holiday.query.filter_by(date=d).first():
        return jsonify({'error': 'A holiday is already set for that date'}), 400
    db.session.add(Holiday(date=d, name=name, added_by=request.user_id))
    db.session.commit()
    return jsonify({'message': f'Holiday "{name}" added for {date_str}'}), 201

@app.route('/api/admin/holidays/<int:holiday_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_holiday(holiday_id):
    h = Holiday.query.get(holiday_id)
    if not h:
        return jsonify({'error': 'Holiday not found'}), 404
    db.session.delete(h)
    db.session.commit()
    return jsonify({'message': 'Holiday removed'}), 200


# ═══════════════════════════════════════════════════════════════
# CLASS ATTENDANCE (timetable-based, replaces booking-based marking)
# ═══════════════════════════════════════════════════════════════

WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
NON_WORKING_WEEKDAYS = {'Sunday'}   # fixed weekly off; admin can add extra holidays on top

def is_working_day(d):
    if WEEKDAYS[d.weekday()] in NON_WORKING_WEEKDAYS:
        return False
    return Holiday.query.filter_by(date=d).first() is None

def next_working_day(d):
    nxt = d + timedelta(days=1)
    while not is_working_day(nxt):
        nxt += timedelta(days=1)
    return nxt

def slot_minutes(slot, which='start'):
    """Returns minutes-since-midnight for a slot's start or end, parsed from slot_name."""
    if not slot or not slot.slot_name:
        return None
    parts = slot.slot_name.split('-')
    text = (parts[0] if which == 'start' else parts[-1]).strip()
    try:
        t = datetime.strptime(text, '%I:%M %p')
        return t.hour * 60 + t.minute
    except (ValueError, TypeError):
        return None

def current_occurrence(entry, now):
    """For a TimetableEntry, find the most recent occurrence (today or yesterday)
    whose weekday matches entry.day_of_week, and return (class_date, window_open, window_close)
    where the marking window is [class_start, next_working_day's same start time)."""
    start_min = slot_minutes(entry.time_slot, 'start')
    if start_min is None:
        return None
    target_weekday = entry.day_of_week
    for days_back in [0, 1, 2]:   # look back up to 2 days to cover a holiday/weekend pushing the window further
        candidate_date = (now - timedelta(days=days_back)).date()
        if WEEKDAYS[candidate_date.weekday()] == target_weekday:
            window_open = datetime.combine(candidate_date, datetime.min.time()) + timedelta(minutes=start_min)
            close_date = next_working_day(candidate_date)
            window_close = datetime.combine(close_date, datetime.min.time()) + timedelta(minutes=start_min)
            if window_open <= now < window_close:
                return candidate_date, window_open, window_close
    return None

@app.route('/api/faculty/attendance/markable', methods=['GET'])
@token_required
@faculty_required
def markable_classes():
    """Lists this faculty's classes whose attendance window is currently open
    (from class start time until the same time the next day)."""
    entries = TimetableEntry.query.filter_by(faculty_id=request.user_id).all()
    now = datetime.utcnow()
    result = []
    for e in entries:
        occ = current_occurrence(e, now)
        if not occ:
            continue
        class_date, window_open, window_close = occ
        already = ClassAttendance.query.filter_by(timetable_entry_id=e.id, class_date=class_date).first() is not None
        result.append({
            'timetable_entry_id': e.id,
            'subject_name': e.subject_name,
            'program': e.program, 'batch_year': e.batch_year, 'section': e.section,
            'day_of_week': e.day_of_week,
            'slot_name': e.time_slot.slot_name if e.time_slot else '',
            'class_date': class_date.strftime('%Y-%m-%d'),
            'window_closes_at': window_close.isoformat(),
            'already_marked': already,
        })
    return jsonify(result), 200

@app.route('/api/faculty/attendance/<int:entry_id>/roster', methods=['GET'])
@token_required
@faculty_required
def attendance_roster(entry_id):
    """Returns the enrolled student roster for this class with auto-suggested status
    (present/out_of_campus, derived from GPS geofence check-ins), or saved status if already marked."""
    entry = TimetableEntry.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Class not found'}), 404
    if entry.faculty_id != request.user_id:
        return jsonify({'error': 'Not your class'}), 403

    date_str = request.args.get('date', '')
    try:
        class_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400

    now = datetime.utcnow()
    occ = current_occurrence(entry, now)
    if not occ:
        return jsonify({'error': 'This class is not currently open for attendance. You can mark it from when it starts until the same time the next day.'}), 400
    occ_date, window_open, window_close = occ
    if class_date and class_date != occ_date:
        return jsonify({'error': 'This class is not currently open for attendance for that date.'}), 400
    class_date = occ_date

    students = User.query.filter_by(
        role='student', program=entry.program, batch_year=entry.batch_year,
        section=entry.section, is_approved=True
    ).order_by(User.first_name).all()

    start_min = slot_minutes(entry.time_slot, 'start')
    end_min = slot_minutes(entry.time_slot, 'end') or (start_min + 60 if start_min is not None else None)
    slot_start_dt = datetime.combine(class_date, datetime.min.time()) + timedelta(minutes=start_min or 0)
    slot_end_dt = datetime.combine(class_date, datetime.min.time()) + timedelta(minutes=end_min or 0)

    existing = {a.student_id: a for a in ClassAttendance.query.filter_by(
        timetable_entry_id=entry_id, class_date=class_date).all()}

    roster = []
    for s in students:
        if s.id in existing:
            a = existing[s.id]
            status, auto_status = a.status, a.auto_status
        else:
            checked_in = GeofenceLog.query.filter(
                GeofenceLog.student_id == s.id, GeofenceLog.is_within == True,
                GeofenceLog.created_at >= slot_start_dt, GeofenceLog.created_at <= slot_end_dt
            ).first() is not None
            auto_status = 'present' if checked_in else 'out_of_campus'
            status = auto_status
        roster.append({
            'student_id': s.id, 'name': f'{s.first_name} {s.last_name}',
            'email': s.email, 'enrollment_no': s.enrollment_no,
            'status': status, 'auto_status': auto_status
        })

    return jsonify({
        'class_date': class_date.strftime('%Y-%m-%d'),
        'window_closes_at': window_close.isoformat(),
        'roster': roster
    }), 200

@app.route('/api/faculty/attendance/save', methods=['POST'])
@token_required
@faculty_required
def save_class_attendance():
    data = request.json or {}
    entry_id = data.get('timetable_entry_id')
    records = data.get('records', [])

    entry = TimetableEntry.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Class not found'}), 404
    if entry.faculty_id != request.user_id:
        return jsonify({'error': 'Not your class'}), 403

    now = datetime.utcnow()
    occ = current_occurrence(entry, now)
    if not occ:
        return jsonify({'error': 'The attendance window for this class has closed.'}), 400
    class_date, _, _ = occ

    valid_statuses = {'present', 'absent', 'out_of_campus'}
    saved = 0
    for r in records:
        student_id = r.get('student_id')
        status = r.get('status')
        if status not in valid_statuses or not student_id:
            continue
        row = ClassAttendance.query.filter_by(
            timetable_entry_id=entry_id, student_id=student_id, class_date=class_date
        ).first()
        if row:
            if row.status != status:
                row.override_reason = r.get('override_reason') or row.override_reason
            row.status = status
            row.marked_by = request.user_id
            row.marked_at = now
        else:
            db.session.add(ClassAttendance(
                timetable_entry_id=entry_id, student_id=student_id, class_date=class_date,
                status=status, auto_status=r.get('auto_status'),
                override_reason=r.get('override_reason'), marked_by=request.user_id, marked_at=now
            ))
        saved += 1
    db.session.commit()
    log_activity(request.user_id, 'attendance_marked', f'Marked attendance for {entry.subject_name} ({saved} student(s)) on {class_date}')
    return jsonify({'message': f'Attendance saved for {saved} student(s).'}), 200


# ═══════════════════════════════════════════════════════════════
# SPORTS / LIBRARY FACILITY BOOKING (instant self-service)
# ═══════════════════════════════════════════════════════════════

FACILITY_TYPES = ['Sports Facility', 'Library Seat']
MAX_GROUP_SEATS = 4   # max seats one student can book together for group study

def get_taken_seats(room_id, target_date, time_slot_id):
    """Returns a set of seat numbers (ints) already booked for this room/date/slot."""
    bookings = FacilityBooking.query.filter_by(
        room_id=room_id, date=target_date, time_slot_id=time_slot_id, status='confirmed'
    ).all()
    taken = set()
    for b in bookings:
        if b.seat_numbers:
            for s in b.seat_numbers.split(','):
                s = s.strip()
                if s.isdigit():
                    taken.add(int(s))
    return taken

@app.route('/api/facilities', methods=['GET'])
@token_required
def get_facilities():
    """List all sports/library rooms with their slot-wise availability for a given date."""
    date_str = request.args.get('date', '')
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    rooms = Room.query.filter(Room.room_type.in_(FACILITY_TYPES)).all()
    slots = sorted_time_slots()

    result = []
    for r in rooms:
        is_library = (r.room_type == 'Library Seat')
        slot_info = []
        for s in slots:
            if is_library:
                taken = get_taken_seats(r.id, target_date, s.id)
                available_seats = [n for n in range(1, r.capacity + 1) if n not in taken]
                slot_info.append({
                    'time_slot_id': s.id,
                    'slot_name': s.slot_name or f"{s.start_time} - {s.end_time}",
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'booked': len(taken),
                    'capacity': r.capacity,
                    'available': len(available_seats),
                    'available_seat_numbers': available_seats,
                    'is_full': len(available_seats) == 0,
                })
            else:
                booked_count = FacilityBooking.query.filter_by(
                    room_id=r.id, date=target_date, time_slot_id=s.id, status='confirmed'
                ).count()
                slot_info.append({
                    'time_slot_id': s.id,
                    'slot_name': s.slot_name or f"{s.start_time} - {s.end_time}",
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'booked': booked_count,
                    'capacity': r.capacity,
                    'available': max(0, r.capacity - booked_count),
                    'is_full': booked_count >= r.capacity
                })
        result.append({
            'id': r.id, 'name': r.name, 'room_type': r.room_type,
            'building': r.building, 'floor': r.floor, 'capacity': r.capacity,
            'max_group_seats': MAX_GROUP_SEATS if is_library else 1,
            'slots': slot_info
        })
    return jsonify({'date': target_date.strftime('%Y-%m-%d'), 'facilities': result}), 200

@app.route('/api/facilities/book', methods=['POST'])
@token_required
def book_facility():
    data = request.json or {}
    room_id      = data.get('room_id')
    date_str     = data.get('date', '')
    time_slot_id = data.get('time_slot_id')
    seat_numbers = data.get('seat_numbers')  # list of ints, Library Seat only

    if not room_id or not date_str or not time_slot_id:
        return jsonify({'error': 'room_id, date and time_slot_id are required'}), 400

    room = Room.query.get(room_id)
    if not room or room.room_type not in FACILITY_TYPES:
        return jsonify({'error': 'Invalid facility'}), 404

    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if booking_date < datetime.utcnow().date():
        return jsonify({'error': 'Cannot book a slot in the past'}), 400

    time_slot = TimeSlot.query.get(time_slot_id)
    if not time_slot:
        return jsonify({'error': 'Invalid time slot'}), 404

    # Prevent double-booking by the same student for the same slot
    existing = FacilityBooking.query.filter_by(
        student_id=request.user_id, room_id=room_id, date=booking_date,
        time_slot_id=time_slot_id, status='confirmed'
    ).first()
    if existing:
        return jsonify({'error': 'You already have a booking for this facility at this time'}), 400

    if room.room_type == 'Library Seat':
        if not seat_numbers or not isinstance(seat_numbers, list):
            return jsonify({'error': 'Please select at least one seat'}), 400
        if len(seat_numbers) > MAX_GROUP_SEATS:
            return jsonify({'error': f'You can book a maximum of {MAX_GROUP_SEATS} seats for group study'}), 400
        try:
            seat_numbers = sorted({int(n) for n in seat_numbers})
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid seat number'}), 400
        if any(n < 1 or n > room.capacity for n in seat_numbers):
            return jsonify({'error': 'Seat number out of range'}), 400

        taken = get_taken_seats(room_id, booking_date, time_slot_id)
        clashing = [n for n in seat_numbers if n in taken]
        if clashing:
            return jsonify({'error': f"Seat(s) {', '.join(map(str, clashing))} already booked. Please choose another seat."}), 400

        booking = FacilityBooking(
            student_id=request.user_id, room_id=room_id,
            date=booking_date, time_slot_id=time_slot_id,
            seat_numbers=','.join(map(str, seat_numbers)),
            group_size=len(seat_numbers)
        )
        db.session.add(booking)
        db.session.commit()
        seats_label = f"Seat {seat_numbers[0]}" if len(seat_numbers) == 1 else f"Seats {', '.join(map(str, seat_numbers))}"
        log_activity(request.user_id, 'facility_booking', f'Booked {room.name} ({seats_label}) for {time_slot.slot_name} on {booking_date}')
        return jsonify({'message': f'{room.name} — {seats_label} booked for {time_slot.slot_name}!', 'id': booking.id}), 201

    # Sports Facility — unchanged behaviour (capacity counter, no seat numbers)
    booked_count = FacilityBooking.query.filter_by(
        room_id=room_id, date=booking_date, time_slot_id=time_slot_id, status='confirmed'
    ).count()
    if booked_count >= room.capacity:
        return jsonify({'error': 'This slot is fully booked. Please choose another time.'}), 400

    booking = FacilityBooking(
        student_id=request.user_id, room_id=room_id,
        date=booking_date, time_slot_id=time_slot_id
    )
    db.session.add(booking)
    db.session.commit()
    log_activity(request.user_id, 'facility_booking', f'Booked {room.name} for {time_slot.slot_name} on {booking_date}')

    return jsonify({'message': f'{room.name} booked successfully for {time_slot.slot_name}!', 'id': booking.id}), 201

@app.route('/api/facilities/my-bookings', methods=['GET'])
@token_required
def my_facility_bookings():
    bookings = FacilityBooking.query.filter_by(student_id=request.user_id)\
        .order_by(FacilityBooking.date.desc(), FacilityBooking.time_slot_id).all()
    return jsonify([{
        'id': b.id,
        'room_name': b.room.name if b.room else '',
        'room_type': b.room.room_type if b.room else '',
        'building': b.room.building if b.room else '',
        'date': b.date.strftime('%Y-%m-%d'),
        'date_display': b.date.strftime('%d %b %Y'),
        'slot_name': b.time_slot.slot_name if b.time_slot else '',
        'status': b.status,
        'seat_numbers': [int(n) for n in b.seat_numbers.split(',')] if b.seat_numbers else [],
        'group_size': b.group_size or 1,
        'is_upcoming': b.date >= datetime.utcnow().date(),
        'created_at': b.created_at.strftime('%d %b %Y, %H:%M')
    } for b in bookings]), 200

@app.route('/api/facilities/bookings/<int:booking_id>', methods=['DELETE'])
@token_required
def cancel_facility_booking(booking_id):
    booking = FacilityBooking.query.get(booking_id)
    if not booking or booking.student_id != request.user_id:
        return jsonify({'error': 'Booking not found'}), 404
    if booking.status == 'cancelled':
        return jsonify({'error': 'Booking already cancelled'}), 400

    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Booking cancelled successfully'}), 200

@app.route('/api/admin/facility-bookings', methods=['GET'])
@token_required
@admin_required
def all_facility_bookings():
    room_type = request.args.get('room_type', '')
    date_str  = request.args.get('date', '')

    q = FacilityBooking.query.filter_by(status='confirmed')
    if room_type:
        q = q.join(Room).filter(Room.room_type == room_type)
    if date_str:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
            q = q.filter(FacilityBooking.date == d)
        except ValueError:
            pass

    bookings = q.order_by(FacilityBooking.date.desc()).all()
    return jsonify([{
        'id': b.id,
        'student_name': f"{b.student.first_name} {b.student.last_name}" if b.student else '',
        'student_email': b.student.email if b.student else '',
        'room_name': b.room.name if b.room else '',
        'room_type': b.room.room_type if b.room else '',
        'date': b.date.strftime('%d %b %Y'),
        'slot_name': b.time_slot.slot_name if b.time_slot else '',
        'seat_numbers': [int(n) for n in b.seat_numbers.split(',')] if b.seat_numbers else [],
        'group_size': b.group_size or 1,
        'created_at': b.created_at.strftime('%d %b %Y, %H:%M')
    } for b in bookings]), 200


def seed_data():
    # ── Seed default campus config ──────────────────────────
    if CampusConfig.query.count() == 0:
        db.session.add(CampusConfig(
            name='My Location (Test)',
            latitude=28.622902, longitude=77.050226, radius_m=500
        ))
        db.session.commit()
        print('✅ Default campus location set')

    # ── Default admin account ───────────────────────────────
    admin_email = 'admin@eduspace.edu'
    if not User.query.filter_by(email=admin_email).first():
        default_admin = User(
            first_name='System', last_name='Admin',
            email=admin_email,
            password_hash=generate_password_hash('Admin@EduSpace2026'),
            role='admin', is_approved=True
        )
        db.session.add(default_admin)
        db.session.commit()
        print('✅ Default admin created → admin@eduspace.edu / Admin@EduSpace2026')
    else:
        print('✅ Admin account exists')

    # ── Sample rooms ────────────────────────────────────────
    if Room.query.count() == 0:
        rooms = [
            Room(name='Class A101', room_type='Classroom',   building='Building A', floor=1, capacity=30),
            Room(name='Lab B201',   room_type='Lab',          building='Building B', floor=2, capacity=25),
            Room(name='Seminar C301',room_type='Seminar Hall',building='Building C', floor=3, capacity=40),
            Room(name='Study D101', room_type='Study Room',   building='Building D', floor=1, capacity=10),
        ]
        db.session.add_all(rooms)
        db.session.commit()

    # ── Sample time slots ───────────────────────────────────
    if TimeSlot.query.count() == 0:
        slots = [
            TimeSlot(slot_name='9:00 AM - 10:00 AM'),
            TimeSlot(slot_name='10:00 AM - 11:00 AM'),
            TimeSlot(slot_name='11:00 AM - 12:00 PM'),
            TimeSlot(slot_name='2:00 PM - 3:00 PM'),
            TimeSlot(slot_name='3:00 PM - 4:00 PM'),
            TimeSlot(slot_name='4:00 PM - 5:00 PM'),
        ]
        db.session.add_all(slots)
        db.session.commit()
    print('✅ Sample rooms and time slots created')

    # ── Seed Skills ─────────────────────────────────────────
    if Skill.query.count() == 0:
        skill_data = [
            ('Python','Programming'),('JavaScript','Programming'),('React','Programming'),
            ('Java','Programming'),('C++','Programming'),('Machine Learning','Programming'),
            ('Data Science','Programming'),('Web Development','Programming'),('SQL','Programming'),
            ('Guitar','Music'),('Piano','Music'),('Vocals','Music'),('Drums','Music'),
            ('Drawing','Arts'),('Photography','Arts'),('Video Editing','Arts'),('Graphic Design','Arts'),
            ('Hindi','Languages'),('English','Languages'),('French','Languages'),('Spanish','Languages'),
            ('Mathematics','Science'),('Physics','Science'),('Chemistry','Science'),('Biology','Science'),
            ('Cricket','Sports'),('Football','Sports'),('Basketball','Sports'),('Chess','Sports'),
            ('Public Speaking','Other'),('Leadership','Other'),('Creative Writing','Other'),('Finance','Other'),
        ]
        db.session.add_all([Skill(name=n, category=c) for n, c in skill_data])
        db.session.commit()
        print(f'✅ {len(skill_data)} skills seeded')

    # ── Seed notifications ──────────────────────────────────
    if Notification.query.count() == 0:
        admin = User.query.filter(User.role.ilike('admin')).first()
        if admin:
            notifs = [
                Notification(title='Welcome to EduSpace!', message='EduSpace is now live. Book rooms, track attendance, and stay updated.', notif_type='info', target_role='all', created_by=admin.id),
                Notification(title='Annual Tech Fest 2026', message='Annual Tech Fest is on 15th June! Register at the admin office.', notif_type='event', target_role='all', created_by=admin.id),
                Notification(title='Library Extended Hours', message='Library will remain open till 10pm starting this week.', notif_type='info', target_role='student', created_by=admin.id),
            ]
            db.session.add_all(notifs)
            db.session.commit()
            print(f'✅ {len(notifs)} sample notifications created')

    # ── Seed Lost & Found ───────────────────────────────────
    if LostFoundItem.query.count() == 0:
        admin = User.query.filter(User.role.ilike('admin')).first()
        if admin:
            samples = [
                LostFoundItem(title='Blue Scientific Calculator', description='Casio FX-991ES Plus', category='electronics', item_type='lost', location='Library 2nd Floor', contact_info='Ask at front desk', reported_by=admin.id),
                LostFoundItem(title='Black Leather Wallet', description='Contains student ID', category='other', item_type='found', location='Canteen', contact_info='Security office', reported_by=admin.id),
                LostFoundItem(title='Data Structures Textbook', description='Cormen CLRS 3rd edition', category='books', item_type='lost', location='Room A101', contact_info='9876543210', reported_by=admin.id),
                LostFoundItem(title='Bunch of Keys', description='Eiffel Tower keychain', category='keys', item_type='found', location='Ground Floor Corridor', contact_info='Security Desk', reported_by=admin.id),
            ]
            db.session.add_all(samples)
            db.session.commit()
            print(f'✅ {len(samples)} Lost & Found items seeded')


with app.app_context():
       db.create_all()

   if __name__ == '__main__':
       with app.app_context():
           seed_data()
       app.run(debug=True, port=5000)
