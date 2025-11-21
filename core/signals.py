from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import SubCategory
from sources.models import DataSource
from api.models import Game, GameCategory


@receiver(post_save, sender=SubCategory)
def create_game_from_subcategory(sender, instance, created, **kwargs):
    """
    SubCategory가 생성되면 자동으로 Game도 생성
    - slug → game_id
    - name → display_name
    - icon_image → icon_image (복사)
    """
    # Category가 'games'인 경우만 Game 생성
    if instance.category.slug == 'games':
        game, game_created = Game.objects.get_or_create(
            game_id=instance.slug,
            defaults={
                'display_name': instance.name,
                'is_active': instance.is_active
            }
        )

        # 아이콘 이미지 복사 (생성 시 또는 업데이트 시 모두)
        if instance.icon_image:
            game.icon_image = instance.icon_image

        # 이미 존재하는 경우 정보 업데이트
        if not game_created:
            game.display_name = instance.name
            game.is_active = instance.is_active

        game.save()

        if game_created:
            print(f"✅ Auto-created Game: {game.display_name} (game_id: {game.game_id})")
        else:
            print(f"🔄 Updated existing Game: {game.display_name}")


@receiver(post_save, sender=DataSource)
def create_game_category_from_datasource(sender, instance, created, **kwargs):
    """
    DataSource가 생성되면 자동으로 GameCategory도 생성
    - DataSource의 name → GameCategory의 name
    - SubCategory의 slug → Game의 game_id로 매핑
    """
    if created:
        # SubCategory가 games 카테고리에 속한 경우만 처리
        if instance.subcategory.category.slug == 'games':
            try:
                # SubCategory의 slug를 game_id로 사용하여 Game 찾기
                game = Game.objects.get(game_id=instance.subcategory.slug)

                # GameCategory 생성 (중복 방지)
                category, cat_created = GameCategory.objects.get_or_create(
                    game=game,
                    name=instance.name
                )

                if cat_created:
                    print(f"✅ Auto-created GameCategory: {game.display_name} - {category.name}")
                else:
                    print(f"ℹ️  GameCategory already exists: {game.display_name} - {category.name}")

            except Game.DoesNotExist:
                print(f"⚠️  Game not found for slug: {instance.subcategory.slug}")
                print(f"   Creating Game first...")

                # Game이 없으면 먼저 생성
                game = Game.objects.create(
                    game_id=instance.subcategory.slug,
                    display_name=instance.subcategory.name,
                    is_active=instance.subcategory.is_active
                )

                # 그 다음 GameCategory 생성
                GameCategory.objects.get_or_create(
                    game=game,
                    name=instance.name
                )
                print(f"✅ Created Game and GameCategory: {game.display_name} - {instance.name}")
