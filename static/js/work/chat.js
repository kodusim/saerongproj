/* 채팅 — 그룹웨어에서는 "기록물등록대장" 표, VS Code 에서는 worklog.txt 로 보인다.

   수신은 WebSocket(/work/ws). 끊기면 2초 폴링으로 자동 강등되고, 재연결되면
   놓친 구간을 HTTP 로 따라잡는다.
   전송은 HTTP POST /work/api/send/ 로 남겼다 — 이미지 multipart 때문. 서버가
   저장 후 모든 클라이언트에게 브로드캐스트한다. */
import { $, escapeHtml, formatDateTime } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { getNickname, isMine, onThemeChange, setMyIp, setNickname, isVscode } from './state.js';
import { bindImageIcons } from './lightbox.js';
import { addUnread } from './unread.js';
import { initColumnResize } from './columns.js';

const POLL_MS = 2000;
const RECONNECT_MIN_MS = 1000;
const RECONNECT_MAX_MS = 15000;
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

let messages = [];
let lastId = 0;

let rowsEl;      // 그룹웨어 표 본문
let linesEl;     // VS Code 에디터 본문
let countEl;

let socket = null;
let pollTimer = null;
let reconnectDelay = RECONNECT_MIN_MS;
let firstLoad = true;   // 최초 로드분은 '안 읽음' 으로 세지 않는다

function socketReady() {
    return Boolean(socket) && socket.readyState === WebSocket.OPEN;
}

/* ---------------- 렌더 ---------------- */

function renderGroupware() {
    countEl.textContent = `(${messages.length})`;

    if (!messages.length) {
        rowsEl.innerHTML = '<div class="gw-empty">아직 등록된 메시지가 없습니다.</div>';
        return;
    }

    const atTop = rowsEl.scrollTop < 40;

    // 문서번호는 작성자와 무관하게 하단(가장 오래된 글)부터 1번으로 순차 부여한다.
    // messages 는 시간순 오름차순이므로 배열 인덱스가 곧 문서번호다.
    // 표시는 최신이 위 — 실제 기록물등록대장과 같은 정렬이라 뒤집어 그린다.
    rowsEl.innerHTML = messages.map((m, i) => {
        const titleText = m.body ? escapeHtml(m.body) : '[이미지 첨부]';
        const imgIcon = m.image_url
            ? `<span class="row-img-icon" data-url="${escapeHtml(m.image_url)}">🖼</span>`
            : '';
        const dateText = formatDateTime(m.created_at);
        const docNo = `사업기록-${String(i + 1).padStart(5, '0')}`;
        const author = escapeHtml(m.sender_name);
        return `
            <div class="gw-row${isMine(m.sender_ip) ? ' mine' : ''}">
                <span class="col-chk"><input type="checkbox" disabled></span>
                <span class="col-status">${m.image_url ? '🖼' : '📄'}</span>
                <span class="col-type">등록</span>
                <span class="col-no" title="${docNo}">${docNo}</span>
                <span class="col-attach">${m.image_url ? 1 : 0}</span>
                <span class="col-title" title="${titleText}">${titleText}${imgIcon}</span>
                <span class="col-author" title="${author}">${author}</span>
                <span class="col-datetime" title="${dateText}">${dateText}</span>
            </div>
        `;
    }).reverse().join('');

    if (atTop) rowsEl.scrollTop = 0;
}

function renderVscode() {
    if (!messages.length) {
        linesEl.innerHTML = '<div class="vc-empty">// 아직 기록된 로그가 없습니다</div>';
        return;
    }

    const atBottom = linesEl.scrollHeight - linesEl.scrollTop - linesEl.clientHeight < 60;

    const header = `
        <div class="vc-line vc-header-line">
            <span class="vc-lineno">1</span>
            <span class="vc-code"><span class="vc-comment">// worklog.txt — ${messages.length}개 항목</span></span>
        </div>
    `;

    const lines = messages.map((m, i) => {
        const nickTag = `<span class="vc-comment">// [${escapeHtml(m.sender_name)}]</span>`;
        const bodyPart = m.body ? ` <span class="vc-str">"${escapeHtml(m.body)}"</span>` : '';
        const imgPart = m.image_url
            ? ` <span class="vc-fn row-img-icon" data-url="${escapeHtml(m.image_url)}">openImage()</span>`
            : '';
        return `
            <div class="vc-line${isMine(m.sender_ip) ? ' mine' : ''}">
                <span class="vc-lineno">${i + 2}</span>
                <span class="vc-code">${nickTag}${bodyPart}${imgPart}</span>
                <span class="vc-time">${formatDateTime(m.created_at)}</span>
            </div>
        `;
    }).join('');

    linesEl.innerHTML = header + lines;

    if (atBottom) linesEl.scrollTop = linesEl.scrollHeight;
}

export function renderMessages() {
    if (isVscode()) renderVscode();
    else renderGroupware();
}

/* ---------------- 수신 ---------------- */

function ingest(incoming) {
    const fresh = (incoming || []).filter((m) => m.id > lastId);
    if (!fresh.length) return;

    messages = messages.concat(fresh);
    fresh.forEach((m) => { lastId = Math.max(lastId, m.id); });

    if (!firstLoad) addUnread(fresh.length);
    renderMessages();
}

/** 놓친 구간을 HTTP 로 따라잡는다 (최초 로드 · 재연결 · 폴링 공용). */
export async function catchUp() {
    const { ok, data } = await api.get(`/work/api/messages/?after=${lastId}`);
    if (!ok || !data) return;
    setMyIp(data.my_ip);
    ingest(data.messages);
}

function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(catchUp, POLL_MS);
}

function stopPolling() {
    if (!pollTimer) return;
    clearInterval(pollTimer);
    pollTimer = null;
}

function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ws;
    try {
        ws = new WebSocket(`${proto}//${location.host}/work/ws`);
    } catch {
        startPolling();
        return;
    }
    socket = ws;

    ws.addEventListener('open', () => {
        reconnectDelay = RECONNECT_MIN_MS;
        stopPolling();
        // 연결이 끊겼던 사이에 온 메시지를 따라잡는다
        catchUp();
    });

    ws.addEventListener('message', (ev) => {
        let payload;
        try {
            payload = JSON.parse(ev.data);
        } catch {
            return;
        }
        if (payload.type === 'hello') setMyIp(payload.my_ip);
        else if (payload.type === 'messages') ingest(payload.messages);
    });

    ws.addEventListener('close', () => {
        socket = null;
        // WebSocket 이 막힌 환경일 수 있으니 폴링으로 버티면서 재연결을 시도한다
        startPolling();
        setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
    });

    ws.addEventListener('error', () => {
        // close 가 뒤따라 오므로 여기서는 폴링만 켜 둔다
        startPolling();
    });
}

/* ---------------- 입력줄 (테마별로 2벌, 서버 로직은 공유) ---------------- */

function setupCompose(ids) {
    const nickname = $(ids.nickname);
    const chatBody = $(ids.chatBody);
    const attachBtn = $(ids.attachBtn);
    const attachFile = $(ids.attachFile);
    const pendingBox = $(ids.pendingBox);
    const pendingName = $(ids.pendingName);
    const pendingRemove = $(ids.pendingRemove);
    const sendBtn = $(ids.sendBtn);

    let pendingFile = null;

    nickname.classList.add('nickname-input');
    nickname.value = getNickname();
    nickname.addEventListener('change', () => setNickname(nickname.value));

    attachBtn.addEventListener('click', () => attachFile.click());

    attachFile.addEventListener('change', () => {
        const f = attachFile.files[0];
        if (!f) return;
        if (!f.type.startsWith('image/')) {
            alert('이미지 파일만 첨부할 수 있습니다.');
            attachFile.value = '';
            return;
        }
        if (f.size > MAX_IMAGE_BYTES) {
            alert('이미지는 8MB 이하만 첨부할 수 있습니다.');
            attachFile.value = '';
            return;
        }
        pendingFile = f;
        pendingName.textContent = `🖼 ${f.name}`;
        pendingBox.hidden = false;
    });

    function clearAttachment() {
        pendingFile = null;
        attachFile.value = '';
        pendingBox.hidden = true;
    }

    pendingRemove.addEventListener('click', clearAttachment);

    chatBody.addEventListener('input', () => {
        chatBody.style.height = 'auto';
        chatBody.style.height = `${Math.min(chatBody.scrollHeight, 90)}px`;
    });

    chatBody.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    });

    async function send() {
        const body = chatBody.value.trim();
        if (!body && !pendingFile) return;

        const fd = new FormData();
        fd.append('sender_name', nickname.value.trim() || '익명');
        fd.append('body', body);
        if (pendingFile) fd.append('image', pendingFile);

        // 낙관적으로 입력창을 비운다 — 실패하면 alert 로 알린다
        chatBody.value = '';
        chatBody.style.height = 'auto';
        clearAttachment();

        const { ok, data } = await api.postForm('/work/api/send/', fd);
        if (!ok) {
            alert((data && data.error) || '전송에 실패했습니다.');
            return;
        }
        // 보통은 WebSocket 브로드캐스트로 돌아온다. 소켓이 열려 있지 않으면
        // 브로드캐스트를 받을 수 없으니 직접 당겨온다.
        if (!socketReady()) await catchUp();
    }

    sendBtn.addEventListener('click', send);
}

/* ---------------- 초기화 ---------------- */

export async function initChat() {
    rowsEl = $('chat-messages');
    linesEl = $('vc-lines');
    countEl = $('doc-count-title');

    bindImageIcons(rowsEl);
    bindImageIcons(linesEl);

    const head = $('chat-table-head');
    initColumnResize({
        wrap: head.closest('.gw-table-wrap'),
        head,
        storageKey: 'work_cols_chat',
        cols: [
            { cls: 'col-status', varName: '--w-status' },
            { cls: 'col-type', varName: '--w-type' },
            { cls: 'col-no', varName: '--w-no' },
            { cls: 'col-attach', varName: '--w-attach' },
            { cls: 'col-title', varName: '--w-title', group: 'title' },
            { cls: 'col-author', varName: '--w-author', group: 'author' },
            { cls: 'col-datetime', varName: '--w-datetime', group: 'date' },
        ],
    });

    $('doc-refresh').addEventListener('click', catchUp);
    $('vc-refresh').addEventListener('click', catchUp);

    setupCompose({
        nickname: 'nickname', chatBody: 'chat-body',
        attachBtn: 'attach-btn', attachFile: 'attach-file',
        pendingBox: 'pending-attachment', pendingName: 'pending-attachment-name',
        pendingRemove: 'pending-attachment-remove', sendBtn: 'chat-send',
    });
    setupCompose({
        nickname: 'nickname-vc', chatBody: 'chat-body-vc',
        attachBtn: 'attach-btn-vc', attachFile: 'attach-file-vc',
        pendingBox: 'pending-attachment-vc', pendingName: 'pending-attachment-name-vc',
        pendingRemove: 'pending-attachment-remove-vc', sendBtn: 'chat-send-vc',
    });

    onThemeChange(renderMessages);

    await catchUp();
    firstLoad = false;
    renderMessages();   // 메시지가 0건이어도 빈 상태를 현재 테마로 그려둔다
    connect();
}
