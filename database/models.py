from sqlalchemy import Boolean, String, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    tg_id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

class Service(Base):
    __tablename__ = 'services'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)  # в минутах
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class BroadcastSettings(Base):
    __tablename__ = 'broadcast_settings'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    default_text: Mapped[str] = mapped_column(Text, nullable=False, default='Заходи на эфир')