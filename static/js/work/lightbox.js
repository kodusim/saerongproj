/* 첨부 이미지 라이트박스 */
import { $ } from '../lib/dom.js';

let modal;
let modalImg;

export function openImage(url) {
    if (!url) return;
    modalImg.src = url;
    modal.classList.add('open');
}

export function closeImage() {
    modal.classList.remove('open');
    modalImg.src = '';
}

export function initLightbox() {
    modal = $('img-modal');
    modalImg = $('img-modal-img');

    $('img-modal-close').addEventListener('click', closeImage);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeImage();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeImage();
    });
}

/** 표/로그 안의 🖼 아이콘 클릭을 위임 처리한다. */
export function bindImageIcons(container) {
    container.addEventListener('click', (e) => {
        const icon = e.target.closest('.row-img-icon');
        if (icon) openImage(icon.dataset.url);
    });
}
