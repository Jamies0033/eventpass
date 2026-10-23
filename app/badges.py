
import io

import qrcode
from flask import Blueprint, abort, render_template, send_file
from flask_login import login_required
from sqlalchemy import select

from app.models import Participant, db

badges_bp = Blueprint("badges", __name__, url_prefix="/badges")


@badges_bp.get("/")
@login_required
def badge_list():
    participants = db.session.scalars(
        select(Participant)
        .where(Participant.is_active.is_(True))
        .order_by(Participant.full_name.asc())
    ).all()

    return render_template("badges.html", participants=participants)


@badges_bp.get("/<int:participant_id>/qr.png")
@login_required
def participant_qr(participant_id):
    participant = db.session.get(Participant, participant_id)

    if participant is None or not participant.is_active:
        abort(404)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(participant.ticket_token)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")

    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    response = send_file(
        image_buffer,
        mimetype="image/png",
        download_name=f"{participant.participant_code}.png",
    )
    response.headers["Cache-Control"] = "no-store"
    return response
