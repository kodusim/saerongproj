"""
Django REST Framework용 JWT 인증 클래스
"""
from rest_framework import authentication
from rest_framework import exceptions
from api.toss_auth import get_user_from_token


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT 토큰 기반 인증 클래스

    Authorization 헤더에서 Bearer 토큰을 추출하여 검증합니다.
    Header: Authorization: Bearer <jwt_token>
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        """
        JWT 토큰 인증

        Returns:
            (user, token) 튜플 또는 None
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        # "Bearer <token>" 형식 파싱
        parts = auth_header.split()

        if len(parts) == 0:
            return None

        if parts[0].lower() != self.keyword.lower():
            return None

        if len(parts) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(parts) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            token = parts[1]
            user = get_user_from_token(token)

            if user is None:
                raise exceptions.AuthenticationFailed('Invalid token or user does not exist.')

            return (user, token)

        except ValueError as e:
            raise exceptions.AuthenticationFailed(str(e))
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Token validation failed: {str(e)}')

    def authenticate_header(self, request):
        """
        401 응답 시 WWW-Authenticate 헤더에 사용될 값
        """
        return self.keyword
