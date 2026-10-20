// Presentation and input transport only. All simulation/rules run in Python.
const replayMemory=new WeakMap();
function mountResearch(root,result,current,send) {
  const q=id=>root.querySelector('#research-'+id), canvas=q('canvas'), ctx=canvas.getContext('2d');
  q('model').onchange=()=>send('research_model',q('model').value);
  q('form').onsubmit=e=>{
    e.preventDefault();const values=Object.fromEntries(new FormData(q('form')));
    if(q('custom-ships').checked){values.ships=[];root.querySelectorAll('[data-ship-row]').forEach(input=>{const i=Number(input.dataset.shipRow);(values.ships[i]??=[])[Number(input.dataset.shipCol)]=Number(input.value);});}
    send('research_run',values);
  };
  const key=JSON.stringify([result.version,result.config,current.formVersion]);
  const cache=replayMemory.get(root)||new Map();replayMemory.set(root,cache);
  const saved=cache.get(key);
  let at=saved?.at||0,playing=false,last=0;
  if(saved)q('speed').value=saved.speed;
  let layer=saved?.layer||'quantum_field';
  if(q('layer'))q('layer').value=layer;
  const save=()=>{cache.set(key,{at,speed:q('speed').value,layer});if(cache.size>8)cache.delete(cache.keys().next().value);};
  const duration=result.duration;
  q('time').max=duration;if(q('duration'))q('duration').textContent=duration;
  const [xmin,ymin,xmax,ymax]=result.bounds, scale=Math.min(900/(xmax-xmin),580/(ymax-ymin));
  const cx=(xmin+xmax)/2,cy=(ymin+ymax)/2, X=x=>500+(x-cx)*scale,Y=y=>340-(y-cy)*scale;
  const paths=result.labels.map((label,j)=>{const path=new Path2D();result.frames.forEach((frame,k)=>{const [x,y]=frame.p[j];k?path.lineTo(X(x),Y(y)):path.moveTo(X(x),Y(y));});return path;});
  const fieldCache=new Map();
  function fieldImages(name){
    if(fieldCache.has(name))return fieldCache.get(name);
    const images=result.frames.map(f=>{if(!f[name])return null;const c=document.createElement('canvas');c.width=c.height=40;const x=c.getContext('2d'),im=x.createImageData(40,40);
      const stops=[[15,38,85],[20,140,180],[80,215,175],[245,213,90],[250,105,45]];
      f[name].forEach((v,i)=>{const t=v/255*4,k=Math.min(3,Math.floor(t)),u=t-k;const rgb=stops[k].map((a,j)=>a+(stops[k+1][j]-a)*u);im.data.set([...rgb,Math.min(220,v*2.5)],i*4);});x.putImageData(im,0,0);return c;});fieldCache.set(name,images);return images;
  }

  function draw() {
    const i=Math.min(duration-1,Math.floor(at)),f=result.frames[i],g=result.frames[i+1],u=at-i;
    ctx.clearRect(0,0,1000,680);ctx.fillStyle='#08232f';ctx.fillRect(0,0,1000,680);
    const fields=layer==='none'?[]:fieldImages(layer);
    if(fields[i]){ctx.globalAlpha=1-u;ctx.drawImage(fields[i],X(xmin),Y(ymax),(xmax-xmin)*scale,(ymax-ymin)*scale);ctx.globalAlpha=u;ctx.drawImage(fields[i+1],X(xmin),Y(ymax),(xmax-xmin)*scale,(ymax-ymin)*scale);ctx.globalAlpha=1;}
    ctx.strokeStyle='#a4d6d315';ctx.lineWidth=1;
    for(let k=0;k<=10;k++){const x=xmin+(xmax-xmin)*k/10,y=ymin+(ymax-ymin)*k/10;ctx.beginPath();ctx.moveTo(X(x),Y(ymin));ctx.lineTo(X(x),Y(ymax));ctx.stroke();ctx.beginPath();ctx.moveTo(X(xmin),Y(y));ctx.lineTo(X(xmax),Y(y));ctx.stroke();}
    ctx.setLineDash([8,7]);ctx.strokeStyle='#cde1e788';for(const route of result.reference_paths||[]){ctx.beginPath();route.forEach(([x,y],j)=>j?ctx.lineTo(X(x),Y(y)):ctx.moveTo(X(x),Y(y)));ctx.stroke();}ctx.setLineDash([]);
    // Full excerpt paths keep the camera and spatial reference stable.
    paths.forEach((path,j)=>{ctx.strokeStyle=j<result.independent?'#c4e0d325':'#d8b38225';ctx.stroke(path);});
    (u===1?g:f).domains.forEach((d,j)=>{const next=g.domains[j];const same=u!==1 && next && JSON.stringify(f.groups[j])===JSON.stringify(g.groups[j]);const v=same?d.map((n,k)=>n+(next[k]-n)*u):d;ctx.strokeStyle='#e0b57b88';ctx.setLineDash([5,7]);ctx.beginPath();ctx.arc(X(v[0]),Y(v[1]),v[3]*scale,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.strokeStyle='#a4d8cc88';ctx.beginPath();ctx.arc(X(v[0]),Y(v[1]),v[2]*scale,0,Math.PI*2);ctx.stroke();});
    f.p.forEach((p,j)=>{
      const x=X(p[0]+(g.p[j][0]-p[0])*u),y=Y(p[1]+(g.p[j][1]-p[1])*u);
      const delta=(g.heading[j]-f.heading[j]+540)%360-180,angle=(f.heading[j]+delta*u)*Math.PI/180;
      const color=result.config.model==='fusion'&&j===0?'#f3e2a9':j<result.independent?'#a9dbd4':'#ddb684';
      ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.strokeStyle=color+'66';ctx.fillStyle=color+'09';
      ctx.beginPath();ctx.ellipse(0,result.config.model==='fusion'?-.6*result.a[j]*scale:0,result.b[j]*scale,result.a[j]*scale,0,0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.fillStyle=color;ctx.beginPath();if(result.static_indices?.includes(j)){ctx.moveTo(0,-7);ctx.lineTo(7,0);ctx.lineTo(0,7);ctx.lineTo(-7,0);}else{ctx.moveTo(0,-10);ctx.lineTo(5,7);ctx.lineTo(0,4);ctx.lineTo(-5,7);}ctx.closePath();ctx.fill();ctx.restore();
      ctx.fillStyle=color;ctx.font='12px system-ui';ctx.fillText(result.labels[j],x+9,y-10);
    });
    ctx.fillStyle='#a5bdc5';ctx.font='12px system-ui';ctx.fillText('N ↑',24,28);ctx.fillText('东 / 北 · m',24,655);
    const bar=10**Math.floor(Math.log10(180/scale));ctx.strokeStyle='#afc5c9';ctx.beginPath();ctx.moveTo(780,645);ctx.lineTo(780+bar*scale,645);ctx.stroke();ctx.fillText(bar+' m',780,635);
    // Risk is computed at integer seconds: do not fabricate interpolated decisions.
    const exact=result.frames[Math.min(duration,Math.floor(at))];q('risk').textContent=exact.risk.toFixed(3);q('distance').textContent=exact.distance.toFixed(1);
    if(q('team-distance'))q('team-distance').textContent=result.controlled && exact.team_distance!=null?'成员最近间距 '+exact.team_distance.toFixed(1)+' m':'';
    const pair=exact.nearest_pair;
    q('pair').textContent=pair.map(j=>result.labels[j]).join(' ↔ ');
    q('intrusion').textContent=result.controlled?(exact.team_avoiding?.some(Boolean)?'成员协调避让':exact.avoiding?.some(Boolean)?'外部避障':exact.recovering?.some(Boolean)?'恢复队形':'航线跟踪'):(exact.intrusion?'保护域侵入':'保护域外');q('intrusion').style.color=exact.intrusion?'#ffad8e':'#a9c6cb';
    if(result.controlled && exact.team_pairs?.length){ctx.strokeStyle='#9ce8e0';ctx.setLineDash([4,5]);for(const [a,b] of exact.team_pairs){ctx.beginPath();ctx.moveTo(X(f.p[a][0]),Y(f.p[a][1]));ctx.lineTo(X(f.p[b][0]),Y(f.p[b][1]));ctx.stroke();}ctx.setLineDash([]);}
    if(exact.intrusion){ctx.strokeStyle='#ff956e';ctx.lineWidth=2;ctx.setLineDash([6,5]);ctx.beginPath();pair.forEach((j,k)=>{const p=f.p[j],next=g.p[j],x=X(p[0]+(next[0]-p[0])*u),y=Y(p[1]+(next[1]-p[1])*u);k?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();ctx.setLineDash([]);ctx.lineWidth=1;}
    if(q('field-scale')){const maximum=result.field_scales?.[layer];q('field-scale').textContent=maximum?'0 — '+maximum.toFixed(3):'';q('field-peak').textContent=maximum?'当前峰值 '+Number(layer==='quantum_field'?exact.quantum_peak:exact.field_peak).toFixed(3):'';}
    q('clock').textContent=String(Math.floor(at+1e-7)).padStart(2,'0');q('time').value=at;
    q('state').textContent=at>=duration?'片段结束':playing?'播放中':'已暂停';q('play').textContent=playing?'暂停':'播放';
  }
  function queue(){cancelAnimationFrame(current.animationFrame);if(playing)current.animationFrame=requestAnimationFrame(tick);}
  function tick(now){if(!playing)return;const elapsed=Math.max(0,(now-last)/1000);last=now;
    if(elapsed<.5 && !document.hidden)at=Math.min(duration,at+elapsed*Number(q('speed').value));
    if(at>=duration)playing=false;draw();save();queue();
  }
  q('play').onclick=()=>{if(at>=duration)at=0;playing=!playing;last=performance.now();draw();save();queue();};
  q('replay').onclick=()=>{at=0;playing=true;last=performance.now();draw();save();queue();};
  q('time').oninput=()=>{at=Math.max(0,Math.min(duration,Number(q('time').value)));playing=false;draw();save();queue();};
  q('speed').onchange=()=>{last=performance.now();save();};
  if(q('layer'))q('layer').onchange=()=>{layer=q('layer').value;draw();save();};
  const visibility=()=>{last=performance.now();if(document.hidden){playing=false;draw();save();queue();}};
  document.addEventListener('visibilitychange',visibility);
  current.cleanupResearch=()=>{save();cancelAnimationFrame(current.animationFrame);document.removeEventListener('visibilitychange',visibility);};
  q('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='swarmeye-research-'+result.config.model+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  draw();last=performance.now();
}
// Passwords and derived keys never enter component trigger values or storage.
const vaultAAD = new TextEncoder().encode('SwarmEye encrypted record v1');
const vaultIterations = 600000;
const toBase64 = bytes => {
  let text='';for(let i=0;i<bytes.length;i+=32768)text+=String.fromCharCode(...bytes.subarray(i,i+32768));
  return btoa(text);
};
const fromBase64 = value => Uint8Array.from(atob(value), c=>c.charCodeAt(0));
async function vaultKey(password,salt,usage) {
  if(!globalThis.crypto?.subtle)throw new Error('当前浏览器不支持加密，请使用 HTTPS 或本机地址访问。');
  const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:vaultIterations,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,[usage]);
}
async function sealRecord(raw,password) {
  const salt=crypto.getRandomValues(new Uint8Array(16)), nonce=crypto.getRandomValues(new Uint8Array(12));
  const key=await vaultKey(password,salt,'encrypt');
  const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv:nonce,additionalData:vaultAAD,tagLength:128},key,new TextEncoder().encode(raw));
  return JSON.stringify({format:'swarmeye-encrypted',version:1,algorithm:'AES-256-GCM',kdf:'PBKDF2-SHA256',iterations:vaultIterations,salt:toBase64(salt),nonce:toBase64(nonce),data:toBase64(new Uint8Array(encrypted))});
}
async function unsealRecord(envelope,password) {
  if(envelope.version!==1 || envelope.algorithm!=='AES-256-GCM' || envelope.kdf!=='PBKDF2-SHA256' || envelope.iterations!==vaultIterations)throw new Error('加密记录格式不兼容。');
  try {
    const salt=fromBase64(envelope.salt), nonce=fromBase64(envelope.nonce), bytes=fromBase64(envelope.data);
    if(salt.length!==16 || nonce.length!==12 || bytes.length<16 || bytes.length>2000016)throw new Error('size');
    const key=await vaultKey(password,salt,'decrypt');
    const raw=await crypto.subtle.decrypt({name:'AES-GCM',iv:nonce,additionalData:vaultAAD,tagLength:128},key,bytes);
    return new TextDecoder('utf-8',{fatal:true}).decode(raw);
  }catch(error){throw new Error('密码不正确，或加密文件已损坏；请检查后重试。');}
}
function passwordDialog(root,confirm,submit) {
  const dialog=document.createElement('dialog');dialog.className='vault-dialog';
  dialog.innerHTML=`<form method="dialog"><h2>${confirm?'加密保存演练记录':'解锁演练记录'}</h2><p>${confirm?'密码只在当前浏览器用于加密，不会传给服务器。请自行保管，平台无法找回。':'密码在当前浏览器解密；确认后将恢复的演练记录交给服务器校验。'}</p><label for="vault-password">${confirm?'设置密码（至少 12 个字符）':'存档密码'}</label><input id="vault-password" type="password" autocomplete="${confirm?'new-password':'off'}" minlength="${confirm?12:1}" maxlength="128" required>${confirm?'<label for="vault-confirm">再次输入密码</label><input id="vault-confirm" type="password" autocomplete="new-password" minlength="12" maxlength="128" required>':''}<p class="vault-error" role="alert"></p><div class="actions"><button type="submit" class="btn primary">${confirm?'加密并下载':'解密并恢复'}</button><button type="button" class="btn secondary vault-cancel">取消</button></div></form>`;
  root.appendChild(dialog);dialog.showModal();
  const close=()=>{dialog.querySelectorAll('input').forEach(input=>input.value='');dialog.close();dialog.remove();};
  dialog.querySelector('.vault-cancel').onclick=close;
  dialog.addEventListener('cancel',()=>dialog.remove());
  dialog.querySelector('form').onsubmit=async e=>{
    e.preventDefault();e.stopPropagation();
    const input=dialog.querySelector('#vault-password'), again=dialog.querySelector('#vault-confirm');
    if(again && input.value!==again.value){dialog.querySelector('.vault-error').textContent='两次输入的密码不一致。';return;}
    const buttons=dialog.querySelectorAll('button');buttons.forEach(b=>b.disabled=true);
    try{await submit(input.value);close();}catch(error){dialog.querySelector('.vault-error').textContent=error.message;buttons.forEach(b=>b.disabled=false);}
  };
}
const instances = new WeakMap();
function showLoading(root,title) {
  root.querySelector('.loading-overlay')?.remove();
  const overlay=document.createElement('div');overlay.className='loading-overlay';
  overlay.setAttribute('role','status');overlay.setAttribute('aria-live','polite');
  overlay.innerHTML='<div class="loading-card"><div class="loading-orbit" aria-hidden="true"><i></i></div><strong></strong><p>正在准备，请稍候</p><div class="loading-track" aria-hidden="true"><i></i></div></div>';
  overlay.querySelector('strong').textContent=title;root.appendChild(overlay);
  return setTimeout(()=>{const p=overlay.querySelector('p');if(p)p.textContent='仍在等待云端响应，请保持页面打开';},8000);
}

export default function paint(component) {
  const {data, parentElement, setTriggerValue} = component;
  const root = parentElement.querySelector('#swarmeye-root');
  if (!root || !data) return;
  const prior = instances.get(parentElement) || {};
  prior.cleanupResearch?.();
  clearTimeout(prior.timer);
  clearTimeout(prior.loadingTimer);
  root.querySelector('.loading-overlay')?.remove();
  cancelAnimationFrame(prior.animationFrame);
  const pageChanged = prior.page !== data.page;
  const motionAttrs=['transform','points','cx','cy','r'];
  const motion=new Map([...root.querySelectorAll('[data-motion]')].map(el=>[el.dataset.motion,Object.fromEntries(motionAttrs.filter(a=>el.hasAttribute(a)).map(a=>[a,el.getAttribute(a)]))]));
  const focused = root.getRootNode().activeElement;
  const focusId = !pageChanged && focused?.id;
  const selection = focused && typeof focused.selectionStart === 'number' ? [focused.selectionStart,focused.selectionEnd] : null;
  // Preserve unsent form drafts through playback and validation errors.
  const drafts = {};
  if (!pageChanged && prior.run === data.run && prior.formVersion === data.form_version) {
    root.querySelectorAll('form').forEach(form => {
      if(form.closest('.vault-dialog'))return;
      drafts[form.id] = Object.fromEntries(new FormData(form));
    });
  }
  // Retain DOM nodes, focus and the expensive textured shell during playback.
  const patch = (old, next) => {
    if(old.isEqualNode(next))return;
    if (old.nodeType !== next.nodeType || old.nodeName !== next.nodeName) {old.replaceWith(next.cloneNode(true));return;}
    if (old.nodeType !== 1) {if(old.nodeValue!==next.nodeValue) old.nodeValue=next.nodeValue;return;}
    for(const a of [...old.attributes]) if(!next.hasAttribute(a.name) && !(old.tagName==='DETAILS' && a.name==='open')) old.removeAttribute(a.name);
    for(const a of next.attributes) if(old.getAttribute(a.name)!==a.value) old.setAttribute(a.name,a.value);
    const children=[...old.childNodes], incoming=[...next.childNodes];
    incoming.forEach((child,i)=>children[i]?patch(children[i],child):old.appendChild(child.cloneNode(true)));
    children.slice(incoming.length).forEach(child=>child.remove());
    if(old.tagName==='INPUT' && old.type!=='file') {old.value=next.value;old.checked=next.checked;}
    if(old.tagName==='SELECT' || old.tagName==='TEXTAREA') old.value=next.value;
  };
  if (!pageChanged && prior.run===data.run && root.firstElementChild) {
    const template=document.createElement('template');template.innerHTML=data.html;
    patch(root.firstElementChild,template.content.firstElementChild);
  } else root.innerHTML=data.html;
  // Interpolate boats, domains and protection circles on the same clock.
  // Never animate a manual seek or a change between truth and observations.
  const tweens=[];
  if (!pageChanged && data.page==='workspace' && prior.run===data.run && data.plot_mode===prior.plotMode && data.time>=prior.time && data.time-prior.time<=1 && (data.localFrame || prior.animating) && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const numeric=/[-+]?\d*\.?\d+(?:e[-+]?\d+)?/gi;
    root.querySelectorAll('[data-motion]').forEach(el=>{
      const old=motion.get(el.dataset.motion);if(!old)return;
      motionAttrs.forEach(attr=>{
        const target=el.getAttribute(attr), source=old[attr];
        if(!target || !source || target===source)return;
        let from=(source.match(numeric)||[]).map(Number), to=(target.match(numeric)||[]).map(Number);
        if(attr==='points' && el.dataset.motion.startsWith('trace-') && from.length>=2){while(from.length<to.length)from.push(...from.slice(-2));}
        if(from.length!==to.length || !from.length)return;
        if(el.dataset.motion.startsWith('heading-') && attr==='transform') from[0]=to[0]-((to[0]-from[0]+540)%360-180);
        tweens.push({el,attr,target,from,to});el.setAttribute(attr,source);
      });
    });
  }
  Object.entries(drafts).forEach(([id, values]) => {
    const form = root.querySelector('#'+id);
    if (!form) return;
    Object.entries(values).forEach(([name, value]) => { if (form.elements[name]) form.elements[name].value = value; });
  });
  let busy = false;
  const send = (type, value = '') => {
    if (busy) return;
    busy = true;
    root.setAttribute('aria-busy','true');
    current.loadingTimer=showLoading(root,type==='nav'?'正在切换页面':type.startsWith('research_')?'正在计算仿真':'正在更新');
    cancelAnimationFrame(current.animationFrame);
    root.querySelectorAll('button').forEach(button => {button.disabled=true;});
    clearTimeout(current.timer);
    setTriggerValue('action', {type, value, at:data.time, run:data.run});
  };
  const download = (content, suffix, type) => {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const a = document.createElement('a');
    a.href = url; a.download = `swarmeye-${data.run || 'record'}.${suffix}`;
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  root.onclick = e => {
    const target = e.target.closest('[data-action]');
    if (!target || target.disabled) return;
    const action = target.dataset.action;
    if(action==='download_encrypted'){
      if(!globalThis.crypto?.subtle)return send('client_error','加密功能需要新版浏览器及 HTTPS 连接。');
      if(data.playing)return send('client_error','请先暂停回放，再加密保存当前时刻。');
      passwordDialog(root,true,password=>{current.pendingSecret=password;send('download_encrypted');});return;
    }
    const value = action === 'preview' ? Object.fromEntries(new FormData(root.querySelector('#scenario-form'))) : target.dataset.value;
    send(action, value);
  };
  root.querySelectorAll('form').forEach(form => {
    if(form.closest('.vault-dialog'))return;
    form.onsubmit = e => {
      e.preventDefault();
      send(form.id === 'research-form' ? 'research_run' : form.id === 'scenario-form' ? 'start' : form.id === 'decision-form' ? 'decide' : 'review', Object.fromEntries(new FormData(form)));
    };
    // Stop playback before editing, without dropping the first character or draft.

  });
  root.querySelectorAll('.parameter input').forEach(input => {
    input.oninput=()=> {input.closest('label').querySelector('output').textContent=input.value+' '+input.dataset.unit;};
    input.oninput();
  });
  for (const [id,action] of [['play-speed','speed'],['compare-a','compare_a'],['compare-b','compare_b'],['compare-time','compare_time']]) {
    const el=root.querySelector('#'+id);
    if(el) el.onchange=()=>send(action,el.value);
  }
  const time = root.querySelector('#timeline');
  if (time) time.onchange = () => send('seek', Math.max(Number(time.dataset.min),Number(time.value)));
  const review = root.querySelector('#review-time');
  if (review) review.onchange = () => send('review_time', Number(review.value));
  const upload = root.querySelector('#import-file');
  if (upload) upload.onchange = async () => {
    const file = upload.files[0];
    if (!file) return;
    if (file.size > 2800000) return send('client_error','文件过大，普通记录上限 2 MB，加密记录上限 2.8 MB');
    const raw=await file.text();let parsed;
    try{parsed=JSON.parse(raw);}catch(error){return send('client_error','无法读取记录，请选择导出的 JSON 或 .swarm 文件。');}
    if(parsed?.format==='swarmeye-encrypted'){
      passwordDialog(root,false,async password=>{const restored=await unsealRecord(parsed,password);send('restore',restored);});
    }else send('restore',raw);
  };
  const current = {page:data.page, run:data.run, formVersion:data.form_version, timer:null,time:data.time,focus:data.focus,plotMode:data.plot_mode,animationFrame:null,animating:false,downloadId:prior.downloadId,pendingSecret:prior.run===data.run?prior.pendingSecret:null};
  root.removeAttribute('aria-busy');
  if (data.download && data.download.id!==prior.downloadId) {
    current.downloadId=data.download.id;
    if(data.download.suffix==='swarm'){
      const password=current.pendingSecret;current.pendingSecret=null;
      if(password)sealRecord(data.download.content,password).then(content=>download(content,'swarm','application/json;charset=utf-8')).catch(()=>send('client_error','加密失败，请重新设置密码并保存。'));
      else send('client_error','密码已失效，请重新点击加密保存。');
    }else download(data.download.content,data.download.suffix,data.download.suffix==='json'?'application/json;charset=utf-8':'text/html;charset=utf-8');
  }
  if (focusId && prior.formVersion === data.form_version) {
    const nextFocus = root.querySelector('#'+CSS.escape(focusId));
    if (nextFocus) {
      nextFocus.focus({preventScroll:true});
      if (selection && typeof nextFocus.setSelectionRange === 'function') nextFocus.setSelectionRange(...selection);
    }
  }
  if (data.playing && data.frames?.length) {
    current.timer=setTimeout(()=>{
      const [frame,...rest]=data.frames;
      paint({...component,data:{...data,html:frame.html,time:frame.time,frames:rest,localFrame:true,playing:!frame.stop}});
      if(frame.stop || !rest.length) {
        clearTimeout(instances.get(parentElement)?.timer);
        root.setAttribute('aria-busy','true');
        root.querySelectorAll('button').forEach(button=>{button.disabled=true;});
        setTriggerValue('action',{type:'buffer_end',at:frame.time,run:data.run});
      }
    },1000/data.speed);
  }
  if(data.research) mountResearch(root,data.research,current,send);
  instances.set(parentElement,current);
  if(data.research_zip){
    root.setAttribute('aria-busy','true');
    current.loadingTimer=showLoading(root,'正在准备回放');
    (async()=>{
      try {
        const bytes=Uint8Array.from(atob(data.research_zip),c=>c.charCodeAt(0));
        const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
        const research=JSON.parse(await new Response(stream).text());
        if(instances.get(parentElement)!==current || busy)return;
        clearTimeout(current.loadingTimer);root.querySelector('.loading-overlay')?.remove();root.removeAttribute('aria-busy');
        mountResearch(root,research,current,send);
      } catch(error){
        if(instances.get(parentElement)!==current || busy)return;
        clearTimeout(current.loadingTimer);root.querySelector('.loading-overlay')?.remove();root.removeAttribute('aria-busy');
        const warning=document.createElement('div');warning.className='notice';warning.setAttribute('role','alert');warning.textContent='回放加载失败，请刷新重试或使用新版浏览器。';(root.querySelector('.site')||root).prepend(warning);
      }
    })();
  }

  if(data.frames_zip && data.playing){
    (async()=>{
      try{
        const bytes=Uint8Array.from(atob(data.frames_zip),c=>c.charCodeAt(0));
        const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
        const frames=JSON.parse(await new Response(stream).text());
        if(instances.get(parentElement)===current && !busy) paint({...component,data:{...data,frames_zip:null,frames}});
      }catch(error){if(instances.get(parentElement)===current && !busy)send('client_error','回放缓冲加载失败，请使用新版浏览器重试。');}
    })();
  }
  if(tweens.length){
    const start=performance.now(), duration=1000/data.speed;
    current.animating=true;
    const animate=now=>{
      const progress=Math.min(1,(now-start)/duration);
      tweens.forEach(({el,attr,target,from,to})=>{
        let i=0;
        el.setAttribute(attr,target.replace(/[-+]?\d*\.?\d+(?:e[-+]?\d+)?/gi,()=>String(from[i]+(to[i]-from[i++])*progress)));
      });
      if(progress<1)current.animationFrame=requestAnimationFrame(animate);else current.animating=false;
    };
    current.animationFrame=requestAnimationFrame(animate);
  }
  if (pageChanged) root.scrollIntoView({block:'start',behavior:'instant'});
  return () => {instances.get(parentElement)?.cleanupResearch?.();clearTimeout(instances.get(parentElement)?.loadingTimer);cancelAnimationFrame(instances.get(parentElement)?.animationFrame);clearTimeout(instances.get(parentElement)?.timer);instances.delete(parentElement);};
}
