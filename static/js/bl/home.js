/* /bltest 홈 — 작품 목록. */
import { $, escapeHtml } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { authorHeaders } from './key.js';
import { seriesCard } from './card.js';

let timer = null;

async function load() {
    const params = new URLSearchParams();
    const q = $('q').value.trim();
    if (q) params.set('q', q);
    params.set('sort', $('sort').value);

    const { ok, data } = await api.get(`/bltest/api/series/?${params}`, {
        headers: authorHeaders(),
    });
    if (!ok || !data) return;

    const list = data.series || [];
    $('list').innerHTML = list.length
        ? list.map(seriesCard).join('')
        : `<div class="bl-empty">
               아직 등록된 작품이 없습니다.<br>
               <a href="/bltest/write">작가 서재</a>에서 첫 작품을 올려보세요.
           </div>`;
}

/** 입력 중엔 요청을 몰아서 보낸다 */
function debounced() {
    clearTimeout(timer);
    timer = setTimeout(load, 250);
}

$('q').addEventListener('input', debounced);
$('sort').addEventListener('change', load);

load();
