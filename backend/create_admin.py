import hashlib
import os
import secrets

from database import SessionLocal, User


DEFAULT_ADMIN_USERNAME = os.getenv("NEUROSCAN_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("NEUROSCAN_ADMIN_PASSWORD", "Admin@123")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return f"pbkdf2_sha256$120000${salt}${digest}"


db = SessionLocal()

try:
    admin = db.query(User).filter(User.role == "admin", User.username == DEFAULT_ADMIN_USERNAME).first()

    if not admin:
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            password=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin",
            full_name="NeuroScan Administrator",
            contact_number="0000000000",
        )
        db.add(admin)
    else:
        admin.password = hash_password(DEFAULT_ADMIN_PASSWORD)

    db.commit()
finally:
    db.close()

print(f"Admin account ready. Username: {DEFAULT_ADMIN_USERNAME}")
