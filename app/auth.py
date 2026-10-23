
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import select
from werkzeug.security import check_password_hash

from app.models import StaffUser, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("participants.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.session.scalar(
            select(StaffUser).where(StaffUser.username == username)
        )

        if (
            user is not None
            and user.is_active
            and check_password_hash(user.password_hash, password)
        ):
            # Clear pre-authentication session data before login.
            session.clear()
            login_user(user, remember=False)

            next_url = request.args.get("next", "")

            # Accept only local application paths.
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)

            return redirect(url_for("participants.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()

    flash("You have signed out.", "success")
    return redirect(url_for("auth.login"))
