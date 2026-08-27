from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="owner")
    charts: Mapped[list["Chart"]] = relationship(back_populates="owner")
    dashboards: Mapped[list["Dashboard"]] = relationship(back_populates="owner")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    filepath: Mapped[str] = mapped_column(String(512))
    columns_json: Mapped[str] = mapped_column(Text, default="[]")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    source_type: Mapped[str] = mapped_column(String(32), default="file")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["User"] = relationship(back_populates="datasets")
    charts: Mapped[list["Chart"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class Chart(Base):
    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    chart_type: Mapped[str] = mapped_column(String(32))
    x_field: Mapped[str] = mapped_column(String(128), default="")
    y_field: Mapped[str] = mapped_column(String(128), default="")
    aggregation: Mapped[str] = mapped_column(String(32), default="sum")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    insight: Mapped[str] = mapped_column(Text, default="")
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dataset: Mapped["Dataset"] = relationship(back_populates="charts")
    owner: Mapped["User"] = relationship(back_populates="charts")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    chart_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    layout_json: Mapped[str] = mapped_column(Text, default="[]")
    share_token: Mapped[str] = mapped_column(String(64), default="", index=True)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["User"] = relationship(back_populates="dashboards")
