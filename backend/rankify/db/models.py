from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rankify.db.base import Base


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list[Item]] = relationship(
        back_populates='category', cascade='all, delete-orphan'
    )
    submissions: Mapped[list[RankingSubmission]] = relationship(
        back_populates='category', cascade='all, delete-orphan'
    )


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey('categories.id', ondelete='CASCADE'), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped[Category] = relationship(back_populates='items')


class RankingSubmission(Base):
    __tablename__ = 'ranking_submissions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey('categories.id', ondelete='CASCADE'), index=True
    )
    anon_id: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped[Category] = relationship(back_populates='submissions')
    entries: Mapped[list[RankingEntry]] = relationship(
        back_populates='submission', cascade='all, delete-orphan'
    )


class RankingEntry(Base):
    __tablename__ = 'ranking_entries'
    __table_args__ = (
        UniqueConstraint('submission_id', 'rank', name='uq_ranking_entries_submission_rank'),
    )

    submission_id: Mapped[int] = mapped_column(
        ForeignKey('ranking_submissions.id', ondelete='CASCADE'), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey('items.id', ondelete='CASCADE'), primary_key=True
    )
    rank: Mapped[int] = mapped_column(Integer)

    submission: Mapped[RankingSubmission] = relationship(back_populates='entries')
    item: Mapped[Item] = relationship()
