'use strict';
(() => {
  const config=JSON.parse(document.querySelector('#demo-data').textContent);
  let rows=[];
  function draw() {
    const group=Number(document.querySelector('#demo-group').value), count=Number(document.querySelector('#demo-period').value);
    rows=Array.from({length:count},(_,i)=>({day:i+1,value:Math.round(config.base*(1+group*.12+Math.sin((i+group)*.8)*.18+Math.cos(i*.3)*.1)*10)/10}));
    const values=rows.map(r=>r.value), min=Math.min(...values)*.85, max=Math.max(...values)*1.12;
    document.querySelector('#demo-average').textContent=(values.reduce((a,b)=>a+b,0)/count).toFixed(1)+' '+config.unit;
    document.querySelector('#demo-max').textContent=Math.max(...values).toFixed(1)+' '+config.unit;
    document.querySelector('#demo-count').textContent=count+'개';
    const svg=document.querySelector('#demo-chart'), ns='http://www.w3.org/2000/svg';svg.replaceChildren();
    function element(name,attrs,text) {const n=document.createElementNS(ns,name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;svg.append(n);return n;}
    element('title',{},'합성 데이터 '+config.metric+' 추세');
    for(let i=0;i<4;i++) {
      const y=25+i*60; element('line',{x1:55,x2:880,y1:y,y2:y,stroke:'#e2e8f0'});
      element('text',{x:3,y:y+5,fill:'#66758a','font-size':13},(max-(max-min)*i/3).toFixed(0));
    }
    const points=rows.map((r,i)=>[55+i*825/(count-1),205-(r.value-min)/(max-min)*180]);
    element('path',{d:'M'+points.map(p=>p.join(',')).join('L')+'L880,205L55,205Z',fill:config.color+'15'});
    element('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:config.color,'stroke-width':3,'stroke-linejoin':'round'});
    element('text',{x:55,y:245,fill:'#66758a','font-size':13},'1일');
    element('text',{x:840,y:245,fill:'#66758a','font-size':13},count+'일');
    const table=document.querySelector('#demo-table');table.replaceChildren();
    rows.forEach(row=>{const tr=document.createElement('tr');for(const value of [row.day+'일',row.value]){const td=document.createElement('td');td.textContent=value;tr.append(td);}table.append(tr);});
  }
  document.querySelectorAll('#demo-group,#demo-period').forEach(select=>select.addEventListener('change',draw));
  document.querySelector('#export-demo').addEventListener('click',()=>{
    const blob=new Blob(['\ufeffsynthetic_data_only,day,value,unit\n'+rows.map(row=>`true,${row.day},${row.value},${config.unit}`).join('\n')],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=config.id+'-synthetic-demo.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });draw();
})();
