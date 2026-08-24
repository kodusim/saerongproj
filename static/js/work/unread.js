/* 안 읽은 메시지 배지 — 탭을 벗어나 있을 때 제목과 파비콘에 개수를 표시한다. */

const NAVY = '#1B3A6B';
const RED = '#e0393e';

let baseTitle = '';
let unread = 0;
let favLink = null;

export function isTabActive() {
    return !document.hidden && document.hasFocus();
}

function ensureFavLink() {
    let link = document.querySelector('link[rel="icon"]');
    if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
    }
    return link;
}

function drawFavicon(count) {
    const size = 64;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = NAVY;
    ctx.fillRect(4, 4, size - 8, size - 8);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 30px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('W', size / 2, size / 2 + 2);

    if (count > 0) {
        ctx.beginPath();
        ctx.arc(size - 16, 16, 16, 0, Math.PI * 2);
        ctx.fillStyle = RED;
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 18px sans-serif';
        ctx.fillText(count > 9 ? '9+' : String(count), size - 16, 17);
    }

    favLink.href = canvas.toDataURL('image/png');
}

function paint() {
    document.title = unread > 0 ? `(${unread}) ${baseTitle}` : baseTitle;
    drawFavicon(unread);
}

export function addUnread(n) {
    if (isTabActive()) return;
    unread += n;
    paint();
}

export function markAllRead() {
    if (unread === 0) return;
    unread = 0;
    paint();
}

export function initUnread() {
    baseTitle = document.title;
    favLink = ensureFavLink();

    document.addEventListener('visibilitychange', () => {
        if (isTabActive()) markAllRead();
    });
    window.addEventListener('focus', () => {
        if (isTabActive()) markAllRead();
    });

    paint();
}
