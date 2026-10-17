// Presentation and input transport only. All simulation/rules run in Python.
const instances = new WeakMap();
export default function(component) {
  const {data, parentElement, setTriggerValue} = component;
  const root = parentElement.querySelector('#swarmeye-root');
  if (!root || !data) return;
  const prior = instances.get(parentElement) || {};
  clearTimeout(prior.timer);
  const pageChanged = prior.page !== data.page;
  const ships = new Map([...root.querySelectorAll('.ship-marker')].map(el => [el.dataset.ship,{x:Number(el.dataset.x),y:Number(el.dataset.y)}]));
  const focused = root.getRootNode().activeElement;
  const focusId = !pageChanged && focused?.id;
  const selection = focused && typeof focused.selectionStart === 'number' ? [focused.selectionStart,focused.selectionEnd] : null;
  // Preserve unsent form drafts through playback and validation errors.
  const drafts = {};
  if (!pageChanged && prior.run === data.run && prior.formVersion === data.form_version) {
    root.querySelectorAll('form').forEach(form => {
      drafts[form.id] = Object.fromEntries(new FormData(form));
    });
  }
  root.innerHTML = data.html;
  if (!pageChanged && data.page==='workspace' && prior.run===data.run && data.time>prior.time && data.time-prior.time<=8 && prior.focus===data.focus && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    root.querySelectorAll('.ship-marker').forEach(el => {
      const old=ships.get(el.dataset.ship);
      if (old) el.animate([{transform:`translate(${old.x}px,${old.y}px)`},{transform:`translate(${el.dataset.x}px,${el.dataset.y}px)`}],{duration:350,easing:'linear'});
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
    setTriggerValue('action', {type, value});
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
    const value = action === 'preview' ? Object.fromEntries(new FormData(root.querySelector('#scenario-form'))) : target.dataset.value;
    send(action, value);
  };
  root.querySelectorAll('form').forEach(form => {
    form.onsubmit = e => {
      e.preventDefault();
      send(form.id === 'scenario-form' ? 'start' : form.id === 'decision-form' ? 'decide' : 'review', Object.fromEntries(new FormData(form)));
    };
    // Stop playback before editing, without dropping the first character or draft.
    form.onfocusin = () => { if (data.playing) send('pause'); };
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
    if (file.size > 2000000) return send('client_error','文件不能超过 2 MB');
    send('restore',await file.text());
  };
  const current = {page:data.page, run:data.run, formVersion:data.form_version, timer:null,time:data.time,focus:data.focus,downloadId:prior.downloadId};
  root.removeAttribute('aria-busy');
  if (data.download && data.download.id!==prior.downloadId) {
    current.downloadId=data.download.id;
    download(data.download.content,data.download.suffix,data.download.suffix==='json'?'application/json;charset=utf-8':'text/html;charset=utf-8');
  }
  if (focusId && prior.formVersion === data.form_version) {
    const nextFocus = root.querySelector('#'+CSS.escape(focusId));
    if (nextFocus) {
      nextFocus.focus({preventScroll:true});
      if (selection && typeof nextFocus.setSelectionRange === 'function') nextFocus.setSelectionRange(...selection);
    }
  }
  if (data.playing) current.timer = setTimeout(() => send('tick'), 1000);
  instances.set(parentElement,current);
  if (pageChanged) root.scrollIntoView({block:'start',behavior:'instant'});
  return () => {clearTimeout(instances.get(parentElement)?.timer);instances.delete(parentElement);};
}
