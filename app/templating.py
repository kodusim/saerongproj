"""Jinja2 템플릿 설정."""
from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR

templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))


def _csrf_token(request: Request) -> str:
    return getattr(request.state, 'csrf_token', '')


# 템플릿에서 {{ csrf_token(request) }} 로 쓴다.
templates.env.globals['csrf_token'] = _csrf_token
