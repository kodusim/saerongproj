'use strict';
(() => {
  const items = JSON.parse(document.querySelector('#travel-data').textContent);
  const form = document.querySelector('#travel-form'), grid = document.querySelector('#travel-grid');
  const cards = new Map([...grid.children].map(card => [card.dataset.id, card]));
  const selection = new Set(); let saved = new Set(), onlySaved = false, chosen = false;
  const validIds = new Set(items.map(item => item.id));
  try { const values = JSON.parse(localStorage.getItem('saerong-travel-saved') || '[]'); if (Array.isArray(values)) saved = new Set(values.filter(id => validIds.has(id))); } catch { /* Storage may be unavailable. */ }
  const moodNames = {nature:'자연',food:'먹거리',culture:'문화·골목',rest:'휴식'};
  function values() { return Object.fromEntries(new FormData(form)); }
  function updateSaved() {
    document.querySelector('#saved-count').textContent = saved.size;
    document.querySelectorAll('[data-save]').forEach(button => {
      const yes = saved.has(button.dataset.save); button.textContent = yes ? '♥' : '♡'; button.setAttribute('aria-pressed', String(yes));
      const item = items.find(d => d.id === button.dataset.save); button.setAttribute('aria-label', item.name + (yes ? ' 저장 취소' : ' 저장'));
    });
    try { localStorage.setItem('saerong-travel-saved', JSON.stringify([...saved])); } catch { /* Session-only saving still works. */ }
  }
  function refresh(scroll = false) {
    const q = values(); let shown = 0;
    const ranked = items.map(item => {
      const reasons = []; let points = 0;
      if (chosen && item.mood.includes(q.mood)) { points += 3; reasons.push(moodNames[q.mood] + ' 취향'); }
      if (chosen && item.transport.includes(q.transport)) { points += 2; reasons.push(q.transport === 'car' ? '자동차 이동' : '대중교통 위주'); }
      if (chosen && item.pace.includes(q.pace)) { points += 1; reasons.push(q.pace === 'light' ? '여유로운 속도' : '알찬 탐색'); }
      return {item, points, reasons};
    }).sort((a,b) => b.points-a.points);
    ranked.forEach(({item, points, reasons}) => {
      const card = cards.get(item.id);
      const visible = (q.region === 'all' || item.region === q.region) && (!onlySaved || saved.has(item.id));
      card.hidden = !visible; grid.append(card); if (visible) shown++;
      card.querySelector('.match-reason').textContent = chosen ? (reasons.length ? reasons.join(' · ') + ' 조건과 맞아요' : '선택 조건과 다른 새로운 후보예요') : '';
    });
    document.querySelectorAll('[data-region].filter').forEach(button => {
      const active = button.dataset.region === q.region; button.classList.toggle('active',active); button.setAttribute('aria-pressed',String(active));
    });
    document.querySelector('#result-title').textContent = onlySaved ? '내가 저장한 여행지' : chosen ? `${moodNames[q.mood]}가 끌리는 당신에게` : '어디로 떠나볼까요?';
    document.querySelector('#result-summary').textContent = chosen ? `${shown}개 후보 · 취향, 교통, 여행 속도가 맞는 순서로 정렬했어요.` : `${shown}개 여행 아이디어 · 지역별로 둘러보세요.`;
    document.querySelector('#empty-travel').hidden = shown > 0;
    document.querySelector('#empty-travel').textContent = onlySaved ? '이 권역에 저장한 여행지가 없습니다. 전체 권역을 선택하거나 카드의 하트를 눌러보세요.' : '조건에 맞는 후보가 없습니다.';
    const params = new URLSearchParams();
    if (chosen) for (const key of ['mood','transport','pace','region']) params.set(key,q[key]);
    else if (q.region !== 'all') params.set('region',q.region);
    history.replaceState(null,'',location.pathname + (params.size ? '?' + params : '') + location.hash);
    if (scroll) document.querySelector('#explore').scrollIntoView({behavior:'smooth'});
  }
  const query = new URLSearchParams(location.search);
  for (const key of ['mood','transport','pace','region']) {
    const value = query.get(key);
    const field = [...form.querySelectorAll(`input[name="${key}"]`)].find(input => input.value === value);
    if (field) field.checked = true;
  }
  chosen = Boolean(values().mood);
  form.addEventListener('submit', event => { event.preventDefault(); chosen = true; onlySaved = false; refresh(true); });
  document.querySelector('#reset-travel').addEventListener('click', () => { form.reset(); chosen=false; onlySaved=false; refresh(); });
  document.querySelectorAll('.filter[data-region]').forEach(button => button.addEventListener('click', () => {
    form.elements.region.value = button.dataset.region; refresh();
  }));
  document.querySelectorAll('[data-save]').forEach(button => button.addEventListener('click', () => {
    const id=button.dataset.save; saved.has(id) ? saved.delete(id) : saved.add(id); updateSaved(); if(onlySaved) refresh();
  }));
  document.querySelector('#saved-toggle').addEventListener('click', () => { onlySaved=!onlySaved; refresh(true); });
  function updateCompare() {
    document.querySelector('#compare-count').textContent=selection.size;
    document.querySelector('#compare-bar').hidden=!selection.size;
    document.querySelectorAll('.compare-input').forEach(input => { input.checked=selection.has(input.value); });
  }
  document.querySelectorAll('.compare-input').forEach(input => input.addEventListener('change', () => {
    if(input.checked && selection.size >= 3) { input.checked=false; toast('최대 3곳까지 비교할 수 있어요.'); return; }
    input.checked ? selection.add(input.value) : selection.delete(input.value); updateCompare();
  }));
  document.querySelector('#clear-compare').addEventListener('click', () => {selection.clear();updateCompare();});
  document.querySelector('#open-compare').addEventListener('click', () => {
    const root=document.querySelector('#compare-content');root.replaceChildren();
    for(const id of selection) {
      const item=items.find(d=>d.id===id), article=document.createElement('article');
      const h=document.createElement('h3');h.textContent=item.icon+' '+item.name;article.append(h);
      for(const text of [item.title, '취향: '+item.mood.map(x=>moodNames[x]).join(' · '), '이동: '+item.transport.map(x=>x==='car'?'자동차':'대중교통').join(' · '),item.tip]) { const p=document.createElement('p');p.textContent=text;article.append(p); }
      const a=document.createElement('a');a.href='/travel/'+item.id;a.textContent='여행 가이드 보기 ↗';a.className='text-link';article.append(a);root.append(article);
    }
    document.querySelector('#compare-dialog').showModal();
  });
  document.querySelector('#share-results').addEventListener('click', () => shareLink(location.origin+location.pathname+location.search, '이번엔 어디? 나의 여행 취향'));
  document.querySelector('#random-trip').addEventListener('click', () => {
    const visible=[...cards.values()].filter(card=>!card.hidden);
    if(!visible.length) {toast('먼저 여행 후보를 선택해주세요.');return;}
    const card=visible[Math.floor(Math.random()*visible.length)]; location.assign('/travel/'+card.dataset.id);
  });
  updateSaved();refresh();
})();
