from flask import g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_user_key():
    return getattr(g, "user_id", None) or get_remote_address()


limiter = Limiter(
    key_func=get_user_key,
    default_limits=[],
    storage_uri="memory://",
)