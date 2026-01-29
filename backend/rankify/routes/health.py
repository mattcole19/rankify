from fastapi import APIRouter

from rankify.database import ping_database
from rankify.version import __version__

router = APIRouter(tags=['health'])


@router.get('/health')
async def health() -> dict[str, str]:
    database_ok = await ping_database()
    return {
        'status': 'ok' if database_ok else 'degraded',
        'database': 'up' if database_ok else 'down',
        'version': __version__,
    }
