/* 작가 서재 — 내 작품/회차 CRUD.

   작품 카드를 펼치면 그 안에 회차 목록이 들어온다 (작품마다 상세를 따로
   부르지 않고, 펼칠 때 한 번만 가져온다).

   이 화면은 로그인이 필요하다 — 서버가 비로그인이면 /bltest/login 으로
   돌려보낸다. 목록(`?mine=1`)에는 로그인한 계정의 작품만 온다. */
import { $, escapeHtml, formatDateTime, getCookie } from '../lib/dom.js';
import { api } from '../lib/api.js';

let series = [];
let openId = null;        // 펼쳐 놓은 작품 id
let episodes = [];        // 그 작품의 회차
let draftNos = new Set(); // 연성이 걸려 있는 회차 번호 (0 = 새 회차)
let editingSeries = null; // 작품 모달이 수정 중인 작품 (null = 새 작품)
let editingEp = null;     // 회차 모달이 수정 중인 회차 (null = 새 회차)

/* ---------------- 목록 ---------------- */

async function load() {
    const { ok, data } = await api.get('/bltest/api/series/?mine=1');
    if (!ok || !data) return;
    series = data.series || [];
    paintList();
}

function epRows() {
    if (!episodes.length) {
        return '<div class="bl-empty">아직 회차가 없습니다.</div>';
    }
    return episodes.map((e) => `
        <div class="bl-ep">
            <span class="bl-ep-no">${e.no}화</span>
            <span class="bl-ep-title">${escapeHtml(e.title)}</span>
            ${e.published ? '' : '<span class="bl-badge draft">임시저장</span>'}
            ${draftNos.has(e.no) ? '<span class="bl-badge wip">작성중</span>' : ''}
            <span class="bl-ep-meta">${
                e.published_at ? formatDateTime(e.published_at) : ''
            }</span>
            <button class="bl-btn small" type="button"
                    data-act="ep-edit" data-no="${e.no}">수정</button>
            <button class="bl-btn small danger" type="button"
                    data-act="ep-delete" data-no="${e.no}">삭제</button>
        </div>
    `).join('');
}

function paintList() {
    $('count').textContent = series.length;

    if (!series.length) {
        $('list').innerHTML = `
            <div class="bl-empty">
                아직 작품이 없습니다.<br>
                <b>＋ 새 작품</b> 을 눌러 연재를 시작하세요.
            </div>`;
        return;
    }

    $('list').innerHTML = series.map((s) => {
        const open = s.id === openId;
        const badges = [
            s.rating === 'teen' ? '<span class="bl-badge teen">15세</span>' : '',
            `<span class="bl-badge">${escapeHtml(s.status_label)}</span>`,
        ].join('');

        return `
            <div class="bl-card" style="cursor:default">
                <div class="bl-card-top">
                    <span class="bl-card-title">${escapeHtml(s.title)}</span>
                    ${badges}
                </div>
                <div class="bl-card-meta">
                    <span>${escapeHtml(s.author_name)}</span>
                    <span>${s.episodes}화</span>
                    <span>조회 ${s.views.toLocaleString()}</span>
                </div>
                <div class="bl-hero-actions">
                    <button class="bl-btn small" type="button"
                            data-act="toggle" data-id="${s.id}">
                        ${open ? '회차 접기' : '회차 관리'}
                    </button>
                    <button class="bl-btn small" type="button"
                            data-act="series-edit" data-id="${s.id}">작품 정보</button>
                    <a class="bl-btn small" href="/bltest/s/${s.id}">보기</a>
                    <button class="bl-btn small danger" type="button"
                            data-act="series-delete" data-id="${s.id}">삭제</button>
                </div>
                ${open ? `
                    <div class="bl-sec-title">
                        회차
                        <span class="bl-spacer"></span>
                        <button class="bl-btn primary small" type="button"
                                data-act="ep-new" data-id="${s.id}">＋ 새 회차</button>
                    </div>
                    <div class="bl-eps">${epRows()}</div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function toggle(id) {
    if (openId === id) {
        openId = null;
        episodes = [];
        paintList();
        return;
    }
    const { ok, data } = await api.get(`/bltest/api/series/${id}/`);
    if (!ok || !data) return;
    openId = id;
    episodes = data.episodes || [];
    draftNos = new Set((data.drafts || []).map((d) => d.episode_no));
    paintList();
}

/* ---------------- 작품 모달 ---------------- */

function openSeriesModal(s) {
    editingSeries = s;
    $('series-modal-title').textContent = s ? '작품 정보' : '새 작품';
    $('s-title').value = s ? s.title : '';
    $('s-author').value = s ? s.author_name : '';
    $('s-summary').value = s ? s.summary : '';
    $('s-tags').value = s ? (s.tags || []).join(', ') : '';
    $('s-rating').value = s ? s.rating : 'all';
    $('s-status').value = s ? s.status : 'ongoing';
    $('series-modal').classList.add('open');
    $('s-title').focus();
}

async function saveSeries() {
    const title = $('s-title').value.trim();
    if (!title) {
        alert('작품 제목을 입력하세요.');
        return;
    }

    const payload = {
        title,
        // 비우면 서버가 계정 아이디를 필명으로 쓴다
        author_name: $('s-author').value.trim(),
        summary: $('s-summary').value,
        tags: $('s-tags').value.split(',').map((t) => t.trim()).filter(Boolean),
        rating: $('s-rating').value,
        status: $('s-status').value,
    };

    const url = editingSeries
        ? `/bltest/api/series/${editingSeries.id}/`
        : '/bltest/api/series/create/';
    const { ok, data } = await api.postJSON(url, payload);
    if (!ok) {
        alert((data && data.error) || '저장하지 못했습니다.');
        return;
    }
    $('series-modal').classList.remove('open');
    load();
}

async function deleteSeries(id) {
    const s = series.find((x) => x.id === id);
    if (!s) return;
    if (!confirm(`"${s.title}" 작품을 삭제할까요?\n회차도 모두 지워지며 되돌릴 수 없습니다.`)) return;

    const { ok, data } = await api.del(`/bltest/api/series/${id}/`);
    if (!ok) {
        alert((data && data.error) || '삭제하지 못했습니다.');
        return;
    }
    if (openId === id) openId = null;
    load();
}

/* ---------------- 회차 모달 ---------------- */

async function openEpModal(no) {
    editingEp = null;
    if (no != null) {
        const { ok, data } = await api.get(`/bltest/api/series/${openId}/ep/${no}/`);
        if (!ok || !data) return;
        editingEp = data.episode;
    }
    $('ep-modal-title').textContent = editingEp ? `${editingEp.no}화 수정` : '새 회차';
    $('e-title').value = editingEp ? editingEp.title : '';
    $('e-body').value = editingEp ? editingEp.body : '';

    // 연성 — 회차 번호로 가른다. 아직 만들지 않은 새 회차는 0 (서버의 NEW_EPISODE).
    draftNo = editingEp ? editingEp.no : 0;
    lastSaved = snapshot();
    setNote('');
    await offerDraft();

    $('ep-modal').classList.add('open');
    $('e-title').focus();
}

/* ---------------- 연성(자동 저장) ----------------

   쓰다 만 회차를 서버에 담아 둔다 (localStorage 가 아니라 서버여야 다른
   기기에서 이어 쓸 수 있다). 회차 본문에 바로 쓰지 않으므로, 공개된 회차를
   고치다 만 글이 독자에게 보이는 일은 없다. */

const DRAFT_DELAY = 1500;   // 타이핑이 멎고 이만큼 지나면 저장한다
let draftNo = null;         // 편집 중인 회차 번호 (새 회차 = 0), 모달이 닫히면 null
let draftTimer = null;
let lastSaved = '';         // 마지막으로 서버에 보낸 내용 — 같으면 다시 안 보낸다

const draftUrl = () => `/bltest/api/series/${openId}/draft/${draftNo}/`;

function snapshot() {
    return JSON.stringify([$('e-title').value, $('e-body').value]);
}

function setNote(text, busy = false) {
    const el = $('ep-note');
    el.textContent = text;
    el.classList.toggle('busy', busy);
}

/** 저장된 회차 본문과 다른 연성이 있으면 이어쓸지 묻는다. */
async function offerDraft() {
    $('ep-discard').hidden = true;
    if (openId == null || draftNo == null) return;

    const { ok, data } = await api.get(draftUrl());
    const d = ok && data ? data.draft : null;
    if (!d) return;
    // 저장된 회차와 내용이 같으면 알릴 게 없다.
    if (JSON.stringify([d.title, d.body]) === lastSaved) return;

    $('ep-discard').hidden = false;
    const chars = (d.body || '').length.toLocaleString();
    const go = confirm(
        `쓰다 말은 연성이 있습니다.\n${formatDateTime(d.updated_at)} · ${chars}자\n\n`
        + '이어서 쓸까요?\n(취소해도 연성은 지우지 않습니다)'
    );
    if (!go) return;

    $('e-title').value = d.title;
    $('e-body').value = d.body;
    lastSaved = snapshot();   // 방금 복원한 내용은 이미 서버에 있다
    setNote('연성을 불러왔습니다');
}

async function saveDraft() {
    if (openId == null || draftNo == null) return;
    const snap = snapshot();
    if (snap === lastSaved) return;

    const [title, body] = JSON.parse(snap);
    const { ok } = await api.postJSON(draftUrl(), { title, body });
    if (!ok) {
        setNote('연성 저장 실패 — 연결을 확인하세요');
        return;
    }
    lastSaved = snap;
    $('ep-discard').hidden = false;
    setNote(`연성 저장됨 · ${new Date().toTimeString().slice(0, 5)}`);
}

function scheduleDraft() {
    if (draftNo == null) return;
    clearTimeout(draftTimer);
    setNote('작성 중…', true);
    draftTimer = setTimeout(saveDraft, DRAFT_DELAY);
}

/** 창을 닫거나 탭을 가릴 때의 마지막 저장. keepalive 라야 언로드 중에도 나간다. */
function flushDraft() {
    if (openId == null || draftNo == null) return;
    const snap = snapshot();
    if (snap === lastSaved) return;
    const [title, body] = JSON.parse(snap);
    try {
        fetch(draftUrl(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            credentials: 'same-origin',
            body: JSON.stringify({ title, body }),
            keepalive: true,
        });
        lastSaved = snap;
    } catch { /* 언로드 중이라 실패해도 할 수 있는 게 없다 */ }
}

async function discardDraft() {
    if (!confirm('저장해 둔 연성을 버릴까요? 되돌릴 수 없습니다.')) return;
    clearTimeout(draftTimer);
    await api.del(draftUrl());
    lastSaved = snapshot();
    $('ep-discard').hidden = true;
    setNote('연성을 버렸습니다');
}

function closeEpModal() {
    clearTimeout(draftTimer);
    saveDraft();          // 닫아도 쓰던 건 남긴다
    draftNo = null;
    $('ep-modal').classList.remove('open');
}

async function saveEp(publish) {
    const title = $('e-title').value.trim();
    if (!title) {
        alert('회차 제목을 입력하세요.');
        return;
    }

    const payload = { title, body: $('e-body').value, publish };
    const url = editingEp
        ? `/bltest/api/series/${openId}/ep/${editingEp.no}/`
        : `/bltest/api/series/${openId}/ep/create/`;

    // 회차로 확정되는 순간이라 자동 저장이 끼어들면 안 된다.
    clearTimeout(draftTimer);

    const { ok, data } = await api.postJSON(url, payload);
    if (!ok) {
        alert((data && data.error) || '저장하지 못했습니다.');
        return;
    }
    // 서버가 이 회차의 연성을 지웠다 — 클라이언트도 편집 상태를 놓는다.
    draftNo = null;
    $('ep-modal').classList.remove('open');

    // 회차 목록과 작품의 화수를 다시 가져온다
    const id = openId;
    openId = null;
    await load();
    await toggle(id);
}

async function deleteEp(no) {
    if (!confirm(`${no}화를 삭제할까요? 되돌릴 수 없습니다.`)) return;
    const { ok, data } = await api.del(`/bltest/api/series/${openId}/ep/${no}/`);
    if (!ok) {
        alert((data && data.error) || '삭제하지 못했습니다.');
        return;
    }
    const id = openId;
    openId = null;
    await load();
    await toggle(id);
}

/* ---------------- 이벤트 ---------------- */

document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const id = Number(btn.dataset.id);
    const no = Number(btn.dataset.no);

    if (act === 'new-series') openSeriesModal(null);
    if (act === 'series-edit') openSeriesModal(series.find((s) => s.id === id));
    if (act === 'series-delete') deleteSeries(id);
    if (act === 'series-cancel') $('series-modal').classList.remove('open');
    if (act === 'series-save') saveSeries();

    if (act === 'toggle') toggle(id);
    if (act === 'ep-new') openEpModal(null);
    if (act === 'ep-edit') openEpModal(no);
    if (act === 'ep-delete') deleteEp(no);
    if (act === 'ep-cancel') closeEpModal();
    if (act === 'ep-discard') discardDraft();
    if (act === 'ep-draft') saveEp(false);
    if (act === 'ep-publish') saveEp(true);
});

// 타이핑이 멎으면 자동 저장
$('e-title').addEventListener('input', scheduleDraft);
$('e-body').addEventListener('input', scheduleDraft);

// 탭을 가리거나 창을 닫을 때의 마지막 한 번. pagehide 는 모바일에서 unload 가
// 안 오는 경우(백그라운드 전환·앱 전환)를 잡는다.
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushDraft();
});
window.addEventListener('pagehide', flushDraft);

load();
