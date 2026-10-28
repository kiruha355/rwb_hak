// Inject into html_preview only, after the app script. No external dependencies.
(async () => {
  const results = [];
  const check = (name, condition) => {
    results.push({name, pass: Boolean(condition)});
    if (!condition) throw Error('QA failed: ' + name);
  };
  const change = (id, value) => {$(id).value = value; $(id).dispatchEvent(new Event('change'));};
  const initial = structuredClone(data);
  try {
    check('demo is explicitly synthetic', data.manifest.mode === 'demo' && data.orders.length === 24);
    check('known zero differs from unknown money', money('0') !== money(null) && money(null)==='Неизвестно');
    check('exact decimal sum before display', sumDecimal(['0.1','0.20','-0.001']) === '0.299');
    check('source month chart exposes keyboard controls', document.querySelector('g[role="button"][tabindex="0"]'));
    change('state',JSON.stringify('SP'));
    check('state filter selects 6 orders', visible.length === 6 && visible.every(o=>o.customer_state==='SP'));
    reset(); change('from','2025-01-01'); change('to','2025-01-31');
    check('date filters select purchase month', visible.length === 6);
    reset();
    document.querySelector('g[data-kind="month"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    check('keyboard month drill selects 6 orders', visible.length === 6 && drill.kind === 'month');
    $('clear-drill').click();
    check('clear chart selection restores 24 orders', visible.length === 24);
    $('tab-service').focus();
    $('tab-service').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
    check('arrow key selects sales and moves focus', tab === 'sales' && document.activeElement === $('tab-sales'));
    check('incomplete revenue stays unknown', $('metrics').textContent.includes('Неизвестно'));
    document.querySelector('[data-kind="seller"]').click();
    check('seller drill contains participating orders', drill.kind==='seller' && visible.every(o=>(itemMap.get(o.order_id)||[]).some(i=>i.seller_id===drill.value)));
    $('clear-drill').click();
    document.querySelector('[data-order]').focus(); document.querySelector('[data-order]').click();
    check('order dialog opens with original dates', $('order-dialog').open && $('order-detail').textContent.includes('Передан в доставку'));
    $('close-dialog').click();
    check('dialog closes and restores trigger focus', !$('order-dialog').open && document.activeElement?.hasAttribute('data-order'));
    $('tab-quality').click();
    check('quality keeps unknown categories distinct', $('story').textContent.includes('Известная категория без перевода'));
    $('tab-service').click(); change('from','2025-04-01');
    check('uncompleted tail has no late percentage', $('metrics').textContent.includes('Нет данных') && visible.length===6);
    reset(); change('from','2026-01-01'); change('to','2026-02-01');
    check('empty slice offers filter recovery', visible.length===0 && $('orders-body').textContent.includes('Измените период'));
    const empty = {...structuredClone(initial), orders:[],items:[],reviews:[]};
    load(empty);
    check('valid empty source is distinct from load error', visible.length===0 && $('error').hidden);
    load(initial);
    let before = data;
    try {load({...initial,months:[null]});} catch (_) {}
    check('invalid calendar cannot replace loaded source', data===before);
    try {load({...initial,items:[]});} catch (_) {}
    check('missing item export cannot become zero revenue', data===before);
    const undated=structuredClone(initial);undated.orders[0].order_purchase_timestamp=null;load(undated);
    check('bounded date filter excludes unknown purchase dates', visible.length===23);
    $('all-snapshot').click();check('whole snapshot includes unknown purchase dates', visible.length===24);load(initial);
    before=data;
    const f = new File(['{"manifest": {"schema_version": 8}}'],'bad.json',{type:'application/json'});
    await $('file-input').onchange({target:{files:[f],value:'bad.json'}});
    check('bad file reports error and preserves data', !$('error').hidden && data===before);
    const goodFile = new File([JSON.stringify(initial)],'model.json',{type:'application/json'});
    await $('file-input').onchange({target:{files:[goodFile],value:'model.json'}});
    check('file input reads JSON without fetch or server', $('error').hidden && data.orders.length===24);
    $('import-button').focus();
    check('primary input is keyboard focusable', document.activeElement===$('import-button'));
    check('document fits viewport; table scroll is local', document.documentElement.scrollWidth <= window.innerWidth);
    console.log('CAPIBARA_QA ' + JSON.stringify({width:window.innerWidth,passed:results.filter(r=>r.pass).length,total:results.length,failed:results.filter(r=>!r.pass).map(r=>r.name)}));
  } catch (error) {
    console.error(error.message); console.error('CAPIBARA_QA ' + JSON.stringify({width:window.innerWidth,passed:results.filter(r=>r.pass).length,total:results.length,failed:results.filter(r=>!r.pass).map(r=>r.name),error:error.message}));
  } finally {load(initial);$('tab-service').click();window.scrollTo(0,0);}
})();
