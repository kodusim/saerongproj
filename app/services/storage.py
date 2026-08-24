"""업로드 파일 저장.

Django ImageField(`upload_to='work/chat/%Y/%m/'`) 가 쓰던 경로 규칙과 파일명
정제 방식을 그대로 따른다 — 기존에 올라간 파일과 DB 의 상대경로가 계속 유효해야 한다.
"""
import io
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import settings

MAX_IMAGE_BYTES = 8 * 1024 * 1024
CHUNK = 1024 * 1024


class ImageTooLargeError(Exception):
    pass


class InvalidImageError(Exception):
    pass


def _safe_filename(name: str) -> str:
    """Django `get_valid_filename` 과 같은 규칙: 공백 → '_', 허용 문자 외 제거."""
    name = unicodedata.normalize('NFC', (name or '').strip()).replace(' ', '_')
    name = re.sub(r'(?u)[^-\w.가-힣]', '', name)
    name = name.lstrip('.') or 'upload'
    return name[:80]


def _unique_path(directory: Path, filename: str) -> Path:
    """이미 있으면 Django 처럼 접미사를 붙여 충돌을 피한다."""
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    for n in range(1, 1000):
        candidate = directory / f'{stem}_{n}{suffix}'
        if not candidate.exists():
            return candidate
    raise InvalidImageError('파일명 충돌을 해결할 수 없습니다.')


async def save_chat_image(upload: UploadFile) -> str:
    """채팅 첨부 이미지를 저장하고 MEDIA_ROOT 기준 상대경로를 돌려준다."""
    data = bytearray()
    while chunk := await upload.read(CHUNK):
        data.extend(chunk)
        if len(data) > MAX_IMAGE_BYTES:
            raise ImageTooLargeError

    if not data:
        raise InvalidImageError

    # 실제 이미지인지 검증 (확장자만 믿지 않는다)
    try:
        Image.open(io.BytesIO(bytes(data))).verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise InvalidImageError

    now = datetime.now(timezone.utc)
    rel_dir = Path('work') / 'chat' / f'{now:%Y}' / f'{now:%m}'
    abs_dir = settings.media_root / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    target = _unique_path(abs_dir, _safe_filename(upload.filename or 'upload'))
    target.write_bytes(bytes(data))

    return (rel_dir / target.name).as_posix()
