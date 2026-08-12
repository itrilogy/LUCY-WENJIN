// 多选下拉（修复版）
function td(id){$(id).classList.toggle('show')}
function buildMulti(containerId, dropId, vals, sel, prefix, onChange){
  const c=$(containerId), d=$(dropId);
  // 渲染已选项
  let html='';
  if(sel.length){sel.forEach(v=>{html+=`<span class="sel-tag">${v}<span class="del" data-p="${prefix}" data-v="${v}">×</span></span>`;});}
  else{html='<span class="ph">'+(prefix==='p'||prefix==='p2'||prefix==='rp'?'省份':prefix==='t'?'类型':prefix==='n'?'办学':'年份')+'</span>';}
  c.innerHTML=html;
  // 绑定删除事件
  c.querySelectorAll('.del').forEach(el=>{el.onclick=function(e){e.stopPropagation();const p=this.dataset.p,v=this.dataset.v;let arr;if(p==='p')arr=selP;else if(p==='t')arr=selT;else if(p==='n')arr=selN;else if(p==='y')arr=selY;else if(p==='y2')arr=selY2;else if(p==='p2')arr=selP2;else if(p==='rp')arr=selRecP;else return;const idx=arr.indexOf(v);if(idx>-1)arr.splice(idx,1);buildMulti(containerId,dropId,vals,arr,prefix,onChange);if(onChange)onChange();}});
  // 渲染下拉
  d.innerHTML=vals.map(v=>`<div class="opt ${sel.includes(v)?'chk':''}" data-v="${v}">${v}</div>`).join('');
  d.querySelectorAll('.opt').forEach(el=>{el.onclick=function(){const v=this.dataset.v;let arr;if(prefix==='p')arr=selP;else if(prefix==='t')arr=selT;else if(prefix==='n')arr=selN;else if(prefix==='y')arr=selY;else if(prefix==='y2')arr=selY2;else if(prefix==='p2')arr=selP2;else if(prefix==='rp')arr=selRecP;else return;const idx=arr.indexOf(v);if(idx>-1)arr.splice(idx,1);else arr.push(v);buildMulti(containerId,dropId,vals,arr,prefix,onChange);if(onChange)onChange();}});
}
// 点击外部关闭下拉
document.addEventListener('click',function(e){document.querySelectorAll('.multi-drop').forEach(d=>{if(!d.parentElement.contains(e.target))d.classList.remove('show')});});
