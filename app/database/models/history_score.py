from typing import TYPE_CHECKING

from datetime import datetime
from datetime import timezone

from database.config import Base

from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .history import History


class HistoryScore(Base):
    __tablename__ = 'history_scores'

    id: Mapped[int] = mapped_column(primary_key=True)
    score: Mapped[float] = mapped_column(default=0.0, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    history_id: Mapped[int] = mapped_column(
        ForeignKey('histories.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )

    history: Mapped["History"] = relationship('History', back_populates='score_rel')

    __table_args__ = (
        UniqueConstraint('history_id', name='uix_history_score_history_id'),
    )


