from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rankify.database import get_db_session
from rankify.db.models import Category, Item
from rankify.schemas import (
    AdminAddCategoryItemsRequest,
    AdminCategoryResponse,
    AdminCreateCategoryRequest,
    ItemOut,
)

router = APIRouter(prefix='/admin', tags=['admin'])


def require_admin_secret(
    request: Request,
    x_admin_secret: Annotated[str | None, Header()] = None,
) -> None:
    expected_secret = request.app.state.settings.admin_secret
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Admin routes are not configured',
        )
    if x_admin_secret is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing admin secret')
    if not compare_digest(x_admin_secret, expected_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid admin secret')


@router.post(
    '/categories',
    response_model=AdminCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_secret)],
)
async def create_category(
    payload: AdminCreateCategoryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminCategoryResponse:
    category = Category(name=payload.name, slug=payload.slug, description=payload.description)
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='Category slug already exists'
        ) from err

    await session.refresh(category)
    return AdminCategoryResponse(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
    )


@router.post(
    '/categories/{category_id}/items',
    response_model=list[ItemOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_secret)],
)
async def add_category_items(
    category_id: int,
    payload: AdminAddCategoryItemsRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ItemOut]:
    category_exists = await session.scalar(select(Category.id).where(Category.id == category_id))
    if category_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

    current_max_order = await session.scalar(
        select(func.max(Item.display_order)).where(Item.category_id == category_id)
    )

    requested_names_normalized = {item_name.lower() for item_name in payload.items}
    existing_names = (
        await session.execute(
            select(Item.name)
            .where(Item.category_id == category_id)
            .where(func.lower(Item.name).in_(requested_names_normalized))
        )
    ).scalars()
    duplicates = sorted({item_name.lower() for item_name in existing_names})
    if duplicates:
        duplicate_summary = ', '.join(duplicates)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Items already exist in category: {duplicate_summary}',
        )

    next_display_order = (current_max_order + 1) if current_max_order is not None else 0

    created_items: list[Item] = []
    for item_name in payload.items:
        item = Item(category_id=category_id, name=item_name, display_order=next_display_order)
        next_display_order += 1
        session.add(item)
        created_items.append(item)

    await session.flush()
    await session.commit()

    return [
        ItemOut(id=item.id, name=item.name, display_order=item.display_order)
        for item in created_items
    ]
