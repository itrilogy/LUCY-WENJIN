function showAbout(){
  var el = document.getElementById('aboutOverlay');
  if(el) el.style.display = 'flex';
  else showToast('鹿溪志愿 v1.2 — 鹿溪联合创新实验室', 'info');
}
function hideAbout(){document.getElementById('aboutOverlay').style.display='none'}

// ═══ B. Toast 通知 ═══
function showToast(msg, type='info', duration=3000){
  const t=$('toast');
  t.textContent=msg;
  t.className='toast '+type+' show';
  clearTimeout(t._timer);
  t._timer=setTimeout(()=>t.classList.remove('show'), duration);
}

// ═══ E. 防抖工具 ═══
const _debounces={};
function debounce(key, ms=300){
  clearTimeout(_debounces[key]);
  _debounces[key]=setTimeout(()=>{
    if(key==='sd') sd(_sdName);
  }, ms);
}
const N=['p0','p1','p2','p3','p4','p5','p6','p7'], tabs=[];
document.querySelectorAll('.nav-item[data-tab]').forEach((e,i)=>{tabs.push(e);e.onclick=()=>sw(i)});
function sw(i){
  document.querySelectorAll('.page').forEach((p,j)=>p.classList.toggle('active',j===i));
  tabs.forEach((t,j)=>t.classList.toggle('active',j===i));
  if(i===0) init();
  if(i===7 && typeof loadQuality==='function') loadQuality();
}
function $(id){return document.getElementById(id)}
function esc(s){return (s||'').replace(/['"]/g,'')}
function htmlEsc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function tg(t){if(!t)return '';const m={'985':'t985','211':'t211','双一流':'tsyl','强基计划':'tqj'};return t.split(',').filter(Boolean).map(x=>{const e=Object.entries(m).find(([k])=>x.includes(k));return `<span class="tag ${e?e[1]:''}">${x.trim()}</span>`}).join(' ');}
