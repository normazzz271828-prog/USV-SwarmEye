// Presentation and input transport only. All simulation/rules run in Python.
const instances = new WeakMap();
export default function(component) {
  const {data, parentElement, setTriggerValue} = component;
  const root = parentElement.querySelector('#swarmeye-root');
  if (!root || !data) return;
  const prior = instances.get(parentElement) || {};
  clearTimeout(prior.timer);
  const pageChanged = prior.page !== data.page;
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
  Object.entries(drafts).forEach(([id, values]) => {
    const form = root.querySelector('#'+id);
    if (!form) return;
    Object.entries(values).forEach(([name, value]) => { if (form.elements[name]) form.elements[name].value = value; });
  });
  let busy = false;
  const send = (type, value = '') => {
    if (busy) return;
    busy = true;
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
    if (action === 'download_json') return download(data.export_json, 'json', 'application/json;charset=utf-8');
    if (action === 'download_html') return download(data.export_html, 'html', 'text/html;charset=utf-8');
    const value = action === 'start' ? root.querySelector('input[name=delay]:checked').value : target.dataset.value;
    send(action, value);
  };
  root.querySelectorAll('form').forEach(form => {
    form.onsubmit = e => {
      e.preventDefault();
      send(form.id === 'decision-form' ? 'decide' : 'review', Object.fromEntries(new FormData(form)));
    };
    // Stop playback before editing, without dropping the first character or draft.
    form.onfocusin = () => { if (data.playing) send('pause'); };
  });
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
  const current = {page:data.page, run:data.run, formVersion:data.form_version, timer:null};
  if (focusId && prior.formVersion === data.form_version) {
    const nextFocus = root.querySelector('#'+CSS.escape(focusId));
    if (nextFocus) {
      nextFocus.focus({preventScroll:true});
      if (selection && typeof nextFocus.setSelectionRange === 'function') nextFocus.setSelectionRange(...selection);
    }
  }
  if (data.playing) current.timer = setTimeout(() => send('tick'), 750);
  instances.set(parentElement,current);
  if (pageChanged) root.scrollIntoView({block:'start',behavior:'instant'});
  return () => {clearTimeout(instances.get(parentElement)?.timer);instances.delete(parentElement);};
}
