/* /work 엔트리.

   초기화 순서가 중요하다: 테마 변경 구독자(chat/board/nav)를 모두 등록한 뒤
   마지막에 initTheme() 이 첫 렌더를 트리거한다. */
import { initLightbox } from './lightbox.js';
import { initResize } from './resize.js';
import { initUnread } from './unread.js';
import { initScholar } from './scholar.js';
import { initBoard, showPanel } from './board.js';
import { initChat } from './chat.js';
import { initNav } from './nav.js';
import { initTheme } from './theme.js';

initLightbox();
initResize();
initUnread();
initScholar();

initBoard();
showPanel('list');
initNav();

// 첫 렌더 — 구독자가 모두 등록된 뒤에 실행한다
initTheme();

// 채팅은 네트워크를 타므로 마지막에 (내부에서 렌더를 다시 호출한다)
initChat();
