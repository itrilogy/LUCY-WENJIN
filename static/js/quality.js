// 数据质量看板
async function loadQuality(){
  const box=$('qualityBox');
  if(!box) return;
  box.innerHTML='<span class="spinner"></span>加载中…';
  try{
    const d=await fetch('/api/quality').then(r=>r.json());
    let h=`<div class="card" style="margin-bottom:12px">
      <h3 style="font-size:14px;margin-bottom:8px">数据年份</h3>
      <p>录取数据 <strong>${d.scoreYear}</strong> · 招生计划 <strong>${d.planYear}</strong></p>
      <div class="stats" style="margin-top:8px">
        <div class="stat" style="background:#2563eb"><span class="stat-num">${d.counts.college_info}</span>学校</div>
        <div class="stat" style="background:#7c3aed"><span class="stat-num">${d.counts.schoolscore}</span>校线</div>
        <div class="stat" style="background:#db2777"><span class="stat-num">${d.counts.majorscore}</span>专业线</div>
        <div class="stat" style="background:#059669"><span class="stat-num">${d.counts.college_plan}</span>计划</div>
      </div>
      <p style="margin-top:8px;color:var(--muted);font-size:13px">计划覆盖学校 ${d.coverage.planSchools} · 录取覆盖学校 ${d.coverage.scoreSchools}</p>
    </div>`;
    h+=`<div class="card"><h3 style="font-size:14px;margin-bottom:8px">2026 选科要求分布 (Top)</h3>
      <table><thead><tr><th>selectSubjects</th><th>条数</th></tr></thead><tbody>`;
    (d.selectSubjectsTop||[]).forEach(r=>{
      h+=`<tr><td><code>${r.selectSubjects||'(空)'}</code></td><td>${r.n}</td></tr>`;
    });
    h+='</tbody></table></div>';
    h+=`<div class="card" style="margin-top:12px"><h3 style="font-size:14px;margin-bottom:8px">一分一段表</h3>`;
    if(d.rankTable&&d.rankTable.length){
      h+='<table><thead><tr><th>年</th><th>科类</th><th>行数</th><th>分范围</th><th>来源</th></tr></thead><tbody>';
      d.rankTable.forEach(r=>{
        const src=r.source==='baidu'?'官方数据(Baidu)':r.source;
        h+=`<tr><td>${r.year}</td><td>${r.curriculum}</td><td>${r.n}</td><td>${r.minScore}–${r.maxScore}</td><td>${src}</td></tr>`;
      });
      h+='</tbody></table>';
    }else{
      h+='<p style="color:var(--muted)">尚未构建。请从百度拉取官方一分一段，或生成近似表。</p>';
    }
    h+=`<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-secondary btn-sm" onclick="rebuildRankTable('baidu')">拉取官方一分一段</button>
      <button class="btn btn-secondary btn-sm" onclick="rebuildRankTable('approx')">重建近似表</button>
      <button class="btn btn-secondary btn-sm" onclick="runCalibration()">运行概率校准</button>
    </div></div>`;
    if(d.calibration){
      const lg=d.calibration.logistic||{};
      const vol=d.calibration.volatility||{};
      h+=`<div class="card" style="margin-top:12px"><h3 style="font-size:14px;margin-bottom:8px">概率校准参数</h3>
        <p style="font-size:13px">k=<strong>${lg.k}</strong> bias=<strong>${lg.bias}</strong> σ=<strong>${vol.sigma}</strong>
        · 跨年样本 n=${vol.n||0} · 拟合样本 n=${lg.n||0}<br>
        <span style="color:var(--muted)">${d.calibration.updatedAt||''} · ${d.calibration.curriculum||''}</span></p></div>`;
    }
    box.innerHTML=h;
  }catch(e){
    box.innerHTML='<p style="color:var(--muted)">加载失败</p>';
  }
}

async function rebuildRankTable(source){
  source=source||'baidu';
  showToast(source==='baidu'?'正在从百度拉取一分一段…':'正在重建近似表…','info');
  const r=await fetch('/api/rank/rebuild',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({source})}).then(r=>r.json());
  if(r.ok){showToast('已写入 '+r.rows+' 行 ('+ (r.source||source)+')','info');loadQuality();}
  else showToast('失败','err');
}

async function runCalibration(){
  showToast('正在校准概率模型…','info');
  const r=await fetch('/api/rank/calibrate',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({curriculum:'物理类'})}).then(r=>r.json());
  if(r.ok){
    const lg=r.calibration.logistic||{};
    showToast(`校准完成 k=${lg.k} bias=${lg.bias}`,'info');
    loadQuality();
  }else showToast('校准失败','err');
}
