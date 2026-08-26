/* 작품 카드 — 홈과 작가 서재가 같은 모양을 쓴다. */
import { escapeHtml } from '../lib/dom.js';

/** @param {object} s /bltest/api/series/ 가 주는 작품 하나 */
export function seriesCard(s) {
    const badges = [
        s.rating === 'teen' ? '<span class="bl-badge teen">15세</span>' : '',
        s.mine ? '<span class="bl-badge mine">내 작품</span>' : '',
        `<span class="bl-badge">${escapeHtml(s.status_label)}</span>`,
    ].join('');

    const tags = (s.tags || []).length
        ? `<div class="bl-tags">${s.tags
            .map((t) => `<span class="bl-tag">${escapeHtml(t)}</span>`).join('')}</div>`
        : '';

    return `
        <a class="bl-card" href="/bltest/s/${s.id}">
            <div class="bl-card-top">
                <span class="bl-card-title">${escapeHtml(s.title)}</span>
                ${badges}
            </div>
            ${s.summary ? `<div class="bl-card-sum">${escapeHtml(s.summary)}</div>` : ''}
            ${tags}
            <div class="bl-card-meta">
                <span>${escapeHtml(s.author_name)}</span>
                <span>${s.episodes}화</span>
                <span>조회 ${s.views.toLocaleString()}</span>
            </div>
        </a>
    `;
}
