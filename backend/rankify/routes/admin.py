from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rankify.auth import require_admin_access
from rankify.database import get_db_session
from rankify.db.models import Category, Item
from rankify.schemas import (
    AdminAddCategoryItemsRequest,
    AdminCategoryResponse,
    AdminCreateCategoryRequest,
    AdminCreateCategoryVersionRequest,
    ItemOut,
)

router = APIRouter(prefix='/admin', tags=['admin'])


@router.post(
    '/categories',
    response_model=AdminCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_access)],
)
async def create_category(
    payload: AdminCreateCategoryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminCategoryResponse:
    existing_slug = await session.scalar(select(Category.id).where(Category.slug == payload.slug).limit(1))
    if existing_slug is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Category slug already exists')

    category = Category(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        version_number=1,
        status='published',
    )
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
        version_number=category.version_number,
        status=category.status,
    )


@router.post(
    '/categories/{category_slug}/versions',
    response_model=AdminCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_access)],
)
async def create_category_version(
    category_slug: str,
    payload: AdminCreateCategoryVersionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminCategoryResponse:
    latest_published = await session.scalar(
        select(Category)
        .where(Category.slug == category_slug, Category.status == 'published')
        .order_by(Category.version_number.desc())
        .limit(1)
    )
    if latest_published is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

    current_items = (
        await session.execute(
            select(Item.name)
            .where(Item.category_id == latest_published.id)
            .order_by(Item.display_order.asc())
        )
    ).scalars().all()
    existing_names_normalized = {item.lower() for item in current_items}
    new_names_normalized = {item.lower() for item in payload.new_items}
    overlaps = sorted(existing_names_normalized.intersection(new_names_normalized))
    if overlaps:
        overlap_summary = ', '.join(overlaps)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Items already exist in category: {overlap_summary}',
        )

    next_version_number = latest_published.version_number + 1
    version_description = (
        payload.description if payload.description is not None else latest_published.description
    )
    new_version = Category(
        slug=latest_published.slug,
        name=latest_published.name,
        description=version_description,
        version_number=next_version_number,
        status='published',
    )
    session.add(new_version)
    await session.flush()

    combined_items = [*current_items, *payload.new_items]
    for index, item_name in enumerate(combined_items):
        session.add(Item(category_id=new_version.id, name=item_name, display_order=index))

    await session.commit()
    await session.refresh(new_version)

    return AdminCategoryResponse(
        id=new_version.id,
        slug=new_version.slug,
        name=new_version.name,
        description=new_version.description,
        version_number=new_version.version_number,
        status=new_version.status,
    )


@router.post(
    '/categories/{category_id}/items',
    response_model=list[ItemOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_access)],
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
