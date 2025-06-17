from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, Text
from app.db.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)

    accounts:Mapped[list["Accounts"]] = relationship("Accounts", back_populates="user")
    presets: Mapped[list["Presets"]] = relationship("Presets", back_populates="user")

class Accounts(Base):
    __tablename__ = "acounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=False)
    api_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=False)
    api_hash: Mapped[str] = mapped_column(String(100), nullable=False, unique=False)
    session_path: Mapped[str] = mapped_column(String(100), nullable=False, unique=False)
    proxy: Mapped[str] = mapped_column(String(255), nullable=True, unique=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="accounts")

    preset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("presets.id"), nullable=True)
    preset: Mapped["Presets"] = relationship("Presets", back_populates="account", uselist=False)

class Presets(Base):
    __tablename__ = "presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_chats: Mapped[list] = mapped_column(JSON, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="presets")

    account: Mapped["Accounts"] = relationship("Accounts", back_populates="preset", uselist=False)