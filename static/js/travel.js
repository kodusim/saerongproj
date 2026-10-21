'use strict';
(() => {
  const $ = (q, root = document) => root.querySelector(q);
  const $$ = (q, root = document) => [...root.querySelectorAll(q)];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const format = value => value == null ? '—' : Number(value).toLocaleString('ko-KR');
  const rating = p => p.rating == null ? '—' : p.rating.toFixed(2);
  const mapLink = p => 'https://map.naver.com/p/search/' + encodeURIComponent(p.name + ' ' + p.address);
  const form = $('#explore-form');
  if (!form) return;
  let results = JSON.parse($('#explorer-data').textContent);
  const cache = new Map(results.items.map(p => [p.id, p]));
  const compare = new Set();
  const storeKey = 'saerong-travel-notebook-v2';
  let notebook = [], bounds = new URLSearchParams(location.search).get('bounds') || '', requestNumber = 0, controller, map, layer;
  let selectedId = '', toastTimer, storageWarning = false;
  const markers = new Map();
  try {
    const stored = JSON.parse(localStorage.getItem(storeKey) || '[]');
    if (Array.isArray(stored)) notebook = stored.filter((p, i, all) => p && /^p-[a-f0-9]{16}$/.test(p.id) && all.findIndex(x => x?.id === p.id) === i)
      .slice(0, 20).map(p => ({id:p.id, note:typeof p.note === 'string' ? p.note.slice(0, 1000) : ''}));
  } catch { /* Corrupt/blocked local storage does not block discovery. */ }

  function toast(message) {
    const el = $('#travel-toast'); el.textContent = message; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3200);
  }
  function persist() {
    try { localStorage.setItem(storeKey, JSON.stringify(notebook)); }
    catch { if (!storageWarning) { toast('브라우저 저장이 차단되어 이번 화면에서만 보관됩니다. 노트를 내려받아 주세요.'); storageWarning = true; } }
    syncButtons();
  }
  function syncButtons() {
    $('#saved-count').textContent = notebook.length;
    $$('[data-save]').forEach(button => {
      const saved = notebook.some(p => p.id === button.dataset.save);
      button.setAttribute('aria-pressed', String(saved));
      const p = cache.get(button.dataset.save);
      button.setAttribute('aria-label', (p?.name || '장소') + (saved ? ' 저장 취소' : ' 저장'));
      if (button.classList.contains('detail-save')) button.textContent = saved ? '노트에 저장됨 ✓' : '여행 노트에 저장';
    });
    $$('[data-compare]').forEach(input => { input.checked = compare.has(input.dataset.compare); });
    $('#compare-count').textContent = compare.size;
    $('#compare-tray').hidden = compare.size === 0;
    $('#open-compare').disabled = compare.size < 2;
  }
  function toggleSave(id) {
    const index = notebook.findIndex(p => p.id === id);
    if (index >= 0) { notebook.splice(index, 1); toast('여행 노트에서 뺐습니다.'); }
    else {
      if (notebook.length >= 20) { toast('한 노트에는 최대 20곳까지 저장할 수 있습니다.'); return; }
      notebook.push({id, note:''}); toast('여행 노트에 저장했습니다.');
    }
    persist();
  }
  function parameters() {
    const params = new URLSearchParams(new FormData(form));
    for (const [key, value] of [...params]) if (!value || key === 'minimum' && value === '5' || key === 'sort' && value === 'samples') params.delete(key);
    if (bounds) params.set('bounds', bounds);
    return params;
  }
  function chips() {
    const values = Object.fromEntries(new FormData(form));
    const labels = {q:values.q, province:values.province, region:results.regions[values.region], category:results.categories[values.category], minimum:values.minimum !== '5' ? values.minimum + '건 이상' : ''};
    if (bounds) labels.bounds = '지도 범위';
    $('#active-filters').innerHTML = Object.entries(labels).filter(([, v]) => v).map(([k,v]) => `<button type="button" data-remove-filter="${k}" aria-label="${escape(v)} 조건 해제">${escape(v)} ×</button>`).join('');
  }
  const bookmark = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg>';
  function card(p, i) {
    return `<article class="place-row${selectedId === p.id ? ' is-selected' : ''}" data-id="${p.id}"><div class="place-index">${String(i + 1 + (results.page-1)*24).padStart(2,'0')}</div><div class="place-summary"><p class="place-meta">${escape(p.province)} <span>·</span> ${escape(p.category_label)}</p><a class="place-title" href="/travel/${p.id}" data-detail="${p.id}">${escape(p.name)}</a><p class="place-address">${escape(p.address)}</p><div class="place-measures"><span>방문 표본 <b>${format(p.samples)}</b><small>건</small></span><span>만족도 <b>${rating(p)}</b><small>/ 5</small></span></div><label class="compare-check"><input type="checkbox" data-compare="${p.id}">비교에 담기</label></div><button class="save-place" type="button" data-save="${p.id}" aria-label="${escape(p.name)} 저장" aria-pressed="false">${bookmark}</button></article>`;
  }
  function renderResults(fit = true) {
    results.items.forEach(p => cache.set(p.id, p));
    $('#place-list').innerHTML = results.items.map(card).join('');
    $('#result-total').textContent = format(results.total);
    $('#page-label').textContent = `${results.page} / ${results.pages}`;
    $('#prev-page').disabled = results.page <= 1;
    $('#next-page').disabled = results.page >= results.pages;
    $('#empty-results').hidden = results.total !== 0;
    const exportParams = parameters();
    $('#export-results').href = '/api/travel/export.csv?' + exportParams;
    $('#export-results').textContent = '검색 결과 CSV ↓';
    chips(); syncButtons(); drawMap(fit);
  }
  async function search(page = 1, fit = true, historyMode = 'push') {
    const current = ++requestNumber;
    controller?.abort(); controller = new AbortController();
    const params = parameters(); if (page > 1) params.set('page', page);
    $('#search-status').textContent = '기록을 찾고 있습니다…';
    $('#place-list').setAttribute('aria-busy', 'true');
    try {
      const response = await fetch('/api/travel/places?' + params, {signal:controller.signal});
      if (!response.ok) throw new Error('request');
      const next = await response.json();
      if (current !== requestNumber) return;
      results = next; renderResults(fit);
      $('#search-status').textContent = `${format(results.total)}곳을 찾았습니다.`;
      if (results.page === 1) params.delete('page'); else params.set('page', results.page);
      const url = '/travel' + (params.size ? '?' + params : '');
      if (historyMode !== 'none') history[historyMode === 'replace' ? 'replaceState' : 'pushState']({}, '', url);
    } catch (error) {
      if (error.name !== 'AbortError' && current === requestNumber) $('#search-status').innerHTML = '결과를 불러오지 못했습니다. 이전 결과를 유지합니다. <button type="button" id="retry-search">다시 시도</button>';
    } finally { if (current === requestNumber) $('#place-list').removeAttribute('aria-busy'); }
  }
  function reset() {
    for (const key of ['q','region','province','category']) form.elements[key].value = '';
    form.elements.minimum.value = '5'; form.elements.sort.value = 'samples'; bounds = ''; search();
  }
  form.addEventListener('submit', event => { event.preventDefault(); bounds = ''; search(); });
  form.addEventListener('change', event => {
    if (event.target.matches('[data-compare]')) {
      const id = event.target.dataset.compare;
      if (event.target.checked && compare.size >= 3) { event.target.checked = false; toast('최대 세 곳까지 비교할 수 있습니다.'); return; }
      event.target.checked ? compare.add(id) : compare.delete(id); syncButtons(); return;
    }
    if (event.target.matches('select, input[type=radio]')) { bounds = ''; search(); }
  });
  $('#prev-page').addEventListener('click', () => { search(results.page - 1, false); $('.results-toolbar').scrollIntoView({block:'start'}); });
  $('#next-page').addEventListener('click', () => { search(results.page + 1, false); $('.results-toolbar').scrollIntoView({block:'start'}); });
  $('#reset-filters').addEventListener('click', reset);
  $('[data-reset]').addEventListener('click', reset);
  $('#active-filters').addEventListener('click', event => {
    const key = event.target.closest('[data-remove-filter]')?.dataset.removeFilter;
    if (!key) return;
    if (key === 'bounds') bounds = ''; else form.elements[key].value = key === 'minimum' ? '5' : '';
    search();
  });
  window.addEventListener('popstate', () => {
    const params = new URLSearchParams(location.search);
    for (const key of ['q','region','province','category','minimum','sort']) form.elements[key].value = params.get(key) || ({minimum:'5',sort:'samples'}[key] || '');
    bounds = params.get('bounds') || ''; search(Number(params.get('page')) || 1, true, 'none');
  });

  function setupMap() {
    if (!window.L) { $('#travel-map').hidden = true; $('#map-fallback').hidden = false; $('#search-map').disabled = true; return; }
    map = L.map('travel-map', {scrollWheelZoom:false, maxBounds:[[32,123],[40,133]], minZoom:6, maxZoom:17}).setView([36.0,127.7], 7);
    let errors = 0;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19, attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'})
      .on('tileerror', () => { if (++errors > 3) $('#map-fallback').hidden = false; })
      .on('tileload', () => { $('#map-fallback').hidden = true; }).addTo(map);
    layer = L.layerGroup().addTo(map); drawMap();
  }
  function drawMap(fit = true) {
    $('#map-count').textContent = `${results.map_items.length}곳 표시` + (results.map_limited ? ' · 정렬 상위 300곳' : '');
    if (!map) return;
    layer.clearLayers(); markers.clear();
    const colors = {nature:'#487e60',culture:'#a27844',shopping:'#98745d',activity:'#5c8193',food:'#877c50'};
    results.map_items.forEach(p => {
      const marker = L.circleMarker([p.lat,p.lng], {radius:Math.min(12,4+Math.log2(p.samples)),weight:1.5,color:'#fff',fillColor:colors[p.category],fillOpacity:.86});
      const label = document.createElement('span'); label.textContent = `${p.name} · ${p.samples}건`;
      marker.bindTooltip(label).on('click', () => openDetail(p.id)).addTo(layer);
      markers.set(p.id, marker);
    });
    if (fit && !bounds) fitMap();
  }
  function fitMap() {
    if (!map || !results.map_items.length) return;
    map.invalidateSize(); map.fitBounds(results.map_items.map(p => [p.lat,p.lng]), {padding:[35,35], maxZoom:12, animate:false});
  }
  $('#fit-map').addEventListener('click', fitMap);
  $('#search-map').addEventListener('click', () => {
    if (!map) return;
    const b = map.getBounds();
    const box = [Math.max(124,b.getWest()),Math.max(32,b.getSouth()),Math.min(132,b.getEast()),Math.min(40,b.getNorth())];
    bounds = box.map(n=>n.toFixed(5)).join(','); search(1, false);
  });
  $$('[data-view]').forEach(button => button.addEventListener('click', () => {
    const showMap = button.dataset.view === 'map'; document.body.classList.toggle('map-mode', showMap);
    $$('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    if (showMap) setTimeout(() => { map?.invalidateSize(); fitMap(); }, 30);
  }));

  async function getPlace(id) {
    if (cache.has(id)) return cache.get(id);
    const response = await fetch('/api/travel/places/' + encodeURIComponent(id));
    if (!response.ok) throw new Error('place');
    const p = await response.json(); cache.set(p.id,p); return p;
  }
  function detailMarkup(p) {
    const histogram = p.histogram ? [...p.histogram].reverse().map((n,i) => `<div class="rating-bar"><label>${5-i}점</label><span><i style="width:${100*n/p.rating_count}%"></i></span><b>${n}건</b></div>`).join('') : '<p class="detail-note">유효 응답이 5건 미만이라 분포를 표시하지 않습니다.</p>';
    return `<p class="travel-kicker">${escape(p.province)} / ${escape(p.category_label)}</p><h2>${escape(p.name)}</h2><p class="detail-address">${escape(p.address)}</p><div class="detail-kpis"><div><span>방문 표본</span><strong>${format(p.samples)}<small> 건</small></strong><small>여행자별 1회</small></div><div><span>만족도 평균</span><strong>${rating(p)}<small> / 5</small></strong><small>${format(p.rating_count)}건 응답</small></div><div><span>체류 중앙값</span><strong>${format(p.stay_minutes)}<small> 분</small></strong><small>${format(p.stay_count)}건 유효 기록</small></div></div><div class="detail-chart"><h3>만족도 응답 분포</h3>${histogram}</div><p class="detail-note">2023년 참여자의 방문 기록입니다. 현재의 인기도나 개인별 만족도 예측이 아닙니다. 체류 시간은 과거 관측값이며 추천 소요 시간이 아닙니다.</p><div class="detail-actions"><button type="button" class="travel-btn solid detail-save" data-save="${p.id}" aria-pressed="false">여행 노트에 저장</button><a class="travel-btn" href="${escape(mapLink(p))}" target="_blank" rel="noopener">지도·운영 정보 ↗</a><a class="travel-btn" href="/travel/${p.id}">상세 링크 ↗</a></div>`;
  }
  let detailRequest = 0;
  async function openDetail(id) {
    const current = ++detailRequest, dialog = $('#place-dialog');
    $('#place-detail').textContent = '장소 기록을 불러오고 있습니다…';
    if (!dialog.open) dialog.showModal();
    try {
      const p = await getPlace(id); if (current !== detailRequest) return;
      selectedId = id; $('#place-detail').innerHTML = detailMarkup(p);
      $$('.place-row').forEach(row => row.classList.toggle('is-selected', row.dataset.id === id));
      syncButtons();
      if (map && markers.has(id)) { map.panTo([p.lat,p.lng],{animate:false}); markers.get(id).openTooltip(); }
    } catch { if (current === detailRequest) $('#place-detail').textContent = '장소를 불러오지 못했습니다. 창을 닫고 다시 선택해주세요.'; }
  }
  document.addEventListener('click', event => {
    const save = event.target.closest('[data-save]'); if (save) { toggleSave(save.dataset.save); return; }
    const link = event.target.closest('[data-detail]'); if (link && !event.ctrlKey && !event.metaKey) { event.preventDefault(); openDetail(link.dataset.detail); }
    if (event.target.id === 'retry-search') search();
  });
  $$('.close-travel-dialog').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  $$('.travel-dialog').forEach(dialog => dialog.addEventListener('click', event => {
    if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); }
  }));
  $('#clear-compare').addEventListener('click', () => { compare.clear(); syncButtons(); });
  $('#open-compare').addEventListener('click', () => {
    const places = [...compare].map(id => cache.get(id)).filter(Boolean);
    const rows = [['지역',p=>escape(p.province)],['분류',p=>escape(p.category_label)],['방문 표본',p=>format(p.samples)+'건'],['만족도',p=>rating(p)+' / 5<br><small>'+p.rating_count+'건 응답</small>'],['체류 중앙값',p=>format(p.stay_minutes)+'분<br><small>'+p.stay_count+'건 유효 기록</small>'],['주소',p=>escape(p.address)]];
    $('#comparison-content').innerHTML = `<div class="compare-scroll"><table class="comparison-table"><thead><tr><th scope="col">비교 기준</th>${places.map(p=>`<td>${escape(p.name)}</td>`).join('')}</tr></thead><tbody>${rows.map(([label,value])=>`<tr><th scope="row">${label}</th>${places.map(p=>`<td>${value(p)}</td>`).join('')}</tr>`).join('')}<tr><th>여행 노트</th>${places.map(p=>`<td><button class="travel-btn detail-save" data-save="${p.id}">저장</button></td>`).join('')}</tr></tbody></table></div><p class="detail-note">관측된 표본의 차이입니다. 방문 표본이 많다고 전국적으로 더 인기 있는 장소라는 뜻은 아닙니다.</p>`;
    syncButtons(); $('#comparison-dialog').showModal();
  });

  async function renderNotebook() {
    const container = $('#notebook-content'); container.textContent = '저장한 장소를 불러오고 있습니다…';
    const snapshot = [...notebook];
    const resolved = await Promise.all(snapshot.map(async entry => { try { return await getPlace(entry.id); } catch { return null; } }));
    container.innerHTML = snapshot.map((entry,index) => {
      const p = resolved[index];
      return `<article class="notebook-item"><span class="notebook-index">${String(index+1).padStart(2,'0')}</span><div><h3>${p ? escape(p.name) : '현재 불러올 수 없는 장소'}</h3><p>${p ? escape(p.address) : '네트워크를 확인하거나 잠시 후 다시 열어주세요.'}</p><label><span class="sr-only">${p ? escape(p.name) : '장소'} 메모</span><textarea data-note="${entry.id}" maxlength="1000" placeholder="가고 싶은 이유, 방문 전에 확인할 것…">${escape(entry.note)}</textarea></label><div class="notebook-controls"><button data-move="${entry.id}" data-delta="-1"${index===0?' disabled':''}>위로 ↑</button><button data-move="${entry.id}" data-delta="1"${index===snapshot.length-1?' disabled':''}>아래로 ↓</button>${p?`<a href="${escape(mapLink(p))}" target="_blank" rel="noopener">지도 ↗</a>`:''}<button data-remove-note="${entry.id}">삭제</button></div></div></article>`;
    }).join('') || '<div class="empty-results"><strong>아직 모아둔 장소가 없습니다.</strong><p>목록의 저장 버튼을 눌러 여행 후보를 모아보세요.</p></div>';
    $('#export-notebook').disabled = notebook.length === 0;
  }
  $('[data-open-notebook]').addEventListener('click', () => { $('#notebook-dialog').showModal(); renderNotebook(); });
  $('#notebook-content').addEventListener('input', event => {
    const entry = notebook.find(p => p.id === event.target.dataset.note);
    if (entry) { entry.note = event.target.value.slice(0,1000); persist(); }
  });
  $('#notebook-content').addEventListener('click', event => {
    const remove = event.target.closest('[data-remove-note]');
    if (remove) { notebook = notebook.filter(p=>p.id!==remove.dataset.removeNote); persist(); renderNotebook(); }
    const move = event.target.closest('[data-move]');
    if (move) {
      const index = notebook.findIndex(p=>p.id===move.dataset.move), next = index + Number(move.dataset.delta);
      if (index >= 0 && next >= 0 && next < notebook.length) { [notebook[index],notebook[next]]=[notebook[next],notebook[index]]; persist(); renderNotebook(); }
    }
  });
  $('#export-notebook').addEventListener('click', () => {
    const text = ['내 여행 노트 · 새롱','직접 정리한 방문 후보입니다. 이동 시간과 운영 정보는 별도 확인하세요.','',...notebook.map((entry,i)=>{
      const p=cache.get(entry.id); return `${i+1}. ${p?.name || entry.id}\n${p?.address || ''}\n${p ? mapLink(p) : ''}\n${entry.note}\n`;
    })].join('\n');
    const url = URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download='my-travel-notes.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('#share-search').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(location.href); toast('검색 조건 링크를 복사했습니다.'); }
    catch { window.prompt('검색 조건 링크를 복사하세요.', location.href); }
  });
  setupMap(); renderResults();
  if (bounds && map) { const b=bounds.split(',').map(Number); map.fitBounds([[b[1],b[0]],[b[3],b[2]]],{animate:false}); }
})();
