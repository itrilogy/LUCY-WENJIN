// 志愿推荐（v1.2 · 概率 + 导出）
function ag(){document.getElementById('r_ag').textContent=document.getElementById('r_aggr').value+'%';}
function sf(){document.getElementById('r_sf').textContent=document.getElementById('r_safe').value+'%';}
function rf(){document.getElementById('r_rf').textContent=parseFloat(document.getElementById('r_rfw').value).toFixed(1);}

function probBadge(adm){
  if(!adm) return '<span style="color:var(--muted)">—</span>';
  const lv=adm.level||'';
  const color=lv==='safe'?'#16a34a':lv==='match'?'#2563eb':lv==='edge'?'#ea580c':'#e11d48';
  const title=`${adm.label||''} 区间 ${adm.rangePct||''}（启发式，非官方）`;
  return `<span title="${title}" style="color:${color};font-weight:600">${adm.pct||'—'}</span><div style="font-size:10px;color:var(--muted)">${adm.rangePct||''}</div>`;
}

async function rec(){
  const score=$('r_score').value,rank=$('r_rank').value;
  if(!score||!rank){showToast('请填写分数和位次', 'warn');return}
  $('rLoading').style.display='block';$('rRes').innerHTML='';$('rSum').innerHTML='';
  const first=document.querySelector('input[name=r_first]:checked')?.value||'物理';
  const seconds=[...document.querySelectorAll('.r_second:checked')].map(cb=>cb.value);
  const keyword=$('r_keyword').value.trim();
  const kwMode=document.querySelector('input[name=r_kw_mode]:checked')?.value||'optional';
  const tagMode=document.querySelector('input[name=r_tag_mode]:checked')?.value||'or';
  const tags=[...document.querySelectorAll('.r_tag:checked')].map(cb=>cb.value);
  const provs=selRecP;
  const aggr=parseInt(document.getElementById('r_aggr').value);
  const safety=parseInt(document.getElementById('r_safe').value);
  const usePlan=document.getElementById('r_plan').checked;
  const rankFilterWidth=parseFloat(document.getElementById('r_rfw').value);
  const sortBy=document.querySelector('input[name=r_sort]:checked')?.value||'score';
  const useCluster=document.getElementById('r_cluster')?document.getElementById('r_cluster').checked:true;
  const r=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({score:+score,rank:+rank,firstSubject:first,secondSubjects:seconds,freeMajor:keyword,freeMajorMode:kwMode,tagMode:tagMode,tags:tags,provinces:provs,aggressiveness:aggr,safety:safety,usePlan:usePlan,rankFilterWidth:rankFilterWidth,sortBy:sortBy,useCluster:useCluster})}).then(r=>r.json());
  $('rLoading').style.display='none';
  if(r.error){$('rRes').innerHTML=`<p style="color:var(--muted)">${r.error}</p>`;return}
  let expandNote='';
  if(r.keywordsExpanded&&r.keywordsExpanded.length>1){
    expandNote=` | 专业簇扩展 ${r.keywordsExpanded.slice(0,6).join('、')}${r.keywordsExpanded.length>6?'…':''}`;
  }
  $('rSum').innerHTML=`<div class="stats"><div class="stat" style="background:#991B1B"><span class="stat-num">${r.reach.length}</span>冲刺梯度</div><div class="stat" style="background:#1E40AF"><span class="stat-num">${r.match.length}</span>稳健梯度</div><div class="stat" style="background:#065F46"><span class="stat-num">${r.safe.length}</span>保底梯度</div></div>
    <p style="color:var(--text-muted);font-size:13px;margin:8px 0 12px">参考基准: ${r.year} 录取线 + ${r.planYear} 招生计划 | 激进 ${r.aggressiveness||0}% · 保底 ${r.safety||0}% | 过滤带宽 ×${r.rankFilterWidth||3} | 概率模型 ${r.probModel||'—'}${expandNote}</p>`;
  const ti=[{k:'reach',l:'冲刺梯度',c:'tr'},{k:'match',l:'稳健梯度',c:'tm'},{k:'safe',l:'保底梯度',c:'ts'}];
  let html='';
  ti.forEach(t=>{
    const items=r[t.k];if(!items.length)return;
    html+=`<div class="tier"><div class="tier-hd ${t.c}">${t.l} · ${items.length} 个专业志愿</div><div class="tier-bd"><table><thead><tr><th>#</th><th>学校</th><th>专业</th><th title="该专业录取最低分/最低位次">分/位次</th><th title="计划数 今/去">计划</th><th title="专业位次÷考生位次">位次比</th><th title="启发式录取概率">推演概率</th><th>总分</th><th>评分</th><th>操作</th></tr></thead><tbody>`;
    items.forEach((item,i)=>{
      const s=item.scores;
      const adm=item.admit||{};
      html+=`<tr><td>${i+1}</td><td class="link" onclick="sd('${esc(item.school)}')">${item.school}${tg(item.tag)}</td>
        <td>${item.majorName}</td><td>${item.majorScore||'-'}/${item.majorRank||'-'}</td>
        <td style="font-size:12px">${item.planThisYear||'-'}/${item.planLastYear||'-'}</td><td class="num">${item.ratio}</td>
        <td>${probBadge(adm)}</td>
        <td class="num"><strong>${s.total}</strong></td>
        <td style="font-size:11px"><div class="bar-row"><span class="bar-label">位次</span><span class="bar" style="width:${s.rankScore*2.4}px;background:linear-gradient(90deg,#1D6FA5,#00D2FF)"></span><span class="bar-val">${s.rankScore}</span></div><div class="bar-row"><span class="bar-label">标签</span><span class="bar" style="width:${s.tagScore*4}px;background:linear-gradient(90deg,#0D5E42,#127A55)"></span><span class="bar-val">${s.tagScore}</span></div><div class="bar-row"><span class="bar-label">专业</span><span class="bar" style="width:${s.majorScore*5}px;background:linear-gradient(90deg,#8A6A05,#F1C40F)"></span><span class="bar-val">${s.majorScore}</span></div><div class="bar-row"><span class="bar-label">计划</span><span class="bar" style="width:${Math.max(0,s.planScore)*6.6}px;background:linear-gradient(90deg,#15803D,#4ADE88)"></span><span class="bar-val">${s.planScore}</span></div></td>
        <td><button class="btn btn-secondary btn-sm" onclick="addShortcut('${esc(item.school)}','${esc(item.majorName)}','${item.majorRank||'-'}','${s.total}','${t.k}','${adm.pct||''}')">+ 备选</button></td></tr>`;
    });
    html+=`</tbody></table></div></div>`;
  });
  $('rRes').innerHTML=html||'<p style="color:var(--muted)">未找到匹配</p>';
  window.recData = r;
  sw(4);
}

function printReport(){
  const d=window.recData; if(!d||(!d.reach?.length&&!d.match?.length&&!d.safe?.length)){showToast('没有可导出的数据', 'warn');return}
  let h=`<html><head><meta charset="UTF-8"><title>志愿推荐报告</title><style>
    body{font:12px sans-serif;padding:20px;color:#333}
    h2{color:#1e293b;font-size:18px}
    table{width:100%;border-collapse:collapse;margin:8px 0 16px}
    th,td{border:1px solid #ddd;padding:5px 8px;text-align:left;font-size:11px}
    th{background:#f1f5f9;font-weight:600}
    .tr{color:#e11d48}.tm{color:#2563eb}.ts{color:#16a34a}
    .t{font-weight:700;font-size:14px;margin:12px 0 4px}
    @media print{body{font-size:10px}th,td{padding:3px 6px}}
  </style></head><body>
  <h2>高考志愿推荐报告（江西）</h2>
  <p>参考: ${d.year}录取线 + ${d.planYear||'?'}招生计划 | 激进 ${d.aggressiveness||50}% 保底 ${d.safety||50}%</p>
  <p style="font-size:11px;color:#666">概率为启发式估算，仅供参考</p>`;
  const ti=[{k:'reach',l:'冲刺',c:'tr'},{k:'match',l:'稳健',c:'tm'},{k:'safe',l:'保底',c:'ts'}];
  ti.forEach(t=>{const items=d[t.k]||[];if(!items.length)return;
    h+=`<div class="t ${t.c}">${t.l} (${items.length})</div><table><thead><tr><th>#</th><th>学校</th><th>专业</th><th>分/位次</th><th>概率</th><th>总分</th></tr></thead><tbody>`;
    items.forEach((item,i)=>{const s=item.scores;const adm=item.admit||{};
      h+=`<tr><td>${i+1}</td><td>${item.school}</td><td>${item.majorName}</td><td>${item.majorScore||'-'}/${item.majorRank||'-'}</td><td>${adm.pct||'-'} (${adm.rangePct||''})</td><td><strong>${s.total}</strong></td></tr>`;
    });h+=`</tbody></table>`;
  });
  h+='</body></html>';const w=window.open('','_blank');
  w.document.write(h);w.document.close();setTimeout(()=>{w.focus();w.print()},500);
}

async function exportRecommendCsv(){
  const d=window.recData;
  if(!d||(!d.reach?.length&&!d.match?.length&&!d.safe?.length)){showToast('没有可导出的数据','warn');return}
  const r=await fetch('/api/recommend/export.csv',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  if(!r.ok){showToast('导出失败','err');return}
  const blob=await r.blob();
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='recommend.csv';
  a.click();
  URL.revokeObjectURL(a.href);
  showToast('已导出 CSV','info');
}

async function lookupRankFromScore(){
  const score=$('r_score').value;
  const first=document.querySelector('input[name=r_first]:checked')?.value||'物理';
  if(!score){showToast('请先填分数','warn');return}
  const cur=first==='物理'?'物理类':'历史类';
  const r=await fetch(`/api/rank/score_to_rank?score=${score}&curriculum=${encodeURIComponent(cur)}`).then(x=>x.json());
  if(r.error){showToast(r.error,'warn');return}
  if(r.rank){
    $('r_rank').value=r.rank;
    showToast(`约等位次 ${r.rank}（${r.source}，样本${r.sampleCount||'?'}）`,'info');
  }
}
