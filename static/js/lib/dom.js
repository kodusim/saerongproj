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

export function formatDateTime(iso) {
    const d = new Date(iso);
    return d.toLocaleString('ko-KR', {
        month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
    });
}
