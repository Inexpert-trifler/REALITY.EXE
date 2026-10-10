"""Password hashing and verification utilities.

Wraps bcrypt via the security module so all password logic is centralised
here rather than scattered across the service layer.
"""

from app.core.security import hash_password as _hash_password
from app.core.security import verify_password as _verify_password


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*.  Never stores plaintext."""
    return _hash_password(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    return _verify_password(plain, hashed)
