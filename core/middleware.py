class SocialSharingCSPMiddleware:
    """
    소셜 미디어 공유에 필요한 CSP 헤더를 추가하는 미들웨어
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # CSP 헤더가 이미 있는지 확인
        if 'Content-Security-Policy' in response:
            csp = response['Content-Security-Policy']
            
            # 카카오 도메인 추가
            if 'script-src' in csp and 'https://t1.kakaocdn.net' not in csp:
                csp = csp.replace('script-src', 'script-src https://t1.kakaocdn.net https://developers.kakao.com')
            
            # 이미지 소스에 카카오 도메인 추가
            if 'img-src' in csp and 'https://developers.kakao.com' not in csp:
                csp = csp.replace('img-src', 'img-src https://developers.kakao.com https://*.kakao.com')
            
            # 연결 소스에 카카오 도메인 추가
            if 'connect-src' not in csp:
                csp += "; connect-src 'self' https://*.kakao.com"
            elif 'https://*.kakao.com' not in csp:
                csp = csp.replace('connect-src', 'connect-src https://*.kakao.com')
            
            response['Content-Security-Policy'] = csp
            
        return response