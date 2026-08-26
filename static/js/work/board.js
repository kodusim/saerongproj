/* 게시판 — 누구나 읽고 쓰고 고치고 지운다 (로그인 없음, 작성자는 IP 로만 구분).

   자료실과 공지사항이 이 파일 하나를 인스턴스 두 개로 돌린다. 글의 생김새가
   같아서 서버도 같은 테이블(`work_workpost`)을 `board` 값으로만 가른다.

   테마별 DOM 이 두 벌(그룹웨어 표 / VS Code 마크다운 목록) 있고 상태는 한 벌이다.
   두 벌에 같은 내용을 렌더링하므로 테마를 바꿔도 화면 상태가 유지된다. */
import { $, escapeHtml, formatDateTime, linkify } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { getNickname, isMine, isVscode, onThemeChange, setMyIp } from './state.js';

/** 접두사로 DOM id 한 벌을 만든다 — 두 게시판이 같은 이름 규칙을 쓴다. */
function idsFor(prefix) {
    return {
        listPanel: `${prefix}-list-panel`,
        editPanel: `${prefix}-edit-panel`,
        viewPanel: `${prefix}-view-panel`,
        rows: `${prefix}-rows`,
        filterCat: `${prefix}-filter-cat`,
        search: `${prefix}-search`,
        refresh: `${prefix}-refresh`,
        newBtn: `${prefix}-new`,
        editCat: `${prefix}-edit-cat`,
        editTitle: `${prefix}-edit-title`,
        editAuthor: `${prefix}-edit-author`,
        editBody: `${prefix}-edit-body`,
        editCancel: `${prefix}-edit-cancel`,
        editSave: `${prefix}-edit-save`,
        vCat: `${prefix}-v-cat`,
        vTitle: `${prefix}-v-title`,
        vMeta: `${prefix}-v-meta`,
        vBody: `${prefix}-v-body`,
        vBack: `${prefix}-v-back`,
        vEdit: `${prefix}-v-edit`,
        vDelete: `${prefix}-v-delete`,
    };
}

/**
 * @param {object} cfg
 * @param {string} cfg.board        서버의 board 값 ('archive' | 'notice')
 * @param {string} cfg.gwPrefix     그룹웨어 DOM id 접두사 (예: 'bd')
 * @param {string} cfg.vcPrefix     VS Code DOM id 접두사 (예: 'vc-bd')
 * @param {string} cfg.countId      제목 옆 (n) 요소 id
 * @param {string} cfg.colPrefix    그룹웨어 열 클래스 접두사 (예: 'col-bd')
 * @param {string} cfg.defaultCat   새 글 기본 분류
 */
export function createBoard(cfg) {
    const UI = {
        groupware: idsFor(cfg.gwPrefix),
        vscode: idsFor(cfg.vcPrefix),
    };
    const skins = () => Object.values(UI);
    const activeUI = () => (isVscode() ? UI.vscode : UI.groupware);
    const C = cfg.colPrefix;

    let posts = [];
    let panel = 'list';      // 'list' | 'edit' | 'view'
    let editingId = null;
    let current = null;

    function showPanel(which) {
        panel = which;
        skins().forEach((ui) => {
            $(ui.listPanel).hidden = which !== 'list';
            $(ui.editPanel).hidden = which !== 'edit';
            $(ui.viewPanel).hidden = which !== 'view';
        });
    }

    /* ---------------- 목록 ---------------- */

    async function loadPosts() {
        const ui = activeUI();
        const params = new URLSearchParams({ board: cfg.board });
        const catEl = $(ui.filterCat);
        const cat = catEl ? catEl.value : '';
        const q = $(ui.search).value.trim();
        if (cat) params.set('category', cat);
        if (q) params.set('q', q);

        const { ok, data } = await api.get(`/work/api/posts/?${params}`);
        if (!ok || !data) return;
        setMyIp(data.my_ip);
        posts = data.posts || [];
        renderPosts();
    }

    function renderPosts() {
        $(cfg.countId).textContent = `(${posts.length})`;

        // 그룹웨어 스킨 — 문서함 표와 같은 행
        $(UI.groupware.rows).innerHTML = !posts.length
            ? '<div class="gw-empty">등록된 글이 없습니다.</div>'
            : posts.map((p) => `
                <div class="gw-row${isMine(p.author_ip) ? ' mine' : ''}">
                    <span class="${C}-no">${p.id}</span>
                    <span class="${C}-cat">${escapeHtml(p.category_label)}</span>
                    <span class="${C}-title" data-id="${p.id}" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</span>
                    <span class="${C}-author" title="${escapeHtml(p.author_name)}">${escapeHtml(p.author_name)}</span>
                    <span class="${C}-views">${p.views}</span>
                    <span class="${C}-date">${formatDateTime(p.created_at)}</span>
                </div>
            `).join('');

        // VS Code 스킨 — 마크다운 목록처럼 (두 게시판이 같은 스킨 클래스를 쓴다)
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
            const catEl = $(ui.vCat);
            if (catEl) catEl.textContent = p.category_label;
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
            const catEl = $(ui.editCat);
            if (catEl) catEl.value = values.category;
            $(ui.editTitle).value = values.title;
            $(ui.editAuthor).value = values.author_name;
            $(ui.editBody).value = values.body;
        });
    }

    function startNew() {
        editingId = null;
        fillEditor({
            category: cfg.defaultCat, title: '',
            author_name: getNickname(), body: '',
        });
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

        const catEl = $(ui.editCat);
        const url = editingId ? `/work/api/posts/${editingId}/` : '/work/api/posts/create/';
        const { ok, data } = await api.postJSON(url, {
            board: cfg.board,
            category: catEl ? catEl.value : cfg.defaultCat,
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

    function init() {
        $(UI.groupware.rows).addEventListener('click', (e) => {
            const t = e.target.closest(`.${C}-title`);
            if (t) openPost(t.dataset.id);
        });
        $(UI.vscode.rows).addEventListener('click', (e) => {
            const t = e.target.closest('.vc-bd-line');
            if (t) openPost(t.dataset.id);
        });

        skins().forEach((ui) => {
            // 필터/검색은 양쪽 테마에서 값이 같도록 동기화한다
            const catEl = $(ui.filterCat);
            if (catEl) {
                catEl.addEventListener('change', () => {
                    const v = catEl.value;
                    skins().forEach((o) => {
                        const el = $(o.filterCat);
                        if (el) el.value = v;
                    });
                    loadPosts();
                });
            }
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

        onThemeChange(() => {
            renderPosts();
            showPanel(panel);
        });

        showPanel('list');
    }

    return { init, load: loadPosts, render: renderPosts, showPanel };
}

/* 자료실 — 소설·수필 등 긴 글 */
export const archiveBoard = createBoard({
    board: 'archive',
    gwPrefix: 'bd', vcPrefix: 'vc-bd',
    countId: 'bd-count-title',
    colPrefix: 'col-bd',
    defaultCat: 'novel',
});

/* 공지사항 — 결재 탭 */
export const noticeBoard = createBoard({
    board: 'notice',
    gwPrefix: 'nt', vcPrefix: 'vc-nt',
    countId: 'nt-count-title',
    colPrefix: 'col-nt',
    defaultCat: 'notice',
});
