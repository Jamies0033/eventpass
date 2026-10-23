
import csv
import io
from datetime import datetime, timezone

from flask import Blueprint, Response
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import Attendance, AttendanceSession, Participant, db

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def csv_response(filename, headers, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)

    for row in rows:
        safe_row = []

        for value in row:
            text = "" if value is None else str(value)

            # Reduce spreadsheet formula-injection risk for untrusted values.
            if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                text = "'" + text

            safe_row.append(text)

        writer.writerow(safe_row)

    response = Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )
    response.headers["Cache-Control"] = "no-store"

    return response


def export_date():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


@reports_bp.get("/participants.csv")
@login_required
def export_participants():
    participants = db.session.scalars(
        select(Participant).order_by(Participant.id.asc())
    ).all()

    rows = (
        (
            participant.participant_code,
            participant.full_name,
            participant.email,
            participant.phone,
            participant.organization,
            "Active" if participant.is_active else "Inactive",
            (
                participant.created_at.isoformat()
                if participant.created_at
                else ""
            ),
        )
        for participant in participants
    )

    return csv_response(
        f"eventpass_participants_{export_date()}.csv",
        [
            "Participant Code",
            "Full Name",
            "Email",
            "Phone",
            "Organization",
            "Status",
            "Registration Date",
        ],
        rows,
    )


@reports_bp.get("/attendance.csv")
@login_required
def export_attendance():
    records = db.session.scalars(
        select(Attendance)
        .options(
            joinedload(Attendance.participant),
            joinedload(Attendance.session),
            joinedload(Attendance.recorded_by),
        )
        .join(
            AttendanceSession,
            Attendance.session_id == AttendanceSession.id,
        )
        .order_by(
            AttendanceSession.session_date.asc(),
            AttendanceSession.checkpoint.asc(),
            Attendance.checked_in_at.asc(),
        )
    ).all()

    rows = (
        (
            record.participant.participant_code,
            record.participant.full_name,
            record.participant.organization,
            record.session.session_date.isoformat(),
            record.session.checkpoint.title(),
            record.checked_in_at.isoformat(),
            record.recorded_by.username,
        )
        for record in records
    )

    return csv_response(
        f"eventpass_attendance_{export_date()}.csv",
        [
            "Participant Code",
            "Full Name",
            "Organization",
            "Attendance Date",
            "Checkpoint",
            "Scan Timestamp",
            "Recorded By",
        ],
        rows,
    )

