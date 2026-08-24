/* 테마 전환 (그룹웨어 ↔ VS Code).

   **외형만** 바꾼다 — 채팅/게시판의 내용과 화면 상태는 그대로 유지된다.
   두 테마의 DOM 이 모두 문서에 있고 한쪽만 보여주는 방식이며, 렌더는
   state.js 의 구독자(chat.js / board.js / nav.js)가 담당한다. */
import { currentTheme, getNickname, notifyThemeChange, storeTheme } from './state.js';

let switchers;

export function setTheme(name) {
    const isVs = name === 'vscode';
    document.getElementById('view-groupware').hidden = isVs;
    document.getElementById('view-vscode').hidden = !isVs;

    switchers.forEach((sel) => { sel.value = isVs ? 'vscode' : 'groupware'; });
    storeTheme(name);

    // 닉네임 입력칸은 테마별로 따로 있으므로 값을 맞춰준다
    document.querySelectorAll('.nickname-input').forEach((el) => {
        el.value = getNickname();
    });

    notifyThemeChange();
}

export function initTheme() {
    switchers = document.querySelectorAll('.theme-switcher');
    switchers.forEach((sel) => {
        sel.addEventListener('change', () => setTheme(sel.value));
    });
    setTheme(currentTheme());
}
