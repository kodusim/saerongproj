/* 화면 전환 — 채팅 · 게시판(자료실) · 일정(설비예약) · 공지사항(결재).

   양쪽 테마의 DOM 을 동시에 토글한다 — 테마를 바꿔도 어느 화면을 보고 있었는지가
   유지되도록. */
import { $ } from '../lib/dom.js';
import { currentNav, onNavChange, onThemeChange, setNav, setValidNavs } from './state.js';
import { archiveBoard, noticeBoard } from './board.js';
import { loadSchedules } from './schedule.js';

// nav 값 → [그룹웨어 본문, VS Code 섹션, 그룹웨어 탭, VS Code 탭, VS Code 트리]
const TARGETS = {
    docs: ['gw-main-docs', 'vc-chat-section', 'nav-tab-docs', 'vc-tab-worklog', 'vc-tree-worklog'],
    board: ['gw-main-board', 'vc-board-section', 'nav-tab-board', 'vc-tab-posts', 'vc-tree-posts'],
    schedule: ['gw-main-schedule', 'vc-schedule-section', 'nav-tab-schedule', 'vc-tab-schedule', 'vc-tree-schedule'],
    notice: ['gw-main-notice', 'vc-notice-section', 'nav-tab-notice', 'vc-tab-notice', 'vc-tree-notice'],
};

// 화면에 들어갈 때 새로 불러올 것
const ON_ENTER = {
    board: () => archiveBoard.load(),
    notice: () => noticeBoard.load(),
    schedule: () => loadSchedules(),
};

function applyNav(nav) {
    Object.entries(TARGETS).forEach(([key, [gwMain, vcSection, gwTab, vcTab, vcTree]]) => {
        const on = key === nav;
        $(gwMain).hidden = !on;
        $(vcSection).hidden = !on;
        $(gwTab).classList.toggle('active', on);
        $(vcTab).classList.toggle('active', on);
        $(vcTree).classList.toggle('selected', on);
    });

    // 채팅 입력줄과 페이지네이션은 문서함에서만 의미가 있다
    const isDocs = nav === 'docs';
    $('gw-compose').hidden = !isDocs;
    $('gw-pagination').hidden = !isDocs;

    const enter = ON_ENTER[nav];
    if (enter) enter();
}

export function initNav() {
    setValidNavs(Object.keys(TARGETS));

    Object.entries(TARGETS).forEach(([key, [, , gwTab, vcTab, vcTree]]) => {
        [gwTab, vcTab, vcTree].forEach((id) =>
            $(id).addEventListener('click', () => setNav(key)));
    });

    onNavChange(applyNav);
    onThemeChange(() => applyNav(currentNav()));
}
