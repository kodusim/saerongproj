from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from psychotest.models import Test
from facetest.models import FaceTestModel
from community.models import Post

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return ['core:root', 'psychotest:test_list', 'facetest:test_list', 'community:category_list']

    def location(self, item):
        return reverse(item)

class PsychoTestSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Test.objects.all()

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse('psychotest:test_intro', args=[obj.id])

class FaceTestSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return FaceTestModel.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('facetest:test_intro', args=[obj.id])

class CommunityPostSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Post.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('community:post_detail', args=[obj.id])