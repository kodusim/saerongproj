from django.test import TestCase

# 앱의 테스트 코드
class MiscTestCase(TestCase):
    def setUp(self):
        # 테스트 설정
        pass

    def test_home_page(self):
        """홈페이지가 제대로 로드되는지 테스트"""
        response = self.client.get('/misc/')
        self.assertEqual(response.status_code, 200)