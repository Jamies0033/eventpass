
import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, UniqueConstraint

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class StaffUser(UserMixin, db.Model):
    __tablename__ = "staff_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="staff", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, nullable=False
    )


class Participant(db.Model):
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True)
    participant_code = db.Column(
        db.String(50), unique=True, nullable=False, index=True
    )
    full_name = db.Column(db.String(160), nullable=False, index=True)
    email = db.Column(db.String(254))
    phone = db.Column(db.String(30))
    organization = db.Column(db.String(160))

    # QR codes contain a random token, not personal information.
    ticket_token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, nullable=False
    )

    attendance_records = db.relationship(
        "Attendance",
        back_populates="participant",
        lazy=True,
    )


class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_date = db.Column(db.Date, nullable=False, index=True)
    checkpoint = db.Column(db.String(10), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "session_date",
            "checkpoint",
            name="uq_attendance_date_checkpoint",
        ),
        db.CheckConstraint(
            "checkpoint IN ('arrival', 'departure')",
            name="ck_attendance_checkpoint",
        ),
    )


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(
        db.Integer,
        db.ForeignKey("participants.id"),
        nullable=False,
    )
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_sessions.id"),
        nullable=False,
    )
    checked_in_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    recorded_by_id = db.Column(
        db.Integer,
        db.ForeignKey("staff_users.id"),
        nullable=False,
    )

    participant = db.relationship(
        "Participant",
        back_populates="attendance_records",
    )
    session = db.relationship("AttendanceSession")
    recorded_by = db.relationship("StaffUser")

    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "session_id",
            name="uq_participant_attendance_session",
        ),
        Index("ix_attendance_session_id", "session_id"),
        Index("ix_attendance_participant_id", "participant_id"),
    )
