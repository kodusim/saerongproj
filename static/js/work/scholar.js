/* 구글 스칼라 검색 결과 패널.

   title_html / meta_html / snippet_html 은 서버(app/services/scholar.py)에서
   <b>·<a> 만 남기고 나머지를 escape 한 값이다 — 그래서 innerHTML 로 넣는다.
   그 외 값(텍스트·URL)은 여기서 escape 한다. */
import { $, escapeHtml } from '../lib/dom.js';
import { api } from '../lib/api.js';

let queryEl;
let resultsEl;

function renderError(data) {
    const div = document.createElement('div');
    div.className = 'scholar-error';
    div.innerHTML = escapeHtml(data.error)
        + (data.fallback_url
            ? `<br><a href="${escapeHtml(data.fallback_url)}" target="_blank" rel="noopener">Google Scholar에서 직접 열기 ↗</a>`
            : '');
    resultsEl.appendChild(div);
}

function renderItem(r) {
    const item = document.createElement('div');
    item.className = 'scholar-item';

    const openTag = r.source_link
        ? `<a href="${escapeHtml(r.source_link)}" target="_blank" rel="noopener">` : '';
    const closeTag = r.source_link ? '</a>' : '';
    const label = r.source_label
        ? `<span class="s-source-label">${escapeHtml(r.source_label)}</span> ` : '';
    const sourceBadge = r.source_site
        ? `<div class="s-source">${openTag}${label}${escapeHtml(r.source_site)}${closeTag}</div>` : '';

    const footer = (r.footer_links || [])
        .map((f) => `<a href="${escapeHtml(f.url)}" target="_blank" rel="noopener">${escapeHtml(f.text)}</a>`)
        .join('<span class="s-sep">·</span>');

    item.innerHTML = `
        <div class="s-main">
            <a class="s-title" href="${escapeHtml(r.link || '#')}" target="_blank" rel="noopener">${r.title_html}</a>
            <div class="s-meta">${r.meta_html}</div>
            <div class="s-snippet">${r.snippet_html}</div>
            <div class="s-footer">
                <span>☆ 저장</span>
                ${footer ? `<span class="s-sep">·</span>${footer}` : ''}
            </div>
        </div>
        ${sourceBadge}
    `;
    resultsEl.appendChild(item);
}

function render(data) {
    resultsEl.innerHTML = '';

    if (data.error) {
        renderError(data);
        return;
    }

    if (data.stats) {
        const stats = document.createElement('div');
        stats.className = 'scholar-stats';
        stats.textContent = data.stats;
        resultsEl.appendChild(stats);
    }

    const results = data.results || [];
    if (!results.length) {
        resultsEl.insertAdjacentHTML('beforeend', '<div class="scholar-empty">검색 결과가 없습니다.</div>');
        return;
    }

    results.forEach(renderItem);
}

async function search() {
    const q = queryEl.value.trim();
    if (!q) return;

    resultsEl.innerHTML = '<div class="scholar-loading">검색 중...</div>';

    const { data } = await api.get(`/work/api/scholar/?q=${encodeURIComponent(q)}`);
    if (!data) {
        render({ error: '네트워크 오류가 발생했습니다.' });
        return;
    }
    render(data);
}

export function initScholar() {
    queryEl = $('scholar-q');
    resultsEl = $('scholar-results');

    $('scholar-search').addEventListener('click', search);
    queryEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') search();
    });
}
