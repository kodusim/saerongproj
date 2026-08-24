/* /tdmprediction — 하이브리드 ML+DL 농도 예측 화면.
   ES 모듈이라 함수가 전역에 노출되지 않는다 — 실행 버튼은 아래에서 바인딩한다. */

let CHART = null;

function val(id) {
  const v = document.getElementById(id).value.trim();
  if (v === '') return null;
  return parseFloat(v);
}

async function runPredict() {
  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>예측 중…';

  const body = {
    patient: {
      age: val('f-age'), sex: parseInt(document.getElementById('f-sex').value, 10),
      height: val('f-height'), weight: val('f-weight'),
      Serum_Cr: val('f-scr'),
      CrCL_mL_per_min: val('f-crcl'),
      Albumin: val('f-alb'), AST: val('f-ast'), ALT: val('f-alt'),
      WBC: val('f-wbc'), Platelet: val('f-plt'), hs_CRP: val('f-crp'),
    },
    dose_mg: val('f-dose'), q_hr: parseFloat(document.getElementById('f-q').value),
    n_doses: parseInt(document.getElementById('f-n').value, 10),
  };

  try {
    const res = await fetch('/tdmprediction/api/predict/', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || ('HTTP ' + res.status));
    render(json);
  } catch (err) {
    alert('예측 실패: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '하이브리드 예측 실행';
  }
}

function statusClass(label) {
  if (!label) return '';
  if (label.includes('치료')) return 'status-ok';
  if (label.includes('저')) return 'status-low';
  return 'status-high';
}

function render(j) {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('result-area').style.display = 'block';

  // KPI
  const ep = j.dl_endpoint;
  if (ep) {
    document.getElementById('k-peak').textContent = ep.steady_peak;
    document.getElementById('k-trough').textContent = ep.steady_trough;
    document.getElementById('k-auc').textContent = ep.steady_auc24;
  } else {
    document.getElementById('k-peak').textContent = j.ml_predictions.ns_peak_5 || '-';
    document.getElementById('k-trough').textContent = j.ml_predictions.ns_trough_5 || '-';
    document.getElementById('k-auc').textContent = '-';
  }
  document.getElementById('k-dd').textContent = j.summary.daily_dose_mg;
  const ts = j.summary.trough_status || '';
  const as_ = j.summary.auc_status || '';
  document.getElementById('k-trough-status').innerHTML = 'mg/L <span class="status ' + statusClass(ts) + '">' + ts + '</span>';
  document.getElementById('k-auc-status').innerHTML = 'mg·hr/L <span class="status ' + statusClass(as_) + '">' + as_ + '</span>';

  // 곡선
  const curve = j.dl_curve || [];
  const direct = j.dl_direct || [];
  drawChart(curve, direct, j.summary);

  // 요약
  const s = j.summary || {};
  const meta = j.model_meta || {};
  const rows = [
    ['산출 CrCL', (s.derived_crcl ?? '-') + ' mL/min'],
    ['산출 BMI', s.derived_bmi ?? '-'],
    ['일일 총 용량', s.daily_dose_mg + ' mg/day'],
    ['목표 Trough', s.target_trough_range_mg_L.join(' ~ ') + ' mg/L'],
    ['목표 AUC₂₄', s.target_auc24_range.join(' ~ ') + ' mg·hr/L'],
    ['Trough 상태', s.trough_status || '-'],
    ['AUC 상태', s.auc_status || '-'],
    ['ML 모델', meta.ml_model || '-'],
    ['DL 모델', meta.dl_model || '(미적용)'],
  ];
  document.getElementById('summary-tbody').innerHTML = rows.map(r =>
    '<tr><td style="text-align:left;font-weight:600;color:var(--navy)">' + r[0] + '</td><td style="text-align:right">' + r[1] + '</td></tr>'
  ).join('');
}

function drawChart(curve, direct, summary) {
  const ctx = document.getElementById('conc-chart');
  if (CHART) CHART.destroy();

  const reconPts = curve.map(p => ({ x: p.t_hr, y: p.conc }));

  CHART = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: '예측 농도', data: reconPts,
          borderColor:'#1B3A6B', backgroundColor:'#1B3A6B22',
          borderWidth:2.2, tension:0, pointRadius:0, fill:false,
        },
      ],
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      parsing:false,
      plugins: {
        legend: { display:false },
        tooltip: { mode:'nearest', intersect:false },
      },
      scales: {
        y: { beginAtZero:true, title:{display:true,text:'혈중 농도 (mg/L)'}, grid:{color:'rgba(0,0,0,.05)'} },
        x: { type:'linear', title:{display:true,text:'시간 (시간)'}, grid:{display:false} },
      },
    },
  });
}

document.getElementById('run-btn').addEventListener('click', runPredict);
