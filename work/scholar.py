"""구글 스칼라(Google Scholar) 검색 결과 스크래핑.

공식 API가 없어 HTML을 직접 파싱한다. 반복 요청 시 구글이
"비정상적인 트래픽" 안내와 함께 차단(캡차)할 수 있음 — 그 경우
ScholarBlockedError 를 던져 호출부에서 폴백 링크를 보여주게 한다.

실제 마크업(scholar.google.com, 2026-08 기준) 구조:
  div.gs_r.gs_or.gs_scl
    div.gs_ggs.gs_fl > div.gs_ggsd > div.gs_or_ggsm > a > span.gs_ctg2 "[PDF]" + 도메인
    div.gs_ri
      h3.gs_rt > a  (제목, 검색어는 <b> 로 하이라이트)
      div.gs_a      (저자 - 저널·연도 - 출판사, 저자명은 <a> 링크)
      div.gs_rs     (스니펫, 매칭 키워드 <b>)
      div.gs_fl.gs_flb > a[...]  (저장/인용/관련 학술자료/전체 버전)
"""
from html import escape
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString

SCHOLAR_BASE = 'https://scholar.google.com'
SCHOLAR_URL = f'{SCHOLAR_BASE}/scholar'
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


def _inline_html(tag, link_class=''):
    """<b>(하이라이트)·<a>(링크)만 허용해 원본 서식을 보존하고,
    그 외 텍스트는 escape 해서 삽입한다 — 임의 HTML 주입 불가."""
    if tag is None:
        return ''
    out = []
    for node in tag.children:
        if isinstance(node, NavigableString):
            out.append(escape(str(node)))
        elif node.name == 'b':
            out.append(f'<strong>{_inline_html(node, link_class)}</strong>')
        elif node.name == 'a':
            href = node.get('href') or ''
            inner = _inline_html(node, link_class)
            if href and not href.lower().startswith('javascript:'):
                abs_href = urljoin(SCHOLAR_BASE + '/', href)
                cls = f' class="{link_class}"' if link_class else ''
                out.append(
                    f'<a{cls} href="{escape(abs_href, quote=True)}" '
                    f'target="_blank" rel="noopener">{inner}</a>'
                )
            else:
                out.append(inner)
        else:
            out.append(escape(node.get_text()))
    return ''.join(out)


def _footer_links(ri):
    links = []
    fl = ri.select_one('div.gs_fl.gs_flb') or ri.select_one('div.gs_fl')
    if not fl:
        return links
    for a in fl.find_all('a'):
        text = a.get_text(' ', strip=True)
        href = a.get('href') or ''
        if not text or not href or href.lower().startswith('javascript:'):
            continue
        links.append({'text': text, 'url': urljoin(SCHOLAR_BASE + '/', href)})
    return links


def search_scholar(query, num=10):
    resp = requests.get(
        SCHOLAR_URL,
        params={'q': query, 'hl': 'ko'},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()

    if 'systems have detected unusual traffic' in resp.text.lower() or 'id="gs_captcha_f"' in resp.text:
        raise ScholarBlockedError('구글이 요청을 차단했습니다 (캡차)')

    soup = BeautifulSoup(resp.text, 'lxml')

    stats_tag = soup.select_one('#gs_ab_md .gs_ab_mdw') or soup.select_one('#gs_ab_md')
    stats = stats_tag.get_text(' ', strip=True) if stats_tag else ''

    results = []
    for row in soup.select('div.gs_r.gs_or.gs_scl')[:num]:
        ri = row.select_one('div.gs_ri')
        if not ri:
            continue

        title_tag = ri.select_one('h3.gs_rt')
        link_tag = title_tag.find('a') if title_tag else None
        if link_tag:
            title_html = _inline_html(link_tag)
            link = link_tag.get('href')
        else:
            title_html = escape(title_tag.get_text(' ', strip=True)) if title_tag else '(제목 없음)'
            link = None

        meta_html = _inline_html(ri.select_one('div.gs_a'), link_class='s-author-link')
        snippet_html = _inline_html(ri.select_one('div.gs_rs'))

        source_a = row.select_one('div.gs_or_ggsm a')
        source_label, source_site, source_link = '', '', None
        if source_a:
            label_tag = source_a.select_one('span.gs_ctg2')
            source_label = label_tag.get_text(strip=True) if label_tag else ''
            source_site = source_a.get_text(' ', strip=True)
            if source_label:
                source_site = source_site.replace(source_label, '', 1).strip()
            source_link = source_a.get('href')

        results.append({
            'title_html': title_html,
            'link': link,
            'meta_html': meta_html,
            'snippet_html': snippet_html,
            'source_label': source_label,
            'source_site': source_site,
            'source_link': source_link,
            'footer_links': _footer_links(ri),
        })

    return {'stats': stats, 'results': results}
