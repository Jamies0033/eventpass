
import os

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.models import StaffUser, db

csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(StaffUser, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    os.makedirs(app.instance_path, exist_ok=True)

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is missing. Set it in your environment before starting EventPass."
        )

    app.config["SECRET_KEY"] = secret_key

    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://", "postgresql+psycopg://", 1
            )
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url
        or "sqlite:///" + os.path.join(app.instance_path, "eventpass.sqlite3")
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Session and cookie security.
    is_production = os.environ.get("FLASK_ENV") == "production" or (
        os.environ.get("APP_ENV") == "production"
    )

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = is_production

    # Initialize extensions.
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Import and register application routes.
    from app.auth import auth_bp
    from app.participants import participants_bp
    from app.reports import reports_bp
    from app.badges import badges_bp
    from app.attendance import attendance_bp
    from app.admin import admin_bp
   
    app.register_blueprint(auth_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(badges_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(admin_bp)
    @app.get("/health")
    def health():
        return {"status": "ok", "application": "EventPass"}, 200

    with app.app_context():
        db.create_all()

    return app
