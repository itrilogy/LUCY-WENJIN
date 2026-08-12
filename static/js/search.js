// 状态
let _f={},selP=[],selT=[],selN=[],selY=[],selY2=[],selP2=[],selRecP=[];

async function init(){
  _f=await fetch('/api/filters').then(r=>r.json());
  buildMulti('fpph','mdp',_f.provinces,selP,'p',()=>search(1));
  buildMulti('ftph','mdt',_f.types,selT,'t',()=>search(1));
  buildMulti('fnph','mdn',_f.natures,selN,'n',()=>search(1));
  buildMulti('myph','mdy',_f.years,selY,'y',null);
  buildMulti('pyph','mdy2',_f.planYears,selY2,'y2',null);
  buildMulti('pph','pdp',_f.provinces,selP2,'p2',null);
  buildMulti('rph','rdp',_f.provinces,selRecP,'rp',null);
  search(1);
}

// 大学搜索（后端分页+排序）
let _schoolSort='rank',_schoolOrder='asc',_schoolPage=1;

async function search(pg){
  _schoolPage=pg||1;
  const p=new URLSearchParams();
  const n=$('f_name').value.trim();if(n)p.set('name',n);
  selP.forEach(v=>p.append('province',v));selT.forEach(v=>p.append('type',v));selN.forEach(v=>p.append('nature',v));
  document.querySelectorAll('.ftag:checked').forEach(cb=>p.append('tag',cb.value));
  p.set('page',_schoolPage);p.set('sort',_schoolSort);p.set('order',_schoolOrder);
  const d=await fetch('/api/schools?'+p).then(r=>r.json());
  _schoolData=d.rows;
  renderSchools();
  renderPager(d);
}

function sortBy(col){
  if(_schoolSort===col) _schoolOrder=_schoolOrder==='asc'?'desc':'asc';
  else{_schoolSort=col;_schoolOrder='asc';}
  search(1);
}

function renderSchools(){
  const rows=_schoolData;
  const s=_schoolSort==='rank'?(_schoolOrder==='asc'?'↑':'↓'):'';
  $('t0').innerHTML=rows.length?`<table><thead><tr><th style="cursor:pointer;user-select:none" onclick="sortBy('rank')">排名 ${s}</th><th>大学</th><th>省份</th><th>标签</th></tr></thead><tbody>`+
    rows.map(r=>`<tr><td>${r.uniqueRank||'-'}</td><td class="link" onclick="sd('${esc(r.college_name)}')">${r.college_name}</td><td>${r.province||''}</td><td>${tg(r.tag)}</td></tr>`).join('')+
    '</tbody></table>':'<p style="color:var(--muted)">无匹配</p>';
}

function renderPager(d){
  if(d.pages<=1){$('t0').innerHTML+=`<p style="color:var(--muted);font-size:13px;text-align:center;margin-top:8px">共${d.total}所</p>`;return;}
  let h=`<div style="display:flex;gap:4px;margin-top:12px;justify-content:center;align-items:center;flex-wrap:wrap">`;
  h+=`<button onclick="search(1)" style="padding:4px 10px;border-radius:4px;border:1px solid var(--border);background:var(--card);cursor:pointer;font-size:13px">«</button>`;
  let start=Math.max(1,d.page-2),end=Math.min(d.pages,d.page+2);
  if(start>1){h+=`<span style="font-size:13px;color:var(--muted)">...</span>`;}
  for(let i=start;i<=end;i++){
    h+=`<button onclick="search(${i})" style="padding:4px 10px;border-radius:4px;border:1px solid ${i===d.page?'var(--primary)':'var(--border)'};background:${i===d.page?'var(--primary)':'var(--card)'};color:${i===d.page?'#fff':'var(--text)'};cursor:pointer;font-size:13px;font-weight:${i===d.page?'600':'400'}">${i}</button>`;
  }
  if(end<d.pages){h+=`<span style="font-size:13px;color:var(--muted)">...</span>`;}
  h+=`<button onclick="search(${d.pages})" style="padding:4px 10px;border-radius:4px;border:1px solid var(--border);background:var(--card);cursor:pointer;font-size:13px">»</button>`;
  h+=`<span style="font-size:12px;color:var(--muted);margin-left:6px">共${d.total}所</span></div>`;
  $('t0').innerHTML+=h;
}

// 学校详情
let _sdName='';
async function sd(name){
  if(!name) return;
  document.getElementById('s_name').value=name;
  _sdName=name;
  // 保存输入框当前值（HTML 重建后恢复）
  const saved={};
  ['r1_min','r1_max','s1_min','s1_max'].forEach(id=>{const el=$(id);if(el)saved[id]=el.value});
  const p=new URLSearchParams();
  const pmap={r1_min:'rank_min',r1_max:'rank_max',s1_min:'score_min',s1_max:'score_max'};
  ['r1_min','r1_max','s1_min','s1_max'].forEach(id=>{const v=$(id);if(v&&v.value)p.set(pmap[id],v.value)});
  const d=await fetch('/api/school/'+encodeURIComponent(name)+'?'+p).then(r=>r.json());
  let h=`<div class="card"><h2>${name}${tg(d.info?.tag)}</h2>`;
  h+=`<div class="flt-row" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:end">
    <div><span class="filter-label">位次</span><div class="range-group"><input id="r1_min" placeholder="下限" value="${saved.r1_min||''}" onkeydown="if(event.key==='Enter')sd(_sdName)"><span class="sep">—</span><input id="r1_max" placeholder="上限" value="${saved.r1_max||''}" onkeydown="if(event.key==='Enter')sd(_sdName)"></div></div>
    <div><span class="filter-label">分数</span><div class="range-group"><input id="s1_min" placeholder="下限" value="${saved.s1_min||''}" onkeydown="if(event.key==='Enter')sd(_sdName)"><span class="sep">—</span><input id="s1_max" placeholder="上限" value="${saved.s1_max||''}" onkeydown="if(event.key==='Enter')sd(_sdName)"></div></div>
    <button class="btn btn-sm" onclick="sd(_sdName)" style="margin-bottom:1px">🔍 查询</button>
  </div></div>`;
  h+=`<div class="cols"><div class="col card"><h3>📊 录取分数线</h3><table><thead><tr><th>年份</th><th>批次</th><th>最低分/位次</th><th>科目</th></tr></thead><tbody>`;
  d.scores.forEach(s=>h+=`<tr><td>${s.year}</td><td>${s.batchName||''}</td><td>${s.minScore||''}/${s.minScoreOrder||''}</td><td>${s.curriculum||''}</td></tr>`);
  h+=`</tbody></table></div><div class="col card"><h3>📚 专业分数线</h3><table><thead><tr><th>年份</th><th>专业</th><th>选科</th><th>最低分/位次</th></tr></thead><tbody>`;
  d.majors.forEach(m=>h+=`<tr><td>${m.year}</td><td>${m.majorName}</td><td>${m.specialCourse||''}</td><td>${m.minScore||''}/${m.minScoreOrder||''}</td></tr>`);
  h+=`</tbody></table></div></div>`;
  $('t1').innerHTML=h;sw(1);
}

// 专业反查
async function sm(){
  const p=new URLSearchParams();
  const m=$('m_name').value.trim();if(m)p.set('major',m);
  selY.forEach(v=>p.append('year',v));
  ['mr_min','mr_max','ms_min','ms_max'].forEach(id=>{const v=$(id);if(v&&v.value)p.set(id.replace('mr_','rank_').replace('ms_','score_'),v.value)});
  const rows=await fetch('/api/major_search?'+p).then(r=>r.json());
  $('t2').innerHTML=rows.length?'<table><thead><tr><th>年份</th><th>学校</th><th>专业</th><th>选科</th><th>最低分/位次</th></tr></thead><tbody>'+
    rows.map(r=>`<tr><td>${r.year}</td><td class="link" onclick="sd('${esc(r.legalName)}')">${r.legalName}</td><td>${r.majorName}</td><td>${r.specialCourse||''}</td><td>${r.minScore}/${r.minScoreOrder}</td></tr>`).join('')+
    '</tbody></table>':'<p style="color:var(--muted)">无匹配</p>';
  sw(2);
}

// 招生计划
async function sp(){
  const p=new URLSearchParams();
  const s=$('p_school').value.trim();if(s)p.set('school',s);
  const m=$('p_major').value.trim();if(m)p.set('major',m);
  selY2.forEach(v=>p.append('year',v));
  selP2.forEach(v=>p.append('province',v));
  document.querySelectorAll('.ptag:checked').forEach(cb=>p.append('tag',cb.value));
  const rows=await fetch('/api/plan_search?'+p).then(r=>r.json());
  $('t3').innerHTML=rows.length?'<table><thead><tr><th>年份</th><th>学校</th><th>专业</th><th>计划</th><th>学制</th><th>学费</th><th>选科</th></tr></thead><tbody>'+
    rows.map(r=>`<tr><td>${r.year}</td><td>${r.legalName}</td><td>${r.major_name}</td><td>${r.enroll_num||''}</td><td>${r.lengthOfSchooling||''}</td><td>${r.tuition||''}</td><td>${r.selectSubjects||''}</td></tr>`).join('')+
    '</tbody></table>':'<p style="color:var(--muted)">无匹配</p>';
  sw(3);
}
