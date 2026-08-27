/* 작가 서재 — 내 작품/회차 CRUD.

   작품 카드를 펼치면 그 안에 회차 목록이 들어온다 (작품마다 상세를 따로
   부르지 않고, 펼칠 때 한 번만 가져온다).

   공개 테스트 중이라 작가 키를 묻지 않는다 — 서버가 방문자 모두를 같은
   작가로 취급하므로 이 화면에는 모든 작품이 뜬다 (app/routers/bl.py 의
   OPEN_TEST 참고). */
import { $, escapeHtml, formatDateTime } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { authorHeaders } from './key.js';

let series = [];
let openId = null;        // 펼쳐 놓은 작품 id
let episodes = [];        // 그 작품의 회차
let editingSeries = null; // 작품 모달이 수정 중인 작품 (null = 새 작품)
let editingEp = null;     // 회차 모달이 수정 중인 회차 (null = 새 회차)

/* ---------------- 목록 ---------------- */

async function load() {
    const { ok, data } = await api.get('/bltest/api/series/?mine=1', {
        headers: authorHeaders(),
    });
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
    const { ok, data } = await api.get(`/bltest/api/series/${id}/`, {
        headers: authorHeaders(),
    });
    if (!ok || !data) return;
    openId = id;
    episodes = data.episodes || [];
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
        author_name: $('s-author').value.trim() || '익명',
        summary: $('s-summary').value,
        tags: $('s-tags').value.split(',').map((t) => t.trim()).filter(Boolean),
        rating: $('s-rating').value,
        status: $('s-status').value,
    };

    const url = editingSeries
        ? `/bltest/api/series/${editingSeries.id}/`
        : '/bltest/api/series/create/';
    const { ok, data } = await api.postJSON(url, payload, {
        headers: authorHeaders(),
    });
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

    const { ok, data } = await api.del(`/bltest/api/series/${id}/`, {
        headers: authorHeaders(),
    });
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
        const { ok, data } = await api.get(`/bltest/api/series/${openId}/ep/${no}/`, {
            headers: authorHeaders(),
        });
        if (!ok || !data) return;
        editingEp = data.episode;
    }
    $('ep-modal-title').textContent = editingEp ? `${editingEp.no}화 수정` : '새 회차';
    $('e-title').value = editingEp ? editingEp.title : '';
    $('e-body').value = editingEp ? editingEp.body : '';
    $('ep-modal').classList.add('open');
    $('e-title').focus();
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

    const { ok, data } = await api.postJSON(url, payload, {
        headers: authorHeaders(),
    });
    if (!ok) {
        alert((data && data.error) || '저장하지 못했습니다.');
        return;
    }
    $('ep-modal').classList.remove('open');

    // 회차 목록과 작품의 화수를 다시 가져온다
    const id = openId;
    openId = null;
    await load();
    await toggle(id);
}

async function deleteEp(no) {
    if (!confirm(`${no}화를 삭제할까요? 되돌릴 수 없습니다.`)) return;
    const { ok, data } = await api.del(`/bltest/api/series/${openId}/ep/${no}/`, {
        headers: authorHeaders(),
    });
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
    if (act === 'ep-cancel') $('ep-modal').classList.remove('open');
    if (act === 'ep-draft') saveEp(false);
    if (act === 'ep-publish') saveEp(true);
});

load();
