from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class XPathCache(Base):
    __tablename__ = "xpath_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instruction_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    url_pattern: Mapped[str] = mapped_column(String(2048), nullable=False)
    xpath: Mapped[str] = mapped_column(Text, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("hit_count", 0)
        super().__init__(**kwargs)
