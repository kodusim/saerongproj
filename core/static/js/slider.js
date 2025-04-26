// 슬라이드 기능 JavaScript 코드
document.addEventListener('DOMContentLoaded', function() {
    // 스크롤 가능한 카드 영역 제어
    const cardContainers = document.querySelectorAll('.scrollable-cards-container');
    
    cardContainers.forEach(container => {
        const cards = container.querySelector('.scrollable-cards');
        const prevBtn = container.querySelector('.slide-prev');
        const nextBtn = container.querySelector('.slide-next');
        
        if (!cards || !prevBtn || !nextBtn) return;
        
        // 다음 슬라이드 버튼 클릭 이벤트
        nextBtn.addEventListener('click', () => {
            const cardWidth = cards.querySelector('.test-card').offsetWidth + 10; // 카드 너비 + 마진
            cards.scrollBy({ left: cardWidth * 3, behavior: 'smooth' });
        });
        
        // 이전 슬라이드 버튼 클릭 이벤트
        prevBtn.addEventListener('click', () => {
            const cardWidth = cards.querySelector('.test-card').offsetWidth + 10; // 카드 너비 + 마진
            cards.scrollBy({ left: -cardWidth * 3, behavior: 'smooth' });
        });
        
        // 드래그 스크롤 기능
        let isDown = false;
        let startX;
        let scrollLeft;
        
        cards.addEventListener('mousedown', (e) => {
            isDown = true;
            cards.classList.add('grabbing');
            startX = e.pageX - cards.offsetLeft;
            scrollLeft = cards.scrollLeft;
        });
        
        cards.addEventListener('mouseleave', () => {
            isDown = false;
            cards.classList.remove('grabbing');
        });
        
        cards.addEventListener('mouseup', () => {
            isDown = false;
            cards.classList.remove('grabbing');
        });
        
        cards.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - cards.offsetLeft;
            const walk = (x - startX) * 2; // 스크롤 속도 조절
            cards.scrollLeft = scrollLeft - walk;
        });
        
        // 터치 이벤트 처리 (모바일)
        cards.addEventListener('touchstart', (e) => {
            isDown = true;
            startX = e.touches[0].pageX - cards.offsetLeft;
            scrollLeft = cards.scrollLeft;
        }, { passive: true });
        
        cards.addEventListener('touchend', () => {
            isDown = false;
        }, { passive: true });
        
        cards.addEventListener('touchmove', (e) => {
            if (!isDown) return;
            const x = e.touches[0].pageX - cards.offsetLeft;
            const walk = (x - startX) * 2;
            cards.scrollLeft = scrollLeft - walk;
        }, { passive: true });
    });
});

function setupSliders() {
    // 모든 스크롤 가능한 카드 컨테이너 찾기
    const sliders = document.querySelectorAll('.scrollable-cards');
    
    sliders.forEach(slider => {
        // 슬라이더 상태
        const state = {
            isDown: false,
            startX: 0,
            scrollLeft: 0
        };
        
        // 마우스/터치 이벤트 리스너 설정
        slider.addEventListener('mousedown', startDrag);
        slider.addEventListener('touchstart', startDrag, {passive: true});
        
        slider.addEventListener('mousemove', drag);
        slider.addEventListener('touchmove', drag, {passive: true});
        
        slider.addEventListener('mouseleave', endDrag);
        slider.addEventListener('mouseup', endDrag);
        slider.addEventListener('touchend', endDrag);
        
        // 슬라이드 컨트롤 버튼 추가
        const parentSection = slider.closest('.section-container');
        if (parentSection) {
            const prevButton = parentSection.querySelector('.slide-prev');
            const nextButton = parentSection.querySelector('.slide-next');
            
            if (prevButton) {
                prevButton.addEventListener('click', function() {
                    slider.scrollBy({
                        left: -300,
                        behavior: 'smooth'
                    });
                });
            }
            
            if (nextButton) {
                nextButton.addEventListener('click', function() {
                    slider.scrollBy({
                        left: 300,
                        behavior: 'smooth'
                    });
                });
            }
            
            // 슬라이더에 내용이 있는지 확인하고 버튼 표시/숨김 처리
            updateButtonsVisibility(slider, prevButton, nextButton);
            
            // 스크롤 이벤트 시 버튼 상태 업데이트
            slider.addEventListener('scroll', function() {
                updateButtonsVisibility(slider, prevButton, nextButton);
            });
        }
        
        // 드래그 시작 함수
        function startDrag(e) {
            state.isDown = true;
            slider.classList.add('grabbing');
            
            // 터치 또는 마우스 이벤트 처리
            const clientX = (e.type === 'touchstart') ? e.touches[0].clientX : e.clientX;
            
            state.startX = clientX - slider.offsetLeft;
            state.scrollLeft = slider.scrollLeft;
            
            // 상위 요소의 스크롤 방지
            if (e.type !== 'touchstart') {
                e.preventDefault();
            }
        }
        
        // 드래그 중 함수
        function drag(e) {
            if (!state.isDown) return;
            
            // 터치 또는 마우스 이벤트 처리
            const clientX = (e.type === 'touchmove') ? e.touches[0].clientX : e.clientX;
            
            const x = clientX - slider.offsetLeft;
            const walk = (x - state.startX) * 1.5; // 스크롤 속도 조정
            slider.scrollLeft = state.scrollLeft - walk;
            
            // 상위 요소의 스크롤 방지
            if (e.type !== 'touchmove') {
                e.preventDefault();
            }
        }
        
        // 드래그 종료 함수
        function endDrag() {
            state.isDown = false;
            slider.classList.remove('grabbing');
        }
    });
}

// 슬라이더 버튼 표시/숨김 상태 업데이트
function updateButtonsVisibility(slider, prevButton, nextButton) {
    if (!prevButton || !nextButton) return;
    
    // 스크롤 위치 확인
    const isAtStart = slider.scrollLeft <= 5;
    const isAtEnd = slider.scrollLeft + slider.offsetWidth >= slider.scrollWidth - 5;
    
    // 버튼 상태 업데이트
    prevButton.style.opacity = isAtStart ? '0.3' : '1';
    prevButton.style.pointerEvents = isAtStart ? 'none' : 'auto';
    
    nextButton.style.opacity = isAtEnd ? '0.3' : '1';
    nextButton.style.pointerEvents = isAtEnd ? 'none' : 'auto';
    
    // 모바일에서 슬라이더 컨텐츠가 적을 경우 버튼 숨기기
    if (slider.scrollWidth <= slider.offsetWidth) {
        prevButton.style.display = 'none';
        nextButton.style.display = 'none';
    } else {
        prevButton.style.display = 'flex';
        nextButton.style.display = 'flex';
    }
}

