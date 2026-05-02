from __future__ import annotations

from hmac import compare_digest
from typing import Annotated, Any

import httpx
from fastapi import HTTPException, Header, Request, status


async def require_admin_access(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_secret: Annotated[str | None, Header()] = None,
) -> None:
    settings = request.app.state.settings

    if authorization and authorization.startswith('Bearer '):
        token = authorization.removeprefix('Bearer ').strip()
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing bearer token')
        await _validate_bearer_admin(request, token)
        return

    if settings.admin_secret:
        if x_admin_secret is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Missing admin authentication (bearer token or admin secret)',
            )
        if not compare_digest(x_admin_secret, settings.admin_secret):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid admin secret')
        return

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail='Admin auth is not configured',
    )


async def _validate_bearer_admin(request: Request, token: str) -> None:
    settings = request.app.state.settings
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Supabase auth is not configured',
        )

    user = await _fetch_supabase_user(settings.supabase_url, settings.supabase_anon_key, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid bearer token')

    email = str(user.get('email') or '').strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Authenticated user has no email')
    if not settings.admin_emails:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='No admin emails configured',
        )
    if email not in settings.admin_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User is not an admin')


async def _fetch_supabase_user(supabase_url: str, anon_key: str, token: str) -> dict[str, Any] | None:
    endpoint = f"{supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        'Authorization': f'Bearer {token}',
        'apikey': anon_key,
    }
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(endpoint, headers=headers)
    if response.status_code != 200:
        return None
    return response.json()
