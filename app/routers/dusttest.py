"""Dust measurement dashboard mockup."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import templates

router = APIRouter(prefix='/dusttest', tags=['dusttest'])


@router.get('/', response_class=HTMLResponse)
async def dusttest_page(request: Request):
    return templates.TemplateResponse(request, 'dusttest/index.html', {})
