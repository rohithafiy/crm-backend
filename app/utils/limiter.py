from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure the global rate limiter using in-memory storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    strategy="fixed-window"
)
