/* 만남 일정 — 월 달력. 그룹웨어 '설비예약' 탭 / VS Code 'schedule.md'.

   두 테마가 **같은 달력 마크업**을 쓰고 CSS 로만 스킨을 바꾼다 (달력은 구조가
   같아도 어색하지 않아서, 게시판처럼 마크업을 두 벌 만들지 않았다).
   상태는 한 벌이고 렌더만 두 컨테이너에 각각 한다. */
import { $, escapeHtml } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { getNickname, isMine, isVscode, onThemeChange, setMyIp } from './state.js';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const MAX_CHIPS = 3;        // 한 칸에 제목을 몇 개까지 보여줄지

const UI = {
    groupware: {
        calendar: 'sc-calendar', label: 'sc-month-label',
        prev: 'sc-prev', next: 'sc-next', today: 'sc-today', newBtn: 'sc-new',
        listPanel: 'sc-list-panel', editPanel: 'sc-edit-panel',
        date: 'sc-edit-date', time: 'sc-edit-time', title: 'sc-edit-title',
        place: 'sc-edit-place', att: 'sc-edit-att', author: 'sc-edit-author',
        memo: 'sc-edit-memo',
        cancel: 'sc-edit-cancel', save: 'sc-edit-save', del: 'sc-edit-delete',
    },
    vscode: {
        calendar: 'vc-sc-calendar', label: 'vc-sc-month-label',
        prev: 'vc-sc-prev', next: 'vc-sc-next', today: 'vc-sc-today', newBtn: 'vc-sc-new',
        listPanel: 'vc-sc-list-panel', editPanel: 'vc-sc-edit-panel',
        date: 'vc-sc-edit-date', time: 'vc-sc-edit-time', title: 'vc-sc-edit-title',
        place: 'vc-sc-edit-place', att: 'vc-sc-edit-att', author: 'vc-sc-edit-author',
        memo: 'vc-sc-edit-memo',
        cancel: 'vc-sc-edit-cancel', save: 'vc-sc-edit-save', del: 'vc-sc-edit-delete',
    },
};

const skins = () => Object.values(UI);
const activeUI = () => (isVscode() ? UI.vscode : UI.groupware);

let items = [];
let panel = 'list';     // 'list'(달력) | 'edit'
let editingId = null;
let viewYear;
let viewMonth;          // 0-11

/* ---------------- 날짜 헬퍼 ---------------- */

const pad = (n) => String(n).padStart(2, '0');
const ymd = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`;

function todayStr() {
    const d = new Date();
    return ymd(d.getFullYear(), d.getMonth(), d.getDate());
}

/** 그 달 일정만 날짜별로 묶는다 — { '2026-08-14': [일정, ...] } */
function byDate() {
    const map = new Map();
    items.forEach((s) => {
        if (!map.has(s.meet_date)) map.set(s.meet_date, []);
        map.get(s.meet_date).push(s);
    });
    // 같은 날은 시간순 (시간 없는 건 뒤로)
    map.forEach((list) => list.sort((a, b) =>
        (a.meet_time || '99:99').localeCompare(b.meet_time || '99:99')));
    return map;
}

/* ---------------- 달력 렌더 ---------------- */

function renderInto(el) {
    if (!el) return;

    const first = new Date(viewYear, viewMonth, 1);
    const startDow = first.getDay();                          // 1일의 요일
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const today = todayStr();
    const map = byDate();

    const head = WEEKDAYS.map((w, i) =>
        `<div class="sc-cal-dow${i === 0 ? ' sun' : ''}${i === 6 ? ' sat' : ''}">${w}</div>`
    ).join('');

    const cells = [];
    for (let i = 0; i < startDow; i += 1) {
        cells.push('<div class="sc-cal-cell empty"></div>');
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
        const key = ymd(viewYear, viewMonth, day);
        const dow = (startDow + day - 1) % 7;
        const list = map.get(key) || [];

        const chips = list.slice(0, MAX_CHIPS).map((s) => `
            <div class="sc-chip${isMine(s.author_ip) ? ' mine' : ''}" data-id="${s.id}" title="${escapeHtml(
                `${s.meet_time ? `${s.meet_time} ` : ''}${s.title}${s.place ? ` · ${s.place}` : ''}`
            )}">${s.meet_time ? `<b>${escapeHtml(s.meet_time)}</b> ` : ''}${escapeHtml(s.title)}</div>
        `).join('');

        const more = list.length > MAX_CHIPS
            ? `<div class="sc-more">+${list.length - MAX_CHIPS}건</div>` : '';

        cells.push(`
            <div class="sc-cal-cell${key === today ? ' today' : ''}" data-date="${key}">
                <div class="sc-cal-daynum${dow === 0 ? ' sun' : ''}${dow === 6 ? ' sat' : ''}">${day}</div>
                <div class="sc-cal-items">${chips}${more}</div>
            </div>
        `);
    }

    // 마지막 주를 7칸으로 채운다
    while (cells.length % 7 !== 0) cells.push('<div class="sc-cal-cell empty"></div>');

    el.innerHTML = `<div class="sc-cal-grid">${head}${cells.join('')}</div>`;
}

export function renderSchedules() {
    const label = `${viewYear}년 ${viewMonth + 1}월`;
    skins().forEach((ui) => {
        const el = $(ui.label);
        if (el) el.textContent = label;
        renderInto($(ui.calendar));
    });
}

/* ---------------- 데이터 ---------------- */

export async function loadSchedules() {
    const { ok, data } = await api.get('/work/api/schedules/');
    if (!ok || !data) return;
    setMyIp(data.my_ip);
    items = data.schedules || [];
    renderSchedules();
}

/* ---------------- 패널 ---------------- */

export function showPanel(which) {
    panel = which;
    skins().forEach((ui) => {
        $(ui.listPanel).hidden = which !== 'list';
        $(ui.editPanel).hidden = which !== 'edit';
    });
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

/** 날짜를 주면 그 날로, 없으면 보고 있는 달의 1일(이번 달이면 오늘)로 연다. */
function startNew(dateStr) {
    editingId = null;
    const today = todayStr();
    const isThisMonth = today.startsWith(`${viewYear}-${pad(viewMonth + 1)}`);
    fill({
        meet_date: dateStr || (isThisMonth ? today : ymd(viewYear, viewMonth, 1)),
        meet_time: '', title: '', place: '', attendees: '',
        author_name: getNickname(), memo: '',
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

    // 저장한 일정이 있는 달로 달력을 옮겨준다
    const [y, m] = meetDate.split('-').map(Number);
    viewYear = y;
    viewMonth = m - 1;

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

/* ---------------- 달 이동 ---------------- */

function moveMonth(delta) {
    const d = new Date(viewYear, viewMonth + delta, 1);
    viewYear = d.getFullYear();
    viewMonth = d.getMonth();
    renderSchedules();
}

function goToday() {
    const d = new Date();
    viewYear = d.getFullYear();
    viewMonth = d.getMonth();
    renderSchedules();
}

/* ---------------- 초기화 ---------------- */

export function initSchedule() {
    const now = new Date();
    viewYear = now.getFullYear();
    viewMonth = now.getMonth();

    skins().forEach((ui) => {
        const cal = $(ui.calendar);
        if (cal) {
            cal.addEventListener('click', (e) => {
                // 일정 제목을 누르면 수정, 빈 칸을 누르면 그 날짜로 등록
                const chip = e.target.closest('.sc-chip');
                if (chip) {
                    startEdit(chip.dataset.id);
                    return;
                }
                const cell = e.target.closest('.sc-cal-cell');
                if (cell && cell.dataset.date) startNew(cell.dataset.date);
            });
        }

        $(ui.prev).addEventListener('click', () => moveMonth(-1));
        $(ui.next).addEventListener('click', () => moveMonth(1));
        $(ui.today).addEventListener('click', goToday);
        $(ui.newBtn).addEventListener('click', () => startNew(null));
        $(ui.cancel).addEventListener('click', () => showPanel('list'));
        $(ui.save).addEventListener('click', save);
        $(ui.del).addEventListener('click', remove);
    });

    onThemeChange(() => {
        renderSchedules();
        showPanel(panel);
    });

    showPanel('list');
    renderSchedules();
}
