/* fetch 래퍼 — CSRF 헤더를 자동으로 붙인다.
   서버는 csrftoken 쿠키와 X-CSRFToken 헤더를 double-submit 으로 검증한다
   (app/security.py). 쿠키는 매 요청마다 다시 읽는다 — 첫 방문 때 응답으로
   내려오므로 모듈 로드 시점에 캐시하면 비어 있을 수 있다. */
import { getCookie } from './dom.js';

const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

async function request(url, { method = 'GET', body, json } = {}) {
    const headers = {};
    if (UNSAFE.has(method)) headers['X-CSRFToken'] = getCookie('csrftoken');
    if (json !== undefined) headers['Content-Type'] = 'application/json';

    const res = await fetch(url, {
        method,
        headers,
        credentials: 'same-origin',
        body: json !== undefined ? JSON.stringify(json) : body,
    });

    let data = null;
    try {
        data = await res.json();
    } catch { /* 본문이 JSON 이 아니면 null 로 둔다 */ }

    return { ok: res.ok, status: res.status, data };
}

export const api = {
    get: (url) => request(url),
    postForm: (url, formData) => request(url, { method: 'POST', body: formData }),
    postJSON: (url, obj) => request(url, { method: 'POST', json: obj }),
    del: (url) => request(url, { method: 'DELETE' }),
};
