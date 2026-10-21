"""Public-site configuration, isolated from the existing TDM settings."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import BASE_DIR


class SiteSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / '.env', BASE_DIR / '.site.env'),
        env_file_encoding='utf-8', extra='ignore',
    )
    site_store: Path = BASE_DIR / 'private_data' / 'inquiries.sqlite3'
    travel_catalog: Path = BASE_DIR / 'private_data' / 'travel' / 'catalog.json'
    site_origin: str = 'https://saerong.com'
    inquiry_to: str = ''
    smtp_host: str = ''
    smtp_port: int = 465
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_from: str = ''
    smtp_ssl: bool = True
    site_admin_user: str = ''
    site_admin_password_hash: str = ''


site_settings = SiteSettings()
