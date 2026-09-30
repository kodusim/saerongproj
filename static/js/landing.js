const examples = {
  heart: {
    title: '그 고민에 누군가의 얼굴이 떠오르나요?',
    answers: ['네, 떠오르는 사람이 있어요', '아니요, 제 자신의 문제예요', '아직 잘 모르겠어요'],
    next: ['그 사람의 마음이 궁금한가요, 아니면 내 마음을 전할지 망설이고 있나요?', '지금 상황을 바꾸고 싶은 마음과 지키고 싶은 마음 사이에서 고민하고 있나요?', '답을 찾는 것보다 누군가 이야기를 들어줬으면 하는 마음에 더 가까운가요?'],
  },
  work: {
    title: '지금의 선택을 바꾸면 잃게 될 것이 먼저 떠오르나요?',
    answers: ['네, 잃는 것이 걱정돼요', '새로 얻을 것이 더 궁금해요', '어느 쪽인지 잘 모르겠어요'],
    next: ['익숙한 생활이 달라지는 게 걱정인가요, 주변의 반응이 더 신경 쓰이나요?', '지금 가장 바라는 건 더 나은 조건인가요, 다른 일을 해보는 경험인가요?', '선택을 미룰 수 있다면 안심될 것 같나요, 오히려 더 답답할 것 같나요?'],
  },
  distance: {
    title: '그 사람과 만나고 나면 혼자만의 시간이 더 필요해지나요?',
    answers: ['네, 혼자 쉬고 싶어져요', '아니요, 더 함께 있고 싶어요', '만날 때마다 달라요'],
    next: ['상대에게 맞추느라 지치는 건가요, 하고 싶은 말을 참게 되는 건가요?', '먼저 다가가고 싶지만 상대에게 부담이 될까 망설이고 있나요?', '특정한 이야기가 나올 때 마음이 불편해지는 편인가요?'],
  },
  self: {
    title: '요즘 마음이 복잡해지는 순간에 공통점이 있나요?',
    answers: ['혼자 있을 때 생각이 많아져요', '사람들과 있을 때 더 복잡해요', '특별한 이유를 모르겠어요'],
    next: ['지난 일이 자꾸 떠오르나요, 아직 일어나지 않은 일이 더 신경 쓰이나요?', '다른 사람의 시선과 내 기준 사이에서 마음이 흔들리는 편인가요?', '지금은 문제를 풀고 싶은 마음과 잠깐 쉬고 싶은 마음 중 어느 쪽에 가까운가요?'],
  },
};
const preview = document.querySelector('#preview');
const followUp = document.querySelector('#follow-up');
const answerButtons = [...document.querySelectorAll('[data-answer]')];
let currentExample = examples.heart;
document.querySelectorAll('[data-preview]').forEach(button => button.addEventListener('click', () => {
  currentExample = examples[button.dataset.preview];
  document.querySelector('#preview-title').textContent = currentExample.title;
  followUp.hidden = true;
  answerButtons.forEach((answer, index) => {
    answer.textContent = currentExample.answers[index];
    answer.setAttribute('aria-pressed', 'false');
  });
  preview.showModal();
}));
document.querySelector('#close-preview').addEventListener('click', () => preview.close());
preview.addEventListener('click', event => {
  const rect = preview.getBoundingClientRect();
  if (event.target === preview && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) preview.close();
});
answerButtons.forEach(button => button.addEventListener('click', () => {
  answerButtons.forEach(answer => answer.setAttribute('aria-pressed', String(answer === button)));
  document.querySelector('#next-question').textContent = currentExample.next[Number(button.dataset.answer)];
  followUp.hidden = false;
}));

const storageKey = 'saerong.saved-preview-ids.v1';
let saved = new Set();
try {
  const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
  if (Array.isArray(stored)) saved = new Set(stored.filter(id => typeof id === 'string' && Object.hasOwn(examples, id)));
} catch { /* Storage can be unavailable; keep session-only saves. */ }
const cards = [...document.querySelectorAll('.content-card')];
const filterButtons = [...document.querySelectorAll('[data-filter]')];
const viewButtons = [...document.querySelectorAll('[data-view]')];
const searchInput = document.querySelector('#search-input');
let filter = 'all';
let view = 'home';
function render() {
  const query = searchInput.value.trim().toLocaleLowerCase();
  let visible = 0;
  cards.forEach(card => {
    const matches = (filter === 'all' || card.dataset.category === filter)
      && (view !== 'saved' || saved.has(card.dataset.id))
      && `${card.dataset.search} ${card.querySelector('h3').textContent}`.toLocaleLowerCase().includes(query);
    card.hidden = !matches;
    if (matches) visible++;
    const save = card.querySelector('[data-save]');
    const isSaved = saved.has(card.dataset.id);
    save.setAttribute('aria-pressed', String(isSaved));
    save.setAttribute('aria-label', `${card.querySelector('h3').textContent} ${isSaved ? '보관 취소' : '보관'}`);
  });
  filterButtons.forEach(button => {
    const active = button.dataset.filter === filter;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  viewButtons.forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  document.querySelector('.banner').hidden = view !== 'home';
  document.querySelector('.page-heading').hidden = view !== 'home';
  document.querySelector('#section-title').textContent = view === 'saved' ? '보관한 이야기' : '주제별 대화 예시';
  document.querySelector('#result-count').textContent = `${visible}개`;
  document.querySelector('#empty-state').hidden = visible > 0;
  document.querySelector('#empty-message').textContent = view === 'saved' && saved.size === 0 ? '아직 보관한 이야기가 없어요. 카드의 보관 버튼을 눌러보세요.' : '이 조건에 맞는 이야기가 없어요.';
}
filterButtons.forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; render(); }));
searchInput.addEventListener('input', render);
document.querySelector('#search-toggle').addEventListener('click', event => {
  const panel = document.querySelector('#search-panel');
  panel.hidden = !panel.hidden;
  event.currentTarget.setAttribute('aria-expanded', String(!panel.hidden));
  if (!panel.hidden) searchInput.focus();
  else { searchInput.value = ''; render(); }
});
document.querySelectorAll('[data-save]').forEach(button => button.addEventListener('click', () => {
  const id = button.dataset.save;
  if (saved.has(id)) saved.delete(id); else saved.add(id);
  let persisted = true;
  try { localStorage.setItem(storageKey, JSON.stringify([...saved])); } catch { persisted = false; }
  render();
  document.querySelector('#announcement').textContent = saved.has(id) ? (persisted ? '보관함에 추가했어요.' : '현재 화면에서만 보관했어요.') : '보관함에서 삭제했어요.';
}));
viewButtons.forEach(button => button.addEventListener('click', () => {
  view = button.dataset.view;
  filter = 'all';
  searchInput.value = '';
  render();
  if (view === 'home') window.scrollTo({ top: 0, behavior: 'instant' });
  else document.querySelector('#explore').scrollIntoView({ behavior: 'instant' });
}));
document.querySelector('#reset-list').addEventListener('click', () => {
  view = 'explore'; filter = 'all'; searchInput.value = ''; render();
});
render();
