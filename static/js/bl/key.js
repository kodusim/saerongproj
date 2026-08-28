/* 작가 키 — 계정이 없던 시절 "이 작품은 내 것"의 근거였다.

   **지금은 쓰이지 않는다.** 계정 로그인이 붙어서 서버(app/routers/bl.py)가
   세션으로 작가를 가르고 `X-Author-Key` 헤더를 아예 읽지 않는다. 남아 있는
   authorHeaders() 호출은 무해한 빈 껍데기다 — 정리 대상.

   예전 방식: IP 로 가르면 공유기 재접속·모바일 전환만으로 작가가 수정 권한을
   잃으므로, 브라우저가 만든 랜덤 토큰을 localStorage 에 두고 헤더로 보냈다. */

const KEY_STORAGE = 'bl_author_key';

/** 서버의 AUTHOR_KEY_RE (^[A-Za-z0-9_-]{16,64}$) 와 같은 규칙 */
const KEY_RE = /^[A-Za-z0-9_-]{16,64}$/;

function generate() {
    const bytes = new Uint8Array(24);
    crypto.getRandomValues(bytes);
    // base64url — 서버 정규식이 허용하는 문자만 남긴다
    return btoa(String.fromCharCode(...bytes))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** 저장된 키를 돌려준다. 없으면 만들지 않고 빈 문자열 (읽기 전용 방문자). */
export function peekKey() {
    try {
        const k = localStorage.getItem(KEY_STORAGE) || '';
        return KEY_RE.test(k) ? k : '';
    } catch {
        return '';
    }
}

/** 저장된 키를 돌려주되, 없으면 새로 만들어 저장한다 (글을 쓰려 할 때). */
export function ensureKey() {
    const existing = peekKey();
    if (existing) return existing;
    const fresh = generate();
    try {
        localStorage.setItem(KEY_STORAGE, fresh);
    } catch { /* 저장 못 하면 이번 세션에만 유효하다 */ }
    return fresh;
}

/** 다른 기기에서 쓰던 키를 넣는다. 형식이 틀리면 false. */
export function setKey(raw) {
    const k = (raw || '').trim();
    if (!KEY_RE.test(k)) return false;
    try {
        localStorage.setItem(KEY_STORAGE, k);
    } catch { /* 무시 */ }
    return true;
}

/** api.js 의 요청에 붙일 헤더 — 키가 없으면 아무것도 붙이지 않는다. */
export function authorHeaders() {
    const k = peekKey();
    return k ? { 'X-Author-Key': k } : {};
}
