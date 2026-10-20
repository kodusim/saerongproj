const dialog = document.querySelector('#detail-dialog');
const title = document.querySelector('#dialog-title');
const content = document.querySelector('#dialog-content');
const label = document.querySelector('#dialog-label');
document.querySelector('#inquiry-form button[type="submit"]').disabled = false;
const demos = {
  neighborhood: ['동네의 발견', '관심 지역을 선택하고 생활 편의·교통 등 필요한 조건을 비교하는 공개서비스 구성 예시입니다.', '지역 선택 → 관심 조건 설정 → 지역별 지표 비교', '실제 운영 중인 서비스와 사용 데이터가 확정되면 이 위치에 소개와 사이트 링크를 연결합니다.'],
  trend: ['데이터 노트', '공개 통계의 시점별 변화를 탐색하는 서비스 구성 예시입니다.', '주제 선택 → 기간·지역 선택 → 변화 탐색', '화면의 그래프는 디자인용 도식이며 실제 분석 결과가 아닙니다.'],
  dashboard: ['엑셀 보고서의 대시보드 전환', '문제: 여러 엑셀을 수작업으로 취합해야 하는 상황을 가정했습니다.', '작업 예시: 파일 형식 정리 → 집계 규칙 정의 → 시각화 → 웹 대시보드 구현', '실제 수주 사례가 아닙니다. 공개 가능한 외주 작업의 화면과 검증된 결과로 교체할 자리입니다.'],
  search: ['흩어진 정보의 검색 도구 전환', '문제: 여러 파일에서 필요한 정보를 일일이 찾는 상황을 가정했습니다.', '작업 예시: 데이터 통합 → 검색 조건 정의 → 검색·비교 화면 구현', '실제 수주 사례가 아닙니다. 고객명과 결과는 공개 허락을 받은 내용만 등록합니다.']
};
function addParagraph(text) {
  const p = document.createElement('p');
  p.textContent = text;
  content.append(p);
}
function openDialog(heading, eyebrow) {
  title.textContent = heading;
  label.textContent = eyebrow;
  content.replaceChildren();
}
document.querySelectorAll('[data-demo]').forEach(button => {
  button.addEventListener('click', () => {
    const [heading, ...paragraphs] = demos[button.dataset.demo];
    openDialog(heading, 'PREVIEW / 구성 예시');
    paragraphs.forEach(addParagraph);
    dialog.showModal();
  });
});
document.querySelectorAll('.close-dialog, .close-bottom').forEach(button => button.addEventListener('click', () => dialog.close()));
dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
document.querySelector('#inquiry-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  for (const input of form.querySelectorAll('[required]')) {
    if (!input.value.trim()) {
      input.setCustomValidity('공백 이외의 내용을 입력해주세요.');
      input.reportValidity();
      input.addEventListener('input', () => input.setCustomValidity(''), {once: true});
      return;
    }
  }
  const data = new FormData(form);
  openDialog('문의 내용 미리보기', 'LOCAL TEST / 메일 발송 없음');
  const fields = [['name', '이름 / 회사명'], ['email', '회신 이메일'], ['data', '보유 데이터'], ['service', '원하는 서비스'], ['timeline', '희망 일정'], ['budget', '예산 범위']];
  for (const [key, caption] of fields) {
    const h = document.createElement('h4');
    h.textContent = caption;
    content.append(h);
    addParagraph(data.get(key)?.trim() || '미입력');
  }
  addParagraph('테스트용 미리보기입니다. 메일을 발송하거나 입력 내용을 저장하지 않았습니다.');
  document.querySelector('#form-status').textContent = '문의 내용을 확인했습니다. 로컬 테스트이므로 실제 메일은 발송되지 않았습니다.';
  dialog.showModal();
});
