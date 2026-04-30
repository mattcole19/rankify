from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rankify.database import get_db_session
from rankify.db.models import Category
from rankify.schemas import AdminCategoryResponse, AdminCreateCategoryRequest

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
