"""Modelos SQLAlchemy. Dinero y HCK siempre como Decimal (Numeric), nunca float."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    xp = Column(Integer, default=0, nullable=False)
    usdt_balance = Column(Numeric(20, 6), default=Decimal("0"), nullable=False)
    hck_balance = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    total_hck_earned = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    referral_code = Column(String(16), unique=True, index=True, nullable=False)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    registration_ip = Column(String(64), nullable=True)
    last_login_ip = Column(String(64), nullable=True)
    daily_bonus_streak = Column(Integer, default=0, nullable=False)
    last_daily_bonus_date = Column(DateTime, nullable=True)
    mining_active = Column(Boolean, default=False, nullable=False)
    mining_started_at = Column(DateTime, nullable=True)
    mining_pending_hck = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    machines = relationship("OwnedMachine", back_populates="user", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan")


class OwnedMachine(Base):
    __tablename__ = "owned_machines"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    machine_id = Column(String(32), nullable=False)
    overclock_level = Column(Integer, default=0, nullable=False)
    purchased_at = Column(DateTime, default=utcnow, nullable=False)
    user = relationship("User", back_populates="machines")


class Deposit(Base):
    __tablename__ = "deposits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tx_hash = Column(String(128), unique=True, index=True, nullable=False)
    network = Column(String(16), nullable=False)  # BSC | TRON
    amount_usdt = Column(Numeric(20, 6), nullable=False)
    status = Column(String(32), default="pending_verification", nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="deposits")


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_usdt = Column(Numeric(20, 6), nullable=False)
    fee_usdt = Column(Numeric(20, 6), nullable=False)
    net_usdt = Column(Numeric(20, 6), nullable=False)
    hck_spent = Column(Numeric(20, 4), nullable=False)
    address = Column(String(128), nullable=False)
    network = Column(String(16), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    reason = Column(Text, nullable=True)
    tx_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    user = relationship("User", back_populates="withdrawals")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(32), nullable=False)  # deposit/purchase/withdrawal/reward/bonus/collect/referral
    amount_hck = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    amount_usdt = Column(Numeric(20, 6), default=Decimal("0"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class UserMission(Base):
    __tablename__ = "user_missions"
    __table_args__ = (UniqueConstraint("user_id", "mission_id", "date", name="uq_user_mission_day"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mission_id = Column(String(32), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    progress = Column(Numeric(20, 4), default=Decimal("0"), nullable=False)
    claimed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class RewardPool(Base):
    __tablename__ = "reward_pool"
    id = Column(Integer, primary_key=True)
    balance_usdt = Column(Numeric(20, 6), default=Decimal("0"), nullable=False)
    total_funded = Column(Numeric(20, 6), default=Decimal("0"), nullable=False)
    total_paid = Column(Numeric(20, 6), default=Decimal("0"), nullable=False)


class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(Integer, primary_key=True)
    hck_to_usdt_rate = Column(Numeric(20, 4), default=Decimal("10000"), nullable=False)
    withdrawal_fee_percent = Column(Numeric(10, 4), default=Decimal("2"), nullable=False)
    min_withdrawal_usdt = Column(Numeric(20, 6), default=Decimal("10"), nullable=False)
    referral_bonus_hck = Column(Numeric(20, 4), default=Decimal("500"), nullable=False)
    production_per_hash = Column(Numeric(10, 4), default=Decimal("10"), nullable=False)
    storage_hours = Column(Numeric(10, 4), default=Decimal("8"), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
