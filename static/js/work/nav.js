/* 채팅(문서함 / worklog.txt) ↔ 게시판(자료실 / posts.md) 전환.

   양쪽 테마의 DOM 을 동시에 토글한다 — 테마를 바꿔도 어느 화면을 보고 있었는지가
   유지되도록. */
import { $ } from '../lib/dom.js';
import { currentNav, onNavChange, onThemeChange, setNav } from './state.js';
import { loadPosts } from './board.js';

function applyNav(nav) {
    const board = nav === 'board';

    // 그룹웨어 테마
    $('gw-main-docs').hidden = board;
    $('gw-main-board').hidden = !board;
    $('gw-compose').hidden = board;
    $('gw-pagination').hidden = board;
    $('nav-tab-docs').classList.toggle('active', !board);
    $('nav-tab-board').classList.toggle('active', board);

    // VS Code 테마
    $('vc-chat-section').hidden = board;
    $('vc-board-section').hidden = !board;
    $('vc-tab-worklog').classList.toggle('active', !board);
    $('vc-tab-posts').classList.toggle('active', board);
    $('vc-tree-worklog').classList.toggle('selected', !board);
    $('vc-tree-posts').classList.toggle('selected', board);

    if (board) loadPosts();
}

export function initNav() {
    ['nav-tab-docs', 'vc-tab-worklog', 'vc-tree-worklog'].forEach((id) =>
        $(id).addEventListener('click', () => setNav('docs')));
    ['nav-tab-board', 'vc-tab-posts', 'vc-tree-posts'].forEach((id) =>
        $(id).addEventListener('click', () => setNav('board')));

    onNavChange(applyNav);
    onThemeChange(() => applyNav(currentNav()));
}
