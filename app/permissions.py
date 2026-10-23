
from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)

        if not current_user.is_active or current_user.role != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view
