// AI 对话（SSE 流式 + 多工具）
let aiHistory=[];

function md2html(text){
  let lines=text.split('\n');
  let inTable=false, html='';
  for(let i=0;i<lines.length;i++){
    let line=lines[i];
    if(line.trim().startsWith('|')){
      const cells=line.split('|').filter(c=>c.trim()).map(c=>'<td>'+c.trim()+'</td>');
      if(!inTable){html+='<table><tr>'+cells.join('')+'</tr>';inTable=true;}
      else if(line.includes('---')) continue;
      else html+='<tr>'+cells.join('')+'</tr>';
    }else{
      if(inTable){html+='</table>';inTable=false;}
      line=line.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
      line=line.replace(/`(.+?)`/g,'<code>$1</code>');
      if(line.trim()) html+='<p>'+line+'</p>';
    }
  }
  if(inTable) html+='</table>';
  return html;
}

function addAiMsg(text,isUser){
  const d=document.getElementById('aiChat');
  const div=document.createElement('div');
  div.style.background=isUser?'#e8f4e8':'#f0f4ff';
  div.style.padding='10px 14px';div.style.borderRadius='8px';
  div.style.alignSelf=isUser?'flex-end':'flex-start';
  div.style.maxWidth='85%';div.style.whiteSpace='pre-wrap';div.style.lineHeight='1.5';
  if(isUser) div.textContent=text;
  else { div.className='ai-msg'; div.innerHTML=md2html(text); }
  d.appendChild(div);d.scrollTop=d.scrollHeight;
  return div;
}

function addAiLoading(){
  const d=document.getElementById('aiChat');
  const div=document.createElement('div');div.id='aiLoading';
  div.style.padding='10px 14px';div.style.borderRadius='8px';
  div.style.alignSelf='flex-start';div.style.backgroundColor='#f0f4ff';div.style.maxWidth='85%';
  div.textContent='⏳ 思考中...';d.appendChild(div);d.scrollTop=d.scrollHeight;
}
function removeAiLoading(){const e=$('aiLoading');if(e)e.remove();}
function setAiLoading(msg){const e=$('aiLoading');if(e)e.textContent=msg;}

async function sendAi(){
  const input=$('aiInput');const msg=input.value.trim();
  if(!msg)return;input.value='';addAiMsg(msg,true);
  addAiLoading();
  // 优先 SSE 流式
  try{
    const resp=await fetch('/api/ai/stream',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:msg,history:aiHistory})});
    if(!resp.ok || !resp.body){
      // fallback 非流式
      removeAiLoading();
      const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:msg,history:aiHistory})}).then(r=>r.json());
      if(r.reply){aiHistory=r.history;addAiMsg(r.reply,false);}
      else addAiMsg(r.error||'无回复',false);
      return;
    }
    const reader=resp.body.getReader();
    const decoder=new TextDecoder();
    let buffer='';
    let streamDiv=null;
    let acc='';
    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      buffer+=decoder.decode(value,{stream:true});
      const parts=buffer.split('\n\n');
      buffer=parts.pop();
      for(const part of parts){
        const line=part.split('\n').find(l=>l.startsWith('data: '));
        if(!line) continue;
        let ev;
        try{ev=JSON.parse(line.slice(6));}catch(e){continue;}
        if(ev.type==='status'||ev.type==='tool'){
          setAiLoading(ev.message||'处理中…');
        }else if(ev.type==='delta'){
          if(!streamDiv){
            removeAiLoading();
            streamDiv=addAiMsg('',false);
            acc='';
          }
          acc+=ev.text||'';
          streamDiv.innerHTML=md2html(acc);
          streamDiv.parentElement.scrollTop=streamDiv.parentElement.scrollHeight;
        }else if(ev.type==='done'){
          removeAiLoading();
          if(ev.history) aiHistory=ev.history;
          if(!streamDiv && ev.reply) addAiMsg(ev.reply,false);
          else if(streamDiv && ev.reply){streamDiv.innerHTML=md2html(ev.reply);acc=ev.reply;}
        }else if(ev.type==='error'){
          removeAiLoading();
          addAiMsg(ev.message||'错误',false);
        }
      }
    }
    removeAiLoading();
  }catch(e){
    removeAiLoading();
    addAiMsg('网络错误，请重试',false);
  }
}

function resetAi(){
  fetch('/api/ai/reset',{method:'POST'});
  aiHistory=[];
  document.getElementById('aiChat').innerHTML=
    '<div class="ai-msg" style="background:var(--bg-sunken);padding:10px 14px;border-radius:var(--radius-sm);align-self:flex-start;max-width:85%;border-left:3px solid var(--color-primary)">你好！我是问津志愿推演助手。支持志愿反查、梯度分布测算、多校横向对比与流式概率评估。请问你的预估成绩、位次或意向专业是什么？</div>';
}
