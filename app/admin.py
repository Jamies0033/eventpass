
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.models import StaffUser, db
from app.permissions import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def staff_list():
    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "create":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "staff")

            if not username or len(username) > 80:
                flash("Enter a username between 1 and 80 characters.", "error")
            elif len(password) < 12:
                flash("Passwords must be at least 12 characters.", "error")
            elif role not in {"admin", "staff"}:
                flash("Choose a valid role.", "error")
            else:
                user = StaffUser(
                    username=username,
                    password_hash=generate_password_hash(password),
                    role=role,
                    is_active=True,
                )
                db.session.add(user)

                try:
                    db.session.commit()
                    flash(f"Account '{username}' created.", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("That username is already in use.", "error")

            return redirect(url_for("admin.staff_list"))

        user_id = request.form.get("user_id", type=int)
        target = db.session.get(StaffUser, user_id) if user_id else None

        if target is None:
            abort(404)

        if action == "toggle_active":
            new_active_state = not target.is_active

            if target.id == current_user.id and not new_active_state:
                flash("You cannot deactivate your own account.", "error")
            elif (
                target.role == "admin"
                and target.is_active
                and not new_active_state
                and db.session.scalar(
                    select(func.count(StaffUser.id)).where(
                        StaffUser.role == "admin",
                        StaffUser.is_active.is_(True),
                    )
                ) <= 1
            ):
                flash("The last active administrator cannot be deactivated.", "error")
            else:
                target.is_active = new_active_state
                db.session.commit()
                flash("Account status updated.", "success")

        elif action == "change_role":
            new_role = request.form.get("role", "")

            if new_role not in {"admin", "staff"}:
                flash("Choose a valid role.", "error")
            elif target.id == current_user.id and new_role != "admin":
                flash("You cannot remove your own administrator role.", "error")
            elif (
                target.role == "admin"
                and target.is_active
                and new_role != "admin"
                and db.session.scalar(
                    select(func.count(StaffUser.id)).where(
                        StaffUser.role == "admin",
                        StaffUser.is_active.is_(True),
                    )
                ) <= 1
            ):
                flash("The last active administrator must remain an administrator.", "error")
            else:
                target.role = new_role
                db.session.commit()
                flash("Account role updated.", "success")

        else:
            abort(400)

        return redirect(url_for("admin.staff_list"))

    staff = db.session.scalars(
        select(StaffUser).order_by(StaffUser.created_at.desc())
    ).all()

    return render_template("admin/staff.html", staff=staff)
