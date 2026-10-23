from getpass import getpass

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import StaffUser, db

app = create_app()

with app.app_context():
    username = input("Admin username: ").strip()
    if not username or len(username) > 80:
        raise SystemExit("Username must be between 1 and 80 characters.")

    existing = db.session.query(StaffUser).filter_by(username=username).first()
    if existing:
        raise SystemExit("That username already exists.")

    password = getpass("Admin password (at least 12 characters): ")
    confirmation = getpass("Confirm password: ")

    if len(password) < 12:
        raise SystemExit("Use a password with at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    admin = StaffUser(
        username=username,
        password_hash=generate_password_hash(password),
        role="admin",
    )
    db.session.add(admin)
    db.session.commit()

    print(f"Administrator '{username}' created successfully.")
