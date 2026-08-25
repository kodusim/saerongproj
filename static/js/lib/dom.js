/* 자주 쓰는 DOM / 포맷 헬퍼 */

export const $ = (id) => document.getElementById(id);

export function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? decodeURIComponent(v.pop()) : '';
}

/** 텍스트를 HTML 에 넣기 전 이스케이프. innerHTML 조립 시 반드시 통과시킨다. */
export function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : s;
    return d.innerHTML;
}

/* URL 앞뒤로 붙기 쉬운 문장부호 — 링크에서 떼어낸다 */
const TRAILING = /[.,!?)\]}>'"·…]+$/;
const URL_RE = /(https?:\/\/[^\s<]+|www\.[^\s<]+)/g;

/**
 * 평문을 escape 한 뒤 URL 부분만 <a> 로 바꾼 HTML 을 돌려준다.
 * 반드시 escape 를 먼저 하므로 원문에 든 태그는 링크가 되지 않는다.
 */
export function linkify(text) {
    const escaped = escapeHtml(text);
    return escaped.replace(URL_RE, (match) => {
        const trail = (match.match(TRAILING) || [''])[0];
        const url = trail ? match.slice(0, -trail.length) : match;
        if (!url) return match;
        const href = url.startsWith('www.') ? `https://${url}` : url;
        return `<a href="${href}" target="_blank" rel="noopener noreferrer">${url}</a>${trail}`;
    });
}

export function formatDateTime(iso) {
    const d = new Date(iso);
    return d.toLocaleString('ko-KR', {
        month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
    });
}
