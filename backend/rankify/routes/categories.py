from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from rankify.database import get_db_session
from rankify.db.models import Category, Item, RankingEntry, RankingSubmission
from rankify.schemas import (
    CategoryDetail,
    CategoryListItem,
    CommunityRankingItem,
    CommunityRankingResponse,
    ItemOut,
)

router = APIRouter(prefix='/categories', tags=['categories'])


@router.get('', response_model=list[CategoryListItem])
async def list_categories(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CategoryListItem]:
    query = (
        select(Category.id, Category.slug, Category.name, func.count(Item.id).label('item_count'))
        .outerjoin(Item, Item.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name.asc())
    )
    rows = (await session.execute(query)).all()
    return [
        CategoryListItem(id=row.id, slug=row.slug, name=row.name, item_count=row.item_count)
        for row in rows
    ]


@router.get('/{category_slug}', response_model=CategoryDetail)
async def get_category(
    category_slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryDetail:
    category = await session.scalar(
        select(Category)
        .where(Category.slug == category_slug)
        .options(selectinload(Category.items), selectinload(Category.submissions))
    )
    if category is None:
        raise HTTPException(status_code=404, detail='Category not found')

    items = sorted(category.items, key=lambda item: item.display_order)
    return CategoryDetail(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        submission_count=len(category.submissions),
        items=[ItemOut.model_validate(item) for item in items],
    )


@router.get('/{category_slug}/community-ranking', response_model=CommunityRankingResponse)
async def get_community_ranking(
    category_slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CommunityRankingResponse:
    category = await session.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        raise HTTPException(status_code=404, detail='Category not found')

    total_submissions = await session.scalar(
        select(func.count(RankingSubmission.id)).where(RankingSubmission.category_id == category.id)
    )
    ranking_rows = (
        await session.execute(
            select(
                Item.id.label('item_id'),
                Item.name.label('item_name'),
                func.avg(RankingEntry.rank).label('average_rank'),
                func.count(RankingEntry.submission_id).label('vote_count'),
            )
            .outerjoin(RankingEntry, RankingEntry.item_id == Item.id)
            .where(Item.category_id == category.id)
            .group_by(Item.id)
            .order_by(func.coalesce(func.avg(RankingEntry.rank), 1_000_000), Item.display_order)
        )
    ).all()

    return CommunityRankingResponse(
        category_id=category.id,
        category_slug=category.slug,
        total_submissions=total_submissions or 0,
        items=[
            CommunityRankingItem(
                item_id=row.item_id,
                item_name=row.item_name,
                average_rank=float(row.average_rank) if row.average_rank is not None else None,
                vote_count=row.vote_count,
            )
            for row in ranking_rows
        ],
    )
