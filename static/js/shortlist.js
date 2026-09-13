// ═══ 备选清单（本地 + 云端 session 同步） ═══
let shortlist = JSON.parse(localStorage.getItem('gkShortlist')||'[]');
let shortlistSession = localStorage.getItem('gkSid')||'';

function addShortcut(school, major, rank, score, tier, prob){
  const key = school+'|'+major;
  if(shortlist.some(x=>x.key===key)){showToast('已在备选清单中', 'info');return}
  const item={key, school, major, rank, score, tier, prob:prob||'', time:new Date().toLocaleString()};
  shortlist.push(item);
  localStorage.setItem('gkShortlist', JSON.stringify(shortlist));
  renderShortlist();
  showToast('已添加 '+school+' - '+major, 'info');
  // 异步云同步
  syncShortlistCloud([item], true);
}

function renderShortlist(){
  const c=$('shortlistContent');
  if(!shortlist.length){
    c.innerHTML='暂无备选，请先在志愿推荐页点击 ➕ 添加';
    $('shortlistActions').style.display='none';
    return;
  }
  $('shortlistActions').style.display='flex';
  c.innerHTML='<table><thead><tr><th>#</th><th>学校</th><th>专业</th><th>位次</th><th>总分</th><th>概率</th><th>档位</th><th>添加时间</th><th></th></tr></thead><tbody>'+
    shortlist.map((x,i)=>'<tr><td>'+(i+1)+'</td><td class="link" onclick="sd(\''+esc(x.school)+'\')">'+x.school+'</td><td>'+x.major+'</td><td>'+x.rank+'</td><td>'+x.score+'</td><td>'+(x.prob||'—')+'</td><td>'+(x.tier==='reach'?'冲刺':x.tier==='match'?'稳健':'保底')+'</td><td style="font-size:12px;color:var(--muted)">'+x.time+'</td><td><button class="btn-sm" style="padding:2px 8px;font-size:11px;background:transparent;color:#e11d48;border:1px solid #e11d48;cursor:pointer" onclick="removeShortcut('+i+')">✕</button></td></tr>').join('')+
    '</tbody></table>';
}

function removeShortcut(idx){
  const item=shortlist[idx];
  shortlist.splice(idx,1);
  localStorage.setItem('gkShortlist', JSON.stringify(shortlist));
  renderShortlist();
  if(item&&shortlistSession){
    fetch('/api/shortlist',{method:'DELETE',headers:{'Content-Type':'application/json','X-Session-Id':shortlistSession},
      body:JSON.stringify({key:item.key,sessionId:shortlistSession})}).catch(()=>{});
  }
}

function clearShortlist(){
  if(!shortlist.length) return;
  if(!confirm('确定清空所有备选？')) return;
  shortlist=[]; localStorage.setItem('gkShortlist',JSON.stringify(shortlist)); renderShortlist();
  if(shortlistSession){
    fetch('/api/shortlist',{method:'DELETE',headers:{'Content-Type':'application/json','X-Session-Id':shortlistSession},
      body:JSON.stringify({sessionId:shortlistSession})}).catch(()=>{});
  }
}

function printShortlist(){
  if(!shortlist.length){showToast('备选清单为空','warn');return}
  let h='<html><head><meta charset="UTF-8"><title>志愿备选清单 · 问津</title><style>body{font:12px -apple-system,sans-serif;padding:24px;color:#1A2428}table{width:100%;border-collapse:collapse;margin:12px 0}th,td{border:1px solid #E2E8F0;padding:6px 10px;text-align:left;font-size:12px}th{background:#F5F7FA;color:#64748B}h2{color:#0D5E42;margin-bottom:4px}.foot{font-size:11px;color:#94A3B8;margin-top:16px}</style></head><body><h2>问津 · 志愿备选清单</h2><p style="color:#64748B;font-size:12px">导出时间: '+new Date().toLocaleString()+'</p><table><thead><tr><th>#</th><th>学校</th><th>专业</th><th>位次</th><th>总分</th><th>推演概率</th><th>梯度档位</th></tr></thead><tbody>';
  shortlist.forEach((x,i)=>{h+='<tr><td>'+(i+1)+'</td><td>'+x.school+'</td><td>'+x.major+'</td><td>'+x.rank+'</td><td>'+x.score+'</td><td>'+(x.prob||'')+'</td><td>'+x.tier+'</td></tr>';});
  h+='</tbody></table></body></html>';
  const w=window.open('','_blank');w.document.write(h);w.document.close();setTimeout(()=>{w.focus();w.print()},300);
}

function exportShortlistCsv(){
  if(!shortlist.length){showToast('备选清单为空','warn');return}
  const lines=['学校,专业,位次,总分,概率,档位,时间'];
  shortlist.forEach(x=>{
    const tier=x.tier==='reach'?'冲刺':x.tier==='match'?'稳健':'保底';
    lines.push([x.school,x.major,x.rank,x.score,x.prob||'',tier,x.time].map(v=>{
      const s=String(v??'');return s.includes(',')?'"'+s.replace(/"/g,'""')+'"':s;
    }).join(','));
  });
  const blob=new Blob(['\ufeff'+lines.join('\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='shortlist.csv';a.click();
  URL.revokeObjectURL(a.href);
  showToast('已导出 CSV','info');
}

async function syncShortlistCloud(items, appendOne){
  try{
    if(appendOne && items && items[0]){
      const r=await fetch('/api/shortlist',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':shortlistSession||''},
        body:JSON.stringify({sessionId:shortlistSession,item:items[0]})}).then(r=>r.json());
      if(r.sessionId){shortlistSession=r.sessionId;localStorage.setItem('gkSid',shortlistSession);}
      return;
    }
    const r=await fetch('/api/shortlist/sync',{method:'POST',headers:{'Content-Type':'application/json','X-Session-Id':shortlistSession||''},
      body:JSON.stringify({sessionId:shortlistSession,items:shortlist})}).then(r=>r.json());
    if(r.sessionId){shortlistSession=r.sessionId;localStorage.setItem('gkSid',shortlistSession);}
    showToast('已同步到云端 ('+(r.count||0)+'条)','info');
  }catch(e){/* 静默 */}
}

async function pullShortlistCloud(){
  try{
    const r=await fetch('/api/shortlist',{headers:{'X-Session-Id':shortlistSession||''}}).then(r=>r.json());
    if(r.sessionId){shortlistSession=r.sessionId;localStorage.setItem('gkSid',shortlistSession);}
    if(r.items && r.items.length){
      shortlist=r.items.map(x=>({
        key:x.key, school:x.school, major:x.major, rank:x.rank, score:x.score,
        tier:x.tier, prob:(x.meta&&x.meta.prob)||x.prob||'', time:x.time||''
      }));
      localStorage.setItem('gkShortlist', JSON.stringify(shortlist));
      renderShortlist();
      showToast('已从云端拉取 '+shortlist.length+' 条','info');
    }else showToast('云端暂无数据','info');
  }catch(e){showToast('拉取失败','err');}
}
