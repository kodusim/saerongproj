/* 좌(채팅) / 우(스칼라) 패널 너비 드래그 조절.
   폭은 localStorage 에 남겨서 다음 방문에도 유지한다. */
import { $ } from '../lib/dom.js';

const WIDTH_KEY = 'work_chat_pct';
const MIN_PCT = 32;
const MAX_PCT = 80;

let wrap;
let chatPane;
let scholarPane;
let handle;
let resizing = false;

function apply(pct) {
    chatPane.style.flex = `0 0 ${pct}%`;
    chatPane.style.maxWidth = `${pct}%`;
    scholarPane.style.flex = `0 0 ${100 - pct}%`;
    scholarPane.style.maxWidth = `${100 - pct}%`;
}

function clamp(pct) {
    return Math.min(MAX_PCT, Math.max(MIN_PCT, pct));
}

export function initResize() {
    wrap = document.querySelector('.work-wrap');
    chatPane = $('chat-pane');
    scholarPane = $('scholar-pane');
    handle = $('resize-handle');

    const saved = parseFloat(localStorage.getItem(WIDTH_KEY));
    if (!Number.isNaN(saved)) apply(clamp(saved));

    handle.addEventListener('mousedown', () => {
        resizing = true;
        handle.classList.add('dragging');
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!resizing) return;
        const rect = wrap.getBoundingClientRect();
        apply(clamp(((e.clientX - rect.left) / rect.width) * 100));
    });

    document.addEventListener('mouseup', () => {
        if (!resizing) return;
        resizing = false;
        handle.classList.remove('dragging');
        document.body.style.userSelect = '';
        localStorage.setItem(WIDTH_KEY, parseFloat(chatPane.style.maxWidth) || '');
    });
}
