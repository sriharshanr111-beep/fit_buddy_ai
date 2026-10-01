"""SQLite persistence using SQLAlchemy ORM."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    username: Mapped[str] = mapped_column(String(60), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    goal: Mapped[str] = mapped_column(String(40), nullable=False)
    intensity: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    plan: Mapped[Optional["Plan"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), unique=True, nullable=False)
    original_plan: Mapped[str] = mapped_column(Text, nullable=False)
    updated_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nutrition_tip: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="plan")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()


# ---------------------------------------------------------------- users
def save_user(db, user_id: str, username: str, age: int, weight: float, goal: str, intensity: str) -> User:
    """Create the user, or update their details if the user_id already exists."""
    user = db.get(User, user_id)
    if user is None:
        user = User(user_id=user_id, username=username, age=age, weight=weight, goal=goal, intensity=intensity)
        db.add(user)
    else:
        user.username, user.age, user.weight = username, age, weight
        user.goal, user.intensity = goal, intensity
    db.commit()
    db.refresh(user)
    return user


def get_user(db, user_id: str) -> Optional[User]:
    return db.get(User, user_id)


def get_all_users(db) -> list:
    return db.query(User).order_by(User.created_at.desc()).all()


def delete_user(db, user_id: str) -> bool:
    user = db.get(User, user_id)
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True


# ---------------------------------------------------------------- plans
def save_plan(db, user_id: str, workout_plan: str, nutrition_tip: str) -> Plan:
    """Save a freshly generated plan (replaces any previous plan for this user)."""
    plan = db.query(Plan).filter(Plan.user_id == user_id).first()
    if plan is None:
        plan = Plan(user_id=user_id, original_plan=workout_plan, nutrition_tip=nutrition_tip)
        db.add(plan)
    else:
        plan.original_plan = workout_plan
        plan.nutrition_tip = nutrition_tip
        plan.updated_plan = None
        plan.last_feedback = None
        plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


def get_original_plan(db, user_id: str) -> Optional[str]:
    plan = db.query(Plan).filter(Plan.user_id == user_id).first()
    return plan.original_plan if plan else None


def get_plan(db, user_id: str) -> Optional[Plan]:
    return db.query(Plan).filter(Plan.user_id == user_id).first()


def update_plan(db, user_id: str, updated_plan: str, feedback: str, nutrition_tip: Optional[str] = None) -> Optional[Plan]:
    """Store the feedback-based plan in its own column (original is preserved)."""
    plan = db.query(Plan).filter(Plan.user_id == user_id).first()
    if plan is None:
        return None
    plan.updated_plan = updated_plan
    plan.last_feedback = feedback
    if nutrition_tip:
        plan.nutrition_tip = nutrition_tip
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


def get_all_plans(db) -> list:
    return db.query(Plan).all()