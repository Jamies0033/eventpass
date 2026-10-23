
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Attendance, AttendanceSession, Participant, db

EVENT_TIMEZONE = ZoneInfo("Africa/Lagos")
participants_bp = Blueprint("participants", __name__)


@participants_bp.get("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("participants.dashboard"))

    return redirect(url_for("auth.login"))


@participants_bp.get("/dashboard")
@login_required
def dashboard():
    total = (
        db.session.scalar(
            select(func.count())
            .select_from(Participant)
            .where(Participant.is_active.is_(True))
        )
        or 0
    )

    today = datetime.now(EVENT_TIMEZONE).date()

    attendance_counts = db.session.execute(
        select(
            AttendanceSession.checkpoint,
            func.count(Attendance.id),
        )
        .outerjoin(
            Attendance,
            Attendance.session_id == AttendanceSession.id,
        )
        .where(AttendanceSession.session_date == today)
        .group_by(AttendanceSession.checkpoint)
    ).all()

    counts = dict(attendance_counts)

    arrivals_today = counts.get("arrival", 0)
    departures_today = counts.get("departure", 0)

    return render_template(
        "dashboard.html",
        total=total,
        arrivals_today=arrivals_today,
        departures_today=departures_today,
    )



@participants_bp.route("/participants/new", methods=["GET", "POST"])
@login_required
def new_participant():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        organization = request.form.get("organization", "").strip() or None

        if not full_name or len(full_name) > 160:
            flash(
                "Enter a participant name of up to 160 characters.",
                "error",
            )
            return render_template("participant_form.html"), 400

        if email and len(email) > 254:
            flash("Email must be 254 characters or fewer.", "error")
            return render_template("participant_form.html"), 400

        if phone and len(phone) > 30:
            flash("Phone number must be 30 characters or fewer.", "error")
            return render_template("participant_form.html"), 400

        if organization and len(organization) > 160:
            flash(
                "Organization must be 160 characters or fewer.",
                "error",
            )
            return render_template("participant_form.html"), 400

        participant = Participant(
            participant_code=f"TEMP-{secrets.token_hex(8)}",
            full_name=full_name,
            email=email,
            phone=phone,
            organization=organization,
        )

        try:
            db.session.add(participant)
            db.session.flush()

            # Generate the readable code after the database assigns an ID.
            participant.participant_code = f"FP-{participant.id:04d}"
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            flash(
                "Registration could not be completed because of a database "
                "constraint. Please retry.",
                "error",
            )
            return render_template("participant_form.html"), 409

        flash(
            f"{participant.full_name} was registered as "
            f"{participant.participant_code}.",
            "success",
        )

        return redirect(url_for("participants.participant_list"))

    return render_template("participant_form.html")


@participants_bp.get("/participants")
@login_required
def participant_list():
    search = request.args.get("q", "").strip()

    query = select(Participant).where(Participant.is_active.is_(True))

    if search:
        term = f"%{search}%"
        query = query.where(
            Participant.full_name.ilike(term)
            | Participant.participant_code.ilike(term)
        )

    participants = db.session.scalars(
        query.order_by(Participant.id.desc()).limit(500)
    ).all()

    return render_template(
        "participants.html",
        participants=participants,
        search=search,
    )
@participants_bp.post("/participants/<int:participant_id>/delete")
@login_required
def delete_participant(participant_id):
    participant = db.session.get(Participant, participant_id)

    if participant is None or not participant.is_active:
        flash("Registration not found.", "error")
        return redirect(url_for("participants.participant_list"))

    if participant.attendance_records:
        flash(
            f"{participant.full_name} has attendance records and cannot "
            "be permanently deleted. Deactivate the registration instead.",
            "error",
        )
        return redirect(url_for("participants.participant_list"))

    name = participant.full_name
    participant.is_active = False
    db.session.commit()

    flash(
        f"Registration for {name} has been removed from the active directory.",
        "success",
    )
    return redirect(url_for("participants.participant_list"))
