from sqlalchemy import Boolean, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    tg_id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    # Связь с записями
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    # Связь с прогрессом воронки
    funnel_progress: Mapped[list["FunnelProgress"]] = relationship(back_populates="user")

class Service(Base):
    __tablename__ = 'services'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)  # в минутах
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Связь с записями
    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")

class BroadcastSettings(Base):
    __tablename__ = 'broadcast_settings'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    default_text: Mapped[str] = mapped_column(Text, nullable=False, default='Заходи на эфир')

class Booking(Base):
    __tablename__ = 'bookings'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(ForeignKey('users.tg_id'), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey('services.id'), nullable=False)
    client_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    preferred_date: Mapped[str] = mapped_column(String(50), nullable=False)  # "15 января"
    preferred_time: Mapped[str] = mapped_column(String(10), nullable=False)  # "14:00"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="bookings")
    service: Mapped["Service"] = relationship(back_populates="bookings")


class Funnel(Base):
    __tablename__ = 'funnels'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), nullable=False)

    # Связь с этапами воронки
    steps: Mapped[list["FunnelStep"]] = relationship(back_populates="funnel", order_by="FunnelStep.order")

class FunnelStep(Base):
    __tablename__ = 'funnel_steps'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    funnel_id: Mapped[int] = mapped_column(ForeignKey('funnels.id'), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False) # Порядок в воронке (1, 2, 3...)
    title: Mapped[str] = mapped_column(String(100), nullable=False) # "День 1: Основы дыхания
    content: Mapped[str] = mapped_column(Text, nullable=False) # "В этом уроке мы познакомимся"
    content_type: Mapped[str] = mapped_column(String(10), nullable=False) # "video" или "text"
    file_id: Mapped[str] = mapped_column(String(255), nullable=True) # ID файла в Telegram
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Бесплатный ли этап
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), nullable=False)

    # Связь с воронкой
    funnel: Mapped["Funnel"] = relationship(back_populates="steps")

class FunnelProgress(Base):
    __tablename__ = 'funnel_progress'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(ForeignKey('users.tg_id'), nullable=False)
    funnel_id: Mapped[int] = mapped_column(ForeignKey('funnels.id'), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())

    # Связи
    user: Mapped["User"] = relationship(back_populates="funnel_progress")
    funnel: Mapped["Funnel"] = relationship()