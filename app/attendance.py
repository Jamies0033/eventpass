from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Attendance,
    AttendanceSession,
    Participant,
    db,
)

attendance_bp = Blueprint(
    "attendance",
    __name__,
    url_prefix="/attendance",
)

EVENT_TIMEZONE = ZoneInfo("Africa/Lagos")
VALID_CHECKPOINTS = {"arrival", "departure"}

@attendance_bp.get("/scan")
@login_required
def scanner_page():
    return render_template("attendance_scanner.html")
@attendance_bp.post("/api/scan")
@login_required
def scan_qr():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A valid JSON request is required."), 400

    token = data.get("token")
    checkpoint = data.get("checkpoint")

    if not isinstance(token, str) or not token.strip():
        return jsonify(error="A QR token is required."), 400

    token = token.strip()

    if len(token) > 64:
        return jsonify(error="Invalid QR token."), 400

    if (
        not isinstance(checkpoint, str)
        or checkpoint not in VALID_CHECKPOINTS
    ):
        return jsonify(
            error="Select either arrival or departure."
        ), 400

    participant = db.session.scalar(
        select(Participant).where(
            Participant.ticket_token == token,
            Participant.is_active.is_(True),
        )
    )

    if participant is None:
        return jsonify(
            error="Invalid QR code or inactive participant."
        ), 404

    event_date = datetime.now(EVENT_TIMEZONE).date()

    attendance_session = db.session.scalar(
        select(AttendanceSession).where(
            AttendanceSession.session_date == event_date,
            AttendanceSession.checkpoint == checkpoint,
        )
    )

    if attendance_session is None:
        attendance_session = AttendanceSession(
            session_date=event_date,
            checkpoint=checkpoint,
        )
        db.session.add(attendance_session)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            attendance_session = db.session.scalar(
                select(AttendanceSession).where(
                    AttendanceSession.session_date == event_date,
                    AttendanceSession.checkpoint == checkpoint,
                )
            )

            if attendance_session is None:
                return jsonify(
                    error=(
                        "Could not prepare the attendance session. "
                        "Try again."
                    )
                ), 500

    existing_record = db.session.scalar(
        select(Attendance).where(
            Attendance.participant_id == participant.id,
            Attendance.session_id == attendance_session.id,
        )
    )

    if existing_record is not None:
        return jsonify(
            error=(
                f"{participant.full_name} is already recorded "
                f"for {checkpoint} today."
            ),
            participant={
                "code": participant.participant_code,
                "name": participant.full_name,
            },
            checkpoint=checkpoint,
        ), 409

    record = Attendance(
        participant_id=participant.id,
        session_id=attendance_session.id,
        checked_in_at=datetime.now(timezone.utc),
        recorded_by_id=current_user.id,
    )

    db.session.add(record)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            error=(
                "This attendance has already been recorded. "
                "No duplicate was added."
            )
        ), 409

    return jsonify(
        message=f"{checkpoint.capitalize()} recorded successfully.",
        participant={
            "code": participant.participant_code,
            "name": participant.full_name,
            "organization": participant.organization,
        },
        checkpoint=checkpoint,
        event_date=event_date.isoformat(),
        recorded_at=record.checked_in_at.isoformat(),
    ), 201
