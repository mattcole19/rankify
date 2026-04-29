from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rankify.database import get_db_session
from rankify.db.models import Item, RankingEntry, RankingSubmission
from rankify.schemas import RankingSubmitRequest, RankingSubmitResponse

router = APIRouter(prefix='/rankings', tags=['rankings'])


@router.post('', response_model=RankingSubmitResponse, status_code=201)
async def submit_ranking(
    payload: RankingSubmitRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RankingSubmitResponse:
    valid_items = (
        await session.execute(
            select(Item.id).where(
                Item.category_id == payload.category_id, Item.id.in_(payload.ordered_item_ids)
            )
        )
    ).scalars()
    valid_item_ids = set(valid_items)
    payload_item_ids = set(payload.ordered_item_ids)
    if valid_item_ids != payload_item_ids:
        raise HTTPException(
            status_code=400, detail='ordered_item_ids must all belong to the category'
        )

    expected_item_count = await session.scalar(
        select(func.count(Item.id)).where(Item.category_id == payload.category_id)
    )
    if expected_item_count != len(payload.ordered_item_ids):
        raise HTTPException(
            status_code=400, detail='ranking must include every item in the category'
        )

    submission = RankingSubmission(
        category_id=payload.category_id,
        anon_id=payload.anon_id or uuid4().hex,
    )
    session.add(submission)
    await session.flush()

    for rank, item_id in enumerate(payload.ordered_item_ids, start=1):
        session.add(RankingEntry(submission_id=submission.id, item_id=item_id, rank=rank))

    await session.commit()
    return RankingSubmitResponse(submission_id=submission.id, anon_id=submission.anon_id)
