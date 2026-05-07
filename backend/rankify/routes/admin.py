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
    AdminCategoryDetailResponse,
    AdminCategoryListItem,
    AdminCategoryResponse,
    AdminCreateCategoryRequest,
    AdminCreateCategoryVersionRequest,
    AdminUpdateCategoryRequest,
    AdminUpdateItemRequest,
    ItemOut,
)

router = APIRouter(prefix='/admin', tags=['admin'])

IMMUTABLE_PUBLISHED_DETAIL = 'Published versions are immutable; create a new version instead'


@router.get(
    '/categories',
    response_model=list[AdminCategoryListItem],
    dependencies=[Depends(require_admin_access)],
)
async def list_admin_categories(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AdminCategoryListItem]:
    rows = (
        await session.execute(
            select(
                Category.id,
                Category.slug,
                Category.name,
                Category.version_number,
                Category.status,
                func.count(Item.id).label('item_count'),
            )
            .outerjoin(Item, Item.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name.asc(), Category.version_number.desc())
        )
    ).all()
    return [
        AdminCategoryListItem(
            id=row.id,
            slug=row.slug,
            name=row.name,
            version_number=row.version_number,
            status=row.status,
            item_count=row.item_count,
        )
        for row in rows
    ]


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
    await session.flush()
    for index, item_name in enumerate(payload.items):
        session.add(Item(category_id=category.id, name=item_name, display_order=index))

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


@router.get(
    '/categories/{category_id}',
    response_model=AdminCategoryDetailResponse,
    dependencies=[Depends(require_admin_access)],
)
async def get_admin_category(
    category_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminCategoryDetailResponse:
    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')

    items = (
        await session.execute(
            select(Item)
            .where(Item.category_id == category.id)
            .order_by(Item.display_order.asc(), Item.id.asc())
        )
    ).scalars().all()

    return AdminCategoryDetailResponse(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        version_number=category.version_number,
        status=category.status,
        items=[ItemOut(id=item.id, name=item.name, display_order=item.display_order) for item in items],
    )


@router.patch(
    '/categories/{category_id}',
    response_model=AdminCategoryResponse,
    dependencies=[Depends(require_admin_access)],
)
async def update_category(
    category_id: int,
    payload: AdminUpdateCategoryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminCategoryResponse:
    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    if category.status != 'draft':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IMMUTABLE_PUBLISHED_DETAIL)

    category.name = payload.name
    category.description = payload.description
    await session.commit()
    await session.refresh(category)

    return AdminCategoryResponse(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        version_number=category.version_number,
        status=category.status,
    )


@router.delete(
    '/categories/{category_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_access)],
)
async def delete_category(
    category_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    if category.status != 'draft':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IMMUTABLE_PUBLISHED_DETAIL)

    await session.delete(category)
    await session.commit()


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

    for index, item_name in enumerate(payload.items):
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
    '/categories/{category_id}/publish',
    response_model=AdminCategoryResponse,
    dependencies=[Depends(require_admin_access)],
)
async def publish_category_version(
    category_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminCategoryResponse:
    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    if category.status != 'draft':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Category is already published')

    item_count = await session.scalar(select(func.count(Item.id)).where(Item.category_id == category.id))
    if (item_count or 0) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category requires at least two items before publishing',
        )

    category.status = 'published'
    await session.commit()
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
    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    if category.status != 'draft':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IMMUTABLE_PUBLISHED_DETAIL)

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


@router.patch(
    '/categories/{category_id}/items/{item_id}',
    response_model=ItemOut,
    dependencies=[Depends(require_admin_access)],
)
async def update_category_item(
    category_id: int,
    item_id: int,
    payload: AdminUpdateItemRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ItemOut:
    item = await session.scalar(
        select(Item).where(Item.id == item_id, Item.category_id == category_id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Item not found')

    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    if category.status != 'draft':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IMMUTABLE_PUBLISHED_DETAIL)

    duplicate_name = await session.scalar(
        select(Item.id).where(
            Item.category_id == category_id,
            func.lower(Item.name) == payload.name.lower(),
            Item.id != item_id,
        )
    )
    if duplicate_name is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Items already exist in category: {payload.name.lower()}',
        )

    item.name = payload.name
    await session.commit()
    await session.refresh(item)
    return ItemOut(id=item.id, name=item.name, display_order=item.display_order)


@router.delete(
    '/categories/{category_id}/items/{item_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_access)],
)
async def delete_category_item(
    category_id: int,
    item_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    category = await session.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found')
    if category.status != 'draft':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IMMUTABLE_PUBLISHED_DETAIL)

    item = await session.scalar(select(Item).where(Item.id == item_id, Item.category_id == category_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Item not found')

    await session.delete(item)
    await session.flush()

    remaining_items = (
        await session.execute(
            select(Item)
            .where(Item.category_id == category_id)
            .order_by(Item.display_order.asc(), Item.id.asc())
        )
    ).scalars().all()
    for index, remaining_item in enumerate(remaining_items):
        remaining_item.display_order = index

    await session.commit()
