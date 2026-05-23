from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExecutionSettings(Base):
    __tablename__ = "execution_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fallback_strategy: Mapped[str] = mapped_column(
        String(20), nullable=False, default="option_c"
    )
    timeout_per_tier_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_retry_per_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
