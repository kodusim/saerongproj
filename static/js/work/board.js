/* 게시판 — 누구나 읽고 쓰고 고치고 지운다 (로그인 없음, 작성자는 IP 로만 구분).

   테마별 DOM 이 두 벌(그룹웨어 표 / VS Code 마크다운 목록) 있고, 상태는 한 벌이다.
   두 벌에 같은 내용을 렌더링하므로 테마를 바꿔도 화면 상태가 유지된다. */
import { $, escapeHtml, formatDateTime, linkify } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { getNickname, isMine, isVscode, onThemeChange, setMyIp } from './state.js';
import { initColumnResize } from './columns.js';

const UI = {
    groupware: {
        listPanel: 'bd-list-panel', editPanel: 'bd-edit-panel', viewPanel: 'bd-view-panel',
        rows: 'bd-rows', filterCat: 'bd-filter-cat', search: 'bd-search',
        refresh: 'bd-refresh', newBtn: 'bd-new',
        editCat: 'bd-edit-cat', editTitle: 'bd-edit-title', editAuthor: 'bd-edit-author',
        editBody: 'bd-edit-body', editCancel: 'bd-edit-cancel', editSave: 'bd-edit-save',
        vTitle: 'bd-v-title', vMeta: 'bd-v-meta', vBody: 'bd-v-body',
        vBack: 'bd-v-back', vEdit: 'bd-v-edit', vDelete: 'bd-v-delete',
        vCat: 'bd-v-cat',
    },
    vscode: {
        listPanel: 'vc-bd-list-panel', editPanel: 'vc-bd-edit-panel', viewPanel: 'vc-bd-view-panel',
        rows: 'vc-bd-rows', filterCat: 'vc-bd-filter-cat', search: 'vc-bd-search',
        refresh: 'vc-bd-refresh', newBtn: 'vc-bd-new',
        editCat: 'vc-bd-edit-cat', editTitle: 'vc-bd-edit-title', editAuthor: 'vc-bd-edit-author',
        editBody: 'vc-bd-edit-body', editCancel: 'vc-bd-edit-cancel', editSave: 'vc-bd-edit-save',
        vTitle: 'vc-bd-v-title', vMeta: 'vc-bd-v-meta', vBody: 'vc-bd-v-body',
        vBack: 'vc-bd-v-back', vEdit: 'vc-bd-v-edit', vDelete: 'vc-bd-v-delete',
        vCat: null,
    },
};

let posts = [];
let panel = 'list';      // 'list' | 'edit' | 'view'
let editingId = null;
let current = null;

const skins = () => Object.values(UI);
const activeUI = () => (isVscode() ? UI.vscode : UI.groupware);

/* ---------------- 패널 전환 ---------------- */

export function showPanel(which) {
    panel = which;
    skins().forEach((ui) => {
        $(ui.listPanel).hidden = which !== 'list';
        $(ui.editPanel).hidden = which !== 'edit';
        $(ui.viewPanel).hidden = which !== 'view';
    });
}

export function currentPanel() {
    return panel;
}

/* ---------------- 목록 ---------------- */

export async function loadPosts() {
    const ui = activeUI();
    const params = new URLSearchParams();
    const cat = $(ui.filterCat).value;
    const q = $(ui.search).value.trim();
    if (cat) params.set('category', cat);
    if (q) params.set('q', q);

    const { ok, data } = await api.get(`/work/api/posts/?${params}`);
    if (!ok || !data) return;
    setMyIp(data.my_ip);
    posts = data.posts || [];
    renderPosts();
}

export function renderPosts() {
    $('bd-count-title').textContent = `(${posts.length})`;

    // 그룹웨어 스킨 — 문서함 표와 같은 행
    $(UI.groupware.rows).innerHTML = !posts.length
        ? '<div class="gw-empty">등록된 글이 없습니다.</div>'
        : posts.map((p) => `
            <div class="gw-row${isMine(p.author_ip) ? ' mine' : ''}">
                <span class="col-bd-no">${p.id}</span>
                <span class="col-bd-cat">${escapeHtml(p.category_label)}</span>
                <span class="col-bd-title" data-id="${p.id}" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</span>
                <span class="col-bd-author" title="${escapeHtml(p.author_name)}">${escapeHtml(p.author_name)}</span>
                <span class="col-bd-views">${p.views}</span>
                <span class="col-bd-date">${formatDateTime(p.created_at)}</span>
            </div>
        `).join('');

    // VS Code 스킨 — 마크다운 목록처럼
    $(UI.vscode.rows).innerHTML = !posts.length
        ? '<div class="vc-empty">// 등록된 글이 없습니다</div>'
        : posts.map((p) => `
            <div class="vc-bd-line${isMine(p.author_ip) ? ' mine' : ''}" data-id="${p.id}">
                <span class="vc-bd-hash">##</span>
                <span class="vc-bd-cat-tag">[${escapeHtml(p.category_label)}]</span>
                <span class="vc-bd-name" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</span>
                <span class="vc-bd-author-tag">@${escapeHtml(p.author_name)}</span>
                <span class="vc-bd-meta-tag">${formatDateTime(p.created_at)} · ${p.views}</span>
            </div>
        `).join('');
}

/* ---------------- 보기 ---------------- */

async function openPost(id) {
    const { ok, data: p } = await api.get(`/work/api/posts/${id}/`);
    if (!ok || !p) return;
    current = p;

    skins().forEach((ui) => {
        if (ui.vCat) $(ui.vCat).textContent = p.category_label;
        $(ui.vTitle).textContent = p.title;
        $(ui.vMeta).innerHTML =
            `<span>작성자 ${escapeHtml(p.author_name)}</span>`
            + `<span>${formatDateTime(p.created_at)}</span>`
            + `<span>조회 ${p.views}</span>`;
        // linkify 가 escape 까지 하므로 innerHTML 로 넣어도 안전하다
        $(ui.vBody).innerHTML = p.body ? linkify(p.body) : '(내용 없음)';
    });
    showPanel('view');
}

/* ---------------- 작성 / 수정 ---------------- */

function fillEditor(values) {
    skins().forEach((ui) => {
        $(ui.editCat).value = values.category;
        $(ui.editTitle).value = values.title;
        $(ui.editAuthor).value = values.author_name;
        $(ui.editBody).value = values.body;
    });
}

function startNew() {
    editingId = null;
    fillEditor({ category: 'novel', title: '', author_name: getNickname(), body: '' });
    showPanel('edit');
    $(activeUI().editTitle).focus();
}

function startEdit() {
    if (!current) return;
    editingId = current.id;
    fillEditor({
        category: current.category,
        title: current.title,
        author_name: current.author_name,
        body: current.body || '',
    });
    showPanel('edit');
}

async function savePost() {
    const ui = activeUI();
    const title = $(ui.editTitle).value.trim();
    if (!title) {
        alert('제목을 입력하세요.');
        return;
    }

    const url = editingId ? `/work/api/posts/${editingId}/` : '/work/api/posts/create/';
    const { ok, data } = await api.postJSON(url, {
        category: $(ui.editCat).value,
        title,
        author_name: $(ui.editAuthor).value.trim() || '익명',
        body: $(ui.editBody).value,
    });

    if (!ok) {
        alert((data && data.error) || '저장에 실패했습니다.');
        return;
    }
    await loadPosts();
    await openPost(data.id);
}

async function deletePost() {
    if (!current) return;
    if (!confirm(`"${current.title}" 글을 삭제할까요? 되돌릴 수 없습니다.`)) return;

    const { ok } = await api.del(`/work/api/posts/${current.id}/`);
    if (!ok) {
        alert('삭제에 실패했습니다.');
        return;
    }
    current = null;
    showPanel('list');
    loadPosts();
}

/* ---------------- 초기화 ---------------- */

export function initBoard() {
    $(UI.groupware.rows).addEventListener('click', (e) => {
        const t = e.target.closest('.col-bd-title');
        if (t) openPost(t.dataset.id);
    });
    $(UI.vscode.rows).addEventListener('click', (e) => {
        const t = e.target.closest('.vc-bd-line');
        if (t) openPost(t.dataset.id);
    });

    skins().forEach((ui) => {
        // 필터/검색은 양쪽 테마에서 값이 같도록 동기화한다
        $(ui.filterCat).addEventListener('change', () => {
            const v = $(ui.filterCat).value;
            skins().forEach((o) => { $(o.filterCat).value = v; });
            loadPosts();
        });
        $(ui.search).addEventListener('input', () => {
            const v = $(ui.search).value;
            skins().forEach((o) => { $(o.search).value = v; });
            loadPosts();
        });

        $(ui.refresh).addEventListener('click', loadPosts);
        $(ui.newBtn).addEventListener('click', startNew);
        $(ui.editCancel).addEventListener('click', () => showPanel(editingId ? 'view' : 'list'));
        $(ui.editSave).addEventListener('click', savePost);
        $(ui.vBack).addEventListener('click', () => { showPanel('list'); loadPosts(); });
        $(ui.vEdit).addEventListener('click', startEdit);
        $(ui.vDelete).addEventListener('click', deletePost);
    });

    const head = $('bd-table-head');
    initColumnResize({
        wrap: head.closest('.gw-table-wrap'),
        head,
        storageKey: 'work_cols_board',
        cols: [
            { cls: 'col-bd-no', varName: '--w-bd-no' },
            { cls: 'col-bd-cat', varName: '--w-bd-cat' },
            { cls: 'col-bd-title', varName: '--w-bd-title' },
            { cls: 'col-bd-author', varName: '--w-bd-author' },
            { cls: 'col-bd-views', varName: '--w-bd-views' },
            { cls: 'col-bd-date', varName: '--w-bd-date' },
        ],
    });

    onThemeChange(() => {
        renderPosts();
        showPanel(panel);
    });
}
