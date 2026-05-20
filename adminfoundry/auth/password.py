import bcrypt as _bcrypt


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_password_strength(password: str, *, min_length: int = 8) -> None:
    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters.")
