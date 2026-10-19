// Presentation and input transport only. All simulation/rules run in Python.
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
export default function paint(component) {
  const {data, parentElement, setTriggerValue} = component;
  const root = parentElement.querySelector('#swarmeye-root');
  if (!root || !data) return;
  const prior = instances.get(parentElement) || {};
  clearTimeout(prior.timer);
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
    form.onsubmit = e => {
      e.preventDefault();
      send(form.id === 'scenario-form' ? 'start' : form.id === 'decision-form' ? 'decide' : 'review', Object.fromEntries(new FormData(form)));
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
  instances.set(parentElement,current);
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
  return () => {cancelAnimationFrame(instances.get(parentElement)?.animationFrame);clearTimeout(instances.get(parentElement)?.timer);instances.delete(parentElement);};
}
