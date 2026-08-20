"""구글 스칼라(Google Scholar) 검색 결과 스크래핑.

공식 API가 없어 HTML을 직접 파싱한다. 반복 요청 시 구글이
"비정상적인 트래픽" 안내와 함께 차단(캡차)할 수 있음 — 그 경우
ScholarBlockedError 를 던져 호출부에서 폴백 링크를 보여주게 한다.
"""
import requests
from bs4 import BeautifulSoup

SCHOLAR_URL = 'https://scholar.google.com/scholar'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}
TIMEOUT = 8


class ScholarBlockedError(Exception):
    pass


def search_scholar(query, num=10):
    resp = requests.get(
        SCHOLAR_URL,
        params={'q': query, 'hl': 'ko'},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()

    if 'systems have detected unusual traffic' in resp.text.lower() or 'gs_captcha' in resp.text:
        raise ScholarBlockedError('구글이 요청을 차단했습니다 (캡차)')

    soup = BeautifulSoup(resp.text, 'lxml')
    results = []
    for item in soup.select('div.gs_ri')[:num]:
        title_tag = item.select_one('h3.gs_rt')
        title = title_tag.get_text(' ', strip=True) if title_tag else '(제목 없음)'
        link_tag = title_tag.find('a') if title_tag else None
        link = link_tag.get('href') if link_tag else None

        meta_tag = item.select_one('div.gs_a')
        meta = meta_tag.get_text(' ', strip=True) if meta_tag else ''

        snippet_tag = item.select_one('div.gs_rs')
        snippet = snippet_tag.get_text(' ', strip=True) if snippet_tag else ''

        cited_by = ''
        for a in item.select('div.gs_fl a'):
            if '피인용' in a.text or 'Cited by' in a.text:
                cited_by = a.get_text(' ', strip=True)
                break

        results.append({
            'title': title,
            'link': link,
            'meta': meta,
            'snippet': snippet,
            'cited_by': cited_by,
        })
    return results
