"""애플리케이션 설정. 기존 Django .env 를 그대로 읽는다."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    debug: bool = False
    secret_key: str = 'insecure-dev-key-change-me'

    # Django 시절 .env 의 DATABASE_URL 을 그대로 쓴다 (postgresql:// → asyncpg 로 변환).
    database_url: str = 'postgresql://postgres:postgres@localhost:5432/saerong'

    # /tdmprediction 단일 계정
    tdm_auth_user: str = 'tdm'
    tdm_auth_password: str = 'tdm1234'

    # 업로드 파일 — nginx 가 /media 로 서빙하는 실제 디렉토리
    media_root: Path = BASE_DIR / 'mediafiles'
    media_url: str = '/media/'

    # TDM 모델 가중치 (용량 때문에 git 제외, 서버에 직접 업로드)
    ml_artifacts_dir: Path = BASE_DIR / 'ml_artifacts'

    session_cookie: str = 'saerong_session'
    csrf_cookie: str = 'csrftoken'

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith('postgresql+asyncpg://'):
            return url
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url.replace('postgresql://', 'postgresql+asyncpg://', 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
