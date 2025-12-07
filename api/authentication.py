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
        path = request.path

        if not auth_header:
            print(f"[JWTAuth] No auth header for {path}")
            return None

        # "Bearer <token>" 형식 파싱
        parts = auth_header.split()

        if len(parts) == 0:
            print(f"[JWTAuth] Empty auth header parts for {path}")
            return None

        if parts[0].lower() != self.keyword.lower():
            print(f"[JWTAuth] Wrong keyword '{parts[0]}' for {path}")
            return None

        if len(parts) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(parts) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            token = parts[1]
            token_preview = token[:20] + '...' if len(token) > 20 else token
            print(f"[JWTAuth] Validating token for {path}: {token_preview}")

            user = get_user_from_token(token)

            if user is None:
                print(f"[JWTAuth] User not found for token on {path}")
                raise exceptions.AuthenticationFailed('Invalid token or user does not exist.')

            print(f"[JWTAuth] Authenticated user {user.id} for {path}")
            return (user, token)

        except ValueError as e:
            print(f"[JWTAuth] ValueError for {path}: {e}")
            raise exceptions.AuthenticationFailed(str(e))
        except Exception as e:
            print(f"[JWTAuth] Exception for {path}: {e}")
            raise exceptions.AuthenticationFailed(f'Token validation failed: {str(e)}')

    def authenticate_header(self, request):
        """
        401 응답 시 WWW-Authenticate 헤더에 사용될 값
        """
        return self.keyword
