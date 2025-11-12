"""
Fix MapleStory DataSources on production server
Run this on the server after deploying the platform.system() fix
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saerong.settings')
django.setup()

from sources.models import DataSource

# Configs for each page type
notice_config = {
    "selectors": {
        "container": ".news_board ul li",
        "title": "p a span",
        "url": "p a",
        "date": ".heart_date dd"
    },
    "base_url": "https://maplestory.nexon.com",
    "wait_selector": ".news_board",
    "game_name": "메이플스토리",
    "max_items": 20
}

update_config = {
    "selectors": {
        "container": ".update_board ul li",
        "title": "p a span",
        "url": "p a",
        "date": ".heart_date dd"
    },
    "base_url": "https://maplestory.nexon.com",
    "wait_selector": ".update_board",
    "game_name": "메이플스토리",
    "max_items": 20
}

event_config = {
    "selectors": {
        "container": ".event_list_wrap",
        "title": "em.event_listMt",
        "url": ".data a",
        "date": ".date p"
    },
    "base_url": "https://maplestory.nexon.com",
    "wait_selector": ".event_board",
    "game_name": "메이플스토리",
    "max_items": 20
}

print("Fixing MapleStory DataSources on server...\n")

# Find and fix/create DataSources by URL
sources_config = [
    ("https://maplestory.nexon.com/News/Notice", "메이플스토리 공지사항", "selenium", notice_config),
    ("https://maplestory.nexon.com/News/Update", "메이플스토리 업데이트", "selenium", update_config),
    ("https://maplestory.nexon.com/News/Event", "메이플스토리 이벤트", "selenium", event_config),
]

from sources.models import SubCategory

# Get or create subcategory
subcategory, _ = SubCategory.objects.get_or_create(
    slug='game-notice',
    defaults={'name': '게임 공지사항', 'category_id': 1}
)

for url, name, crawler_type, config in sources_config:
    # Find existing or create new
    source, created = DataSource.objects.get_or_create(
        url=url,
        defaults={
            'name': name,
            'subcategory': subcategory,
            'crawler_type': crawler_type,
            'crawler_class': '',
            'config': config,
            'crawl_interval': 60,  # 1 hour
            'is_active': True
        }
    )

    if created:
        print(f"[CREATED] {name}")
        print(f"  URL: {url}")
        print(f"  Crawler: {crawler_type}")
    else:
        print(f"[UPDATED] {name} (ID: {source.id})")
        print(f"  Old config: {source.config}")

        # Update config and crawler_type
        source.crawler_type = crawler_type
        source.crawler_class = ''
        source.config = config
        source.is_active = True
        source.save()

        print(f"  New config: {config}")
        print(f"  Crawler: {crawler_type}")

    print()

print("Done! All MapleStory DataSources are now configured correctly.")
print("\nNext steps:")
print("1. Restart Celery worker: sudo supervisorctl restart celery")
print("2. Check logs: sudo tail -f /var/log/celery/worker.log")
