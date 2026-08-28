/* 작품 상세 — 소개 + 회차 목록 + 신고. */
import { $, escapeHtml, formatDateTime } from '../lib/dom.js';
import { api } from '../lib/api.js';

const seriesId = Number(document.body.dataset.seriesId);
let current = null;

function render(series, episodes) {
    const badges = [
        series.rating === 'teen' ? '<span class="bl-badge teen">15세</span>' : '',
        `<span class="bl-badge">${escapeHtml(series.status_label)}</span>`,
        series.mine ? '<span class="bl-badge mine">내 작품</span>' : '',
    ].join('');

    const tags = (series.tags || []).length
        ? `<div class="bl-tags">${series.tags
            .map((t) => `<span class="bl-tag">${escapeHtml(t)}</span>`).join('')}</div>`
        : '';

    const eps = episodes.length
        ? episodes.map((e) => `
            <a class="bl-ep" href="/bltest/s/${seriesId}/${e.no}">
                <span class="bl-ep-no">${e.no}화</span>
                <span class="bl-ep-title">${escapeHtml(e.title)}</span>
                ${e.published ? '' : '<span class="bl-badge draft">임시저장</span>'}
                <span class="bl-ep-meta">${
                    e.published_at ? formatDateTime(e.published_at) : ''
                }</span>
            </a>
        `).join('')
        : '<div class="bl-empty">아직 공개된 회차가 없습니다.</div>';

    $('content').innerHTML = `
        <div class="bl-hero">
            <div class="bl-card-top">${badges}</div>
            <h1>${escapeHtml(series.title)}</h1>
            <div class="bl-hero-meta">
                <span>${escapeHtml(series.author_name)}</span>
                <span>${series.episodes}화</span>
                <span>조회 ${series.views.toLocaleString()}</span>
            </div>
            ${series.summary ? `<div class="bl-hero-sum">${escapeHtml(series.summary)}</div>` : ''}
            ${tags}
            <div class="bl-hero-actions">
                ${episodes.length
                    ? `<a class="bl-btn primary" href="/bltest/s/${seriesId}/${episodes[0].no}">첫 화 읽기</a>`
                    : ''}
                ${series.mine ? '<a class="bl-btn" href="/bltest/write">서재에서 관리</a>' : ''}
                <button class="bl-btn danger small" type="button" data-act="report">신고</button>
            </div>
        </div>

        <div class="bl-sec-title">회차 목록</div>
        <div class="bl-eps">${eps}</div>
    `;
}

async function load() {
    const { ok, data } = await api.get(`/bltest/api/series/${seriesId}/`);
    if (!ok || !data) {
        $('content').innerHTML = '<div class="bl-empty">작품을 찾을 수 없습니다.</div>';
        return;
    }
    current = data.series;
    render(data.series, data.episodes || []);
}

/* ---------------- 신고 ---------------- */

function openReport() {
    $('report-detail').value = '';
    $('report-modal').classList.add('open');
}

function closeReport() {
    $('report-modal').classList.remove('open');
}

async function sendReport() {
    const { ok, data } = await api.postJSON('/bltest/api/report/', {
        target_type: 'series',
        target_id: seriesId,
        reason: $('report-reason').value,
        detail: $('report-detail').value,
    });
    if (!ok) {
        alert((data && data.error) || '신고를 접수하지 못했습니다.');
        return;
    }
    closeReport();
    alert('신고가 접수되었습니다. 검토 후 조치하겠습니다.');
}

document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    if (act === 'report') openReport();
    if (act === 'report-cancel') closeReport();
    if (act === 'report-send') sendReport();
});

load();
