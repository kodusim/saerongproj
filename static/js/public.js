'use strict';
function toast(text) {
  document.querySelector('.toast')?.remove();
  const node = document.createElement('div');
  node.className = 'toast'; node.setAttribute('role', 'status'); node.textContent = text;
  document.body.append(node); setTimeout(() => node.remove(), 4500);
}
async function shareLink(url, title = document.title) {
  try {
    if (navigator.share) await navigator.share({title, url});
    else { await navigator.clipboard.writeText(url); toast('링크를 복사했습니다. 친구에게 보내보세요.'); }
  } catch (error) {
    if (error.name !== 'AbortError') window.prompt('이 링크를 복사해주세요.', url);
  }
}
document.querySelectorAll('[data-share-page]').forEach(button => button.addEventListener('click', () => shareLink(location.href)));
document.querySelectorAll('.dialog-close').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
async function api(path, body) {
  const token = document.cookie.split('; ').find(v => v.startsWith('csrftoken='))?.split('=').slice(1).join('=') || '';
  const response = await fetch(path, {method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(token)}, body: JSON.stringify(body)});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || data.detail || '요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.');
  return data;
}
const inquiryForm = document.querySelector('#inquiry-form');
if (inquiryForm) {
  inquiryForm.querySelector('[type=submit]').disabled = false;
  let payload = null;
  const dialog = document.querySelector('#inquiry-dialog');
  const status = document.querySelector('#form-status');
  inquiryForm.addEventListener('submit', event => {
    event.preventDefault();
    for (const field of inquiryForm.querySelectorAll('input[required]:not([type=checkbox]),textarea[required]')) {
      if (!field.value.trim()) { field.setCustomValidity('공백 이외의 내용을 입력해주세요.'); field.reportValidity(); field.addEventListener('input', () => field.setCustomValidity(''), {once:true}); return; }
    }
    payload = Object.fromEntries(new FormData(inquiryForm));
    payload.consent = inquiryForm.elements.consent.checked;
    const review = document.querySelector('#inquiry-review'); review.replaceChildren();
    [['name','이름 / 회사명'],['email','회신 이메일'],['data','보유 데이터'],['service','원하는 서비스'],['timeline','희망 일정'],['budget','예산 범위']].forEach(([key,title]) => {
      const h = document.createElement('h3'), p = document.createElement('p');
      h.textContent = title; p.textContent = payload[key] || '미입력'; review.append(h,p);
    });
    document.querySelector('#submit-status').textContent = '';
    dialog.showModal();
  });
  document.querySelector('#send-inquiry').addEventListener('click', async event => {
    const button = event.currentTarget; if (button.disabled || !payload) return;
    button.disabled = true; button.textContent = '접수 중…';
    try {
      const result = await api('/api/inquiries', payload);
      dialog.close(); inquiryForm.reset();
      inquiryForm.querySelectorAll('input,textarea,select,button').forEach(node => node.disabled = true);
      status.classList.remove('error'); status.textContent = `${result.message} 접수번호: ${result.reference}`;
      status.focus(); payload = null;
    } catch (error) {
      const target = document.querySelector('#submit-status'); target.textContent = error.message; target.classList.add('error');
    } finally { button.disabled = false; button.textContent = '문의 접수하기'; }
  });
}
const loginForm = document.querySelector('#admin-login');
if (loginForm) {
  loginForm.querySelector('button').disabled = false;
  loginForm.addEventListener('submit', async event => {
    event.preventDefault(); const button = loginForm.querySelector('button'); button.disabled = true;
    try { await api('/api/admin/login', Object.fromEntries(new FormData(loginForm))); location.assign('/admin/'); }
    catch(error) { document.querySelector('#login-status').textContent = error.message; button.disabled = false; }
  });
}
document.querySelector('#admin-logout')?.addEventListener('click', async () => {
  try { await api('/api/admin/logout', {}); location.assign('/admin/login/'); } catch(error) { toast(error.message); }
});
document.querySelectorAll('.inquiry-state').forEach(select => select.addEventListener('change', async () => {
  select.disabled = true;
  try { await api('/api/admin/inquiries/' + select.closest('[data-reference]').dataset.reference, {status:select.value}); toast('처리 상태를 저장했습니다.'); }
  catch(error) { document.querySelector('#admin-status').textContent = error.message; }
  finally { select.disabled = false; }
}));
document.querySelectorAll('.delete-inquiry').forEach(button => button.addEventListener('click', async () => {
  if (!confirm('이 문의를 영구 삭제할까요? 삭제 후에는 복구할 수 없습니다.')) return;
  button.disabled = true;
  try { await api('/api/admin/inquiries/' + button.closest('[data-reference]').dataset.reference, {status:'delete'}); location.reload(); }
  catch(error) { document.querySelector('#admin-status').textContent = error.message; button.disabled = false; }
}));
