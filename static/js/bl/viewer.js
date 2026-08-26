/* 뷰어 — 읽는 화면. 글자 크기·배경·읽던 위치를 localStorage 에 남긴다. */
import { $, escapeHtml, formatDateTime } from '../lib/dom.js';
import { api } from '../lib/api.js';
import { authorHeaders } from './key.js';

const seriesId = Number(document.body.dataset.seriesId);
const no = Number(document.body.dataset.no);

const PREF_KEY = 'bl_reader_pref';
const POS_KEY = `bl_reader_pos_${seriesId}`;

const SIZES = [14, 15, 16, 17, 19, 21, 24];

let nav = { prev: null, next: null };
let saveTimer = null;

/* ---------------- 읽기 설정 ---------------- */

function loadPref() {
    try {
        const p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
        return {
            size: SIZES.includes(p.size) ? p.size : 16,
            theme: ['light', 'sepia', 'dark'].includes(p.theme) ? p.theme : 'light',
        };
    } catch {
        return { size: 16, theme: 'light' };
    }
}

let pref = loadPref();

function applyPref() {
    document.body.dataset.theme = pref.theme;
    document.documentElement.style.setProperty('--reader-size', `${pref.size}px`);
    $('theme').value = pref.theme;
    try {
        localStorage.setItem(PREF_KEY, JSON.stringify(pref));
    } catch { /* 무시 */ }
}

function bumpSize(dir) {
    const i = SIZES.indexOf(pref.size);
    const next = SIZES[Math.min(SIZES.length - 1, Math.max(0, i + dir))];
    pref.size = next;
    applyPref();
}

/* ---------------- 읽던 위치 ---------------- */

function saveScroll() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
        const max = document.body.scrollHeight - window.innerHeight;
        const ratio = max > 0 ? window.scrollY / max : 0;
        try {
            localStorage.setItem(POS_KEY, JSON.stringify({ no, ratio }));
        } catch { /* 무시 */ }
    }, 300);
}

function restoreScroll() {
    try {
        const saved = JSON.parse(localStorage.getItem(POS_KEY) || '{}');
        if (saved.no !== no || typeof saved.ratio !== 'number') return;
        const max = document.body.scrollHeight - window.innerHeight;
        if (max > 0 && saved.ratio > 0.02) window.scrollTo(0, max * saved.ratio);
    } catch { /* 무시 */ }
}

/* ---------------- 본문 ---------------- */

async function load() {
    const { ok, data } = await api.get(`/bltest/api/series/${seriesId}/ep/${no}/`, {
        headers: authorHeaders(),
    });
    if (!ok || !data) {
        $('content').innerHTML = '<div class="bl-empty">회차를 찾을 수 없습니다.</div>';
        return;
    }

    const { series, episode } = data;
    nav = { prev: data.prev, next: data.next };
    document.title = `${episode.title} — ${series.title}`;

    $('content').innerHTML = `
        <div class="bl-reader-head">
            <a class="bl-reader-series" href="/bltest/s/${seriesId}">${escapeHtml(series.title)}</a>
            <h1>${episode.no}화. ${escapeHtml(episode.title)}</h1>
            <div class="bl-reader-meta">
                ${escapeHtml(series.author_name)}
                ${episode.published_at ? ` · ${formatDateTime(episode.published_at)}` : ' · 임시저장'}
            </div>
        </div>
        <div class="bl-body">${escapeHtml(episode.body) || '(내용 없음)'}</div>
    `;

    restoreScroll();
}

function go(dir) {
    const target = dir < 0 ? nav.prev : nav.next;
    if (target == null) {
        alert(dir < 0 ? '첫 화입니다.' : '마지막 화입니다.');
        return;
    }
    location.href = `/bltest/s/${seriesId}/${target}`;
}

/* ---------------- 이벤트 ---------------- */

document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    if (act === 'prev') go(-1);
    if (act === 'next') go(1);
    if (act === 'size-up') bumpSize(1);
    if (act === 'size-down') bumpSize(-1);
});

$('theme').addEventListener('change', () => {
    pref.theme = $('theme').value;
    applyPref();
});

document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select')) return;
    if (e.key === 'ArrowLeft') go(-1);
    if (e.key === 'ArrowRight') go(1);
});

window.addEventListener('scroll', saveScroll, { passive: true });

applyPref();
load();
