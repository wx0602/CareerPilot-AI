from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.security import hash_password
from ..dbmodels import User


def ensure_demo_user(db: Session, settings: Settings) -> User:
    account = settings.demo_account.strip().lower()
    user = db.scalar(select(User).where(User.account == account))
    if user is None:
        user = User(account=account, password_hash=hash_password(settings.demo_password))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
