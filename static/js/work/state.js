/* 화면 전체가 공유하는 상태.

   테마(그룹웨어 / VS Code)는 **외형만** 바꾼다 — 채팅·게시판의 내용과 화면
   상태는 그대로 유지된다. 그래서 상태는 여기 한 벌만 두고, 테마별 DOM 두 벌에
   같은 내용을 렌더링한다.

   모듈 간 순환 import 를 피하려고 구독(subscribe) 방식을 쓴다: theme/nav 가
   바뀌면 등록된 콜백이 불린다. chat.js / board.js 가 자기 렌더 함수를 등록한다. */

const THEME_KEY = 'work_theme';
const NICK_KEY = 'work_nickname';

const themeSubs = [];
const navSubs = [];

const NAVS = ['docs', 'board', 'schedule'];

let nav = 'docs';   // 'docs'(채팅) | 'board'(게시판) | 'schedule'(일정)
let myIp = null;

/* ---------------- 내 IP (내가 쓴 글 강조용) ---------------- */

export function getMyIp() {
    return myIp;
}

export function setMyIp(ip) {
    if (ip) myIp = ip;
}

export function isMine(ip) {
    return Boolean(myIp && ip === myIp);
}

/* ---------------- 닉네임 ---------------- */

export function getNickname() {
    return localStorage.getItem(NICK_KEY) || '';
}

export function setNickname(name) {
    localStorage.setItem(NICK_KEY, (name || '').trim());
}

/* ---------------- 테마 ---------------- */

export function currentTheme() {
    return localStorage.getItem(THEME_KEY) === 'vscode' ? 'vscode' : 'groupware';
}

export function isVscode() {
    return currentTheme() === 'vscode';
}

export function onThemeChange(cb) {
    themeSubs.push(cb);
}

export function notifyThemeChange() {
    themeSubs.forEach((cb) => cb(currentTheme()));
}

export function storeTheme(name) {
    localStorage.setItem(THEME_KEY, name === 'vscode' ? 'vscode' : 'groupware');
}

/* ---------------- 내비 (채팅 / 게시판) ---------------- */

export function currentNav() {
    return nav;
}

export function onNavChange(cb) {
    navSubs.push(cb);
}

export function setNav(which) {
    nav = NAVS.includes(which) ? which : 'docs';
    navSubs.forEach((cb) => cb(nav));
}
