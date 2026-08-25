/* 만남 일정 — 그룹웨어에서는 '설비예약' 탭, VS Code 에서는 schedule.md.

   게시판과 같은 구조: 상태는 한 벌, 테마별 DOM 두 벌에 같은 내용을 렌더링한다.
   목록 → 행 클릭 → 편집(등록/수정/삭제) 두 단계뿐이라 보기 패널은 두지 않았다. */
import { $, escapeHtml } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { getNickname, isMine, isVscode, onThemeChange, setMyIp } from './state.js';
import { initColumnResize } from './columns.js';

const UI = {
    groupware: {
        listPanel: 'sc-list-panel', editPanel: 'sc-edit-panel',
        rows: 'sc-rows', search: 'sc-search',
        refresh: 'sc-refresh', newBtn: 'sc-new',
        date: 'sc-edit-date', time: 'sc-edit-time', title: 'sc-edit-title',
        place: 'sc-edit-place', att: 'sc-edit-att', author: 'sc-edit-author',
        memo: 'sc-edit-memo',
        cancel: 'sc-edit-cancel', save: 'sc-edit-save', del: 'sc-edit-delete',
    },
    vscode: {
        listPanel: 'vc-sc-list-panel', editPanel: 'vc-sc-edit-panel',
        rows: 'vc-sc-rows', search: 'vc-sc-search',
        refresh: 'vc-sc-refresh', newBtn: 'vc-sc-new',
        date: 'vc-sc-edit-date', time: 'vc-sc-edit-time', title: 'vc-sc-edit-title',
        place: 'vc-sc-edit-place', att: 'vc-sc-edit-att', author: 'vc-sc-edit-author',
        memo: 'vc-sc-edit-memo',
        cancel: 'vc-sc-edit-cancel', save: 'vc-sc-edit-save', del: 'vc-sc-edit-delete',
    },
};

let items = [];
let panel = 'list';     // 'list' | 'edit'
let editingId = null;
let query = '';

const skins = () => Object.values(UI);
const activeUI = () => (isVscode() ? UI.vscode : UI.groupware);

/** 오늘(로컬) 자정 — 지난 일정을 흐리게 표시하는 기준 */
function todayStr() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function matches(s) {
    if (!query) return true;
    const q = query.toLowerCase();
    return [s.title, s.place, s.attendees, s.author_name]
        .some((v) => (v || '').toLowerCase().includes(q));
}

function visible() {
    return items.filter(matches);
}

/* ---------------- 패널 ---------------- */

export function showPanel(which) {
    panel = which;
    skins().forEach((ui) => {
        $(ui.listPanel).hidden = which !== 'list';
        $(ui.editPanel).hidden = which !== 'edit';
    });
}

/* ---------------- 목록 ---------------- */

export async function loadSchedules() {
    const { ok, data } = await api.get('/work/api/schedules/');
    if (!ok || !data) return;
    setMyIp(data.my_ip);
    items = data.schedules || [];
    renderSchedules();
}

export function renderSchedules() {
    const rows = visible();
    const today = todayStr();
    $('sc-count-title').textContent = `(${rows.length})`;

    $(UI.groupware.rows).innerHTML = !rows.length
        ? '<div class="gw-empty">등록된 일정이 없습니다.</div>'
        : rows.map((s) => `
            <div class="gw-row${isMine(s.author_ip) ? ' mine' : ''}${s.meet_date < today ? ' past' : ''}">
                <span class="col-sc-date">${escapeHtml(s.meet_date)}</span>
                <span class="col-sc-time">${escapeHtml(s.meet_time || '-')}</span>
                <span class="col-sc-title" data-id="${s.id}" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</span>
                <span class="col-sc-place" title="${escapeHtml(s.place)}">${escapeHtml(s.place || '-')}</span>
                <span class="col-sc-att" title="${escapeHtml(s.attendees)}">${escapeHtml(s.attendees || '-')}</span>
                <span class="col-sc-author" title="${escapeHtml(s.author_name)}">${escapeHtml(s.author_name)}</span>
            </div>
        `).join('');

    $(UI.vscode.rows).innerHTML = !rows.length
        ? '<div class="vc-empty">// 등록된 일정이 없습니다</div>'
        : rows.map((s) => `
            <div class="vc-sc-line${isMine(s.author_ip) ? ' mine' : ''}${s.meet_date < today ? ' past' : ''}" data-id="${s.id}">
                <span class="vc-sc-key">-</span>
                <span class="vc-sc-date">${escapeHtml(s.meet_date)}${s.meet_time ? ` ${escapeHtml(s.meet_time)}` : ''}</span>
                <span class="vc-sc-name" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</span>
                <span class="vc-sc-meta">${escapeHtml(s.place || '장소 미정')} · @${escapeHtml(s.author_name)}</span>
            </div>
        `).join('');
}

/* ---------------- 편집 ---------------- */

function fill(values) {
    skins().forEach((ui) => {
        $(ui.date).value = values.meet_date;
        $(ui.time).value = values.meet_time;
        $(ui.title).value = values.title;
        $(ui.place).value = values.place;
        $(ui.att).value = values.attendees;
        $(ui.author).value = values.author_name;
        $(ui.memo).value = values.memo;
        $(ui.del).hidden = !values.canDelete;
    });
}

function startNew() {
    editingId = null;
    fill({
        meet_date: todayStr(), meet_time: '', title: '',
        place: '', attendees: '', author_name: getNickname(), memo: '',
        canDelete: false,
    });
    showPanel('edit');
    $(activeUI().title).focus();
}

function startEdit(id) {
    const s = items.find((x) => String(x.id) === String(id));
    if (!s) return;
    editingId = s.id;
    fill({
        meet_date: s.meet_date, meet_time: s.meet_time, title: s.title,
        place: s.place, attendees: s.attendees, author_name: s.author_name,
        memo: s.memo || '',
        canDelete: true,
    });
    showPanel('edit');
}

async function save() {
    const ui = activeUI();
    const title = $(ui.title).value.trim();
    if (!title) {
        alert('일정 제목을 입력하세요.');
        return;
    }
    const meetDate = $(ui.date).value;
    if (!meetDate) {
        alert('날짜를 선택하세요.');
        return;
    }

    const url = editingId
        ? `/work/api/schedules/${editingId}/`
        : '/work/api/schedules/create/';
    const { ok, data } = await api.postJSON(url, {
        title,
        meet_date: meetDate,
        meet_time: $(ui.time).value,
        place: $(ui.place).value.trim(),
        attendees: $(ui.att).value.trim(),
        author_name: $(ui.author).value.trim() || '익명',
        memo: $(ui.memo).value,
    });

    if (!ok) {
        alert((data && data.error) || '저장에 실패했습니다.');
        return;
    }
    await loadSchedules();
    showPanel('list');
}

async function remove() {
    if (!editingId) return;
    const s = items.find((x) => x.id === editingId);
    if (!confirm(`"${s ? s.title : '이 일정'}" 을 삭제할까요? 되돌릴 수 없습니다.`)) return;

    const { ok } = await api.del(`/work/api/schedules/${editingId}/`);
    if (!ok) {
        alert('삭제에 실패했습니다.');
        return;
    }
    editingId = null;
    await loadSchedules();
    showPanel('list');
}

/* ---------------- 초기화 ---------------- */

export function initSchedule() {
    $(UI.groupware.rows).addEventListener('click', (e) => {
        const t = e.target.closest('.col-sc-title');
        if (t) startEdit(t.dataset.id);
    });
    $(UI.vscode.rows).addEventListener('click', (e) => {
        const t = e.target.closest('.vc-sc-line');
        if (t) startEdit(t.dataset.id);
    });

    skins().forEach((ui) => {
        $(ui.search).addEventListener('input', () => {
            query = $(ui.search).value.trim();
            skins().forEach((o) => { $(o.search).value = query; });
            renderSchedules();
        });
        $(ui.refresh).addEventListener('click', loadSchedules);
        $(ui.newBtn).addEventListener('click', startNew);
        $(ui.cancel).addEventListener('click', () => showPanel('list'));
        $(ui.save).addEventListener('click', save);
        $(ui.del).addEventListener('click', remove);
    });

    const head = $('sc-table-head');
    initColumnResize({
        wrap: head.closest('.gw-table-wrap'),
        head,
        storageKey: 'work_cols_schedule',
        cols: [
            { cls: 'col-sc-date', varName: '--w-sc-date' },
            { cls: 'col-sc-time', varName: '--w-sc-time' },
            { cls: 'col-sc-title', varName: '--w-sc-title' },
            { cls: 'col-sc-place', varName: '--w-sc-place' },
            { cls: 'col-sc-att', varName: '--w-sc-att' },
            { cls: 'col-sc-author', varName: '--w-sc-author' },
        ],
    });

    onThemeChange(() => {
        renderSchedules();
        showPanel(panel);
    });
}
