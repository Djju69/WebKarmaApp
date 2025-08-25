(function(){
  'use strict';

  const STORAGE_KEY = 'ks_coupons_v1';

  // State
  let coupons = load();
  let sort = { by:'title', dir:'asc' };
  let filter = { q:'', status:'' };

  // Elements
  const $ = s=>document.querySelector(s);
  const $cabQrHtml = s=>Array.from(document.querySelectorAll(s));
  const tbody = #couponsTbody;
  const emptyState = #emptyState;

  const btnAdd = #btnAddCoupon;
  const btnExport = #btnExport;
  const importInput = #importCsvInput;

  // form
  const editModal = #editModal;
  const form = #couponForm;
  const f = {
    id: #id,
    title: #title,
    code: #code,
    discountType: #discountType,
    value: #value,
    start: #start,
    end: #end,
    maxUses: #maxUses,
    minPurchase: #minPurchase,
    published: #published,
    description: #description,
  };
  const btnGenCode = #btnGenCode;
  const btnSave = #btnSave;

  // filters
  const searchInput = #searchInput;
  const statusFilter = #statusFilter;

  // qr modal
  const qrModal = #qrModal;
  const qrBox = #qrBox;
  const qrTitle = #qrTitle;
  const qrCodeText = #qrCodeText;
  const btnCopyLink = #btnCopyLink;
  const btnDownloadPng = #btnDownloadPng;
  const btnPrint = #btnPrint;

  // ====== Helpers ======
  function uid(){ return 'id_'+Math.random().toString(36).slice(2)+Date.now().toString(36); }
  function escapeHtml(str=''){ return String(str).replace(/[&<>\"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }
  function todayStr(d=new Date()){ const z=n=>String(n).padStart(2,'0'); return d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate()); }

  function parseDate(v){
    if (!v) return null;
    const d = new Date(v+'T00:00:00');
    return isNaN(d.getTime()) ? null : d;
  }

  function statusOf(c){
    if (!c.published) return 'Р С›РЎвЂљР С”Р В»РЎР‹РЎвЂЎР ВµР Р…Р С•';
    const now = new Date();
    const s = parseDate(c.start), e = parseDate(c.end);
    if (s && now < s) return 'Р вЂ”Р В°Р С—Р В»Р В°Р Р…Р С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С•';
    if (e && now > new Date(e.getTime()+24*3600*1000-1)) return 'Р ВРЎРѓРЎвЂљРЎвЂР С”';
    if (c.maxUses && Number(c.used||0) >= Number(c.maxUses)) return 'Р вЂєР С‘Р СР С‘РЎвЂљ Р С‘РЎРѓРЎвЂЎР ВµРЎР‚Р С—Р В°Р Р…';
    return 'Р С’Р С”РЎвЂљР С‘Р Р†Р ВµР Р…';
  }

  function statusClass(s){
    const x = (s||'').toLowerCase();
    if (x.includes('Р В°Р С”РЎвЂљР С‘Р Р†')) return 'ok';
    if (x.includes('Р С—Р В»Р В°Р Р…'))  return 'warn';
    if (x.includes('Р С‘РЎРѓРЎвЂЎР ВµРЎР‚')) return 'warn';
    if (x.includes('Р С‘РЎРѓРЎвЂљРЎвЂ') || x.includes('Р С‘РЎРѓРЎвЂљР ВµР С”')) return 'muted';
    if (x.includes('Р С•РЎвЂљР С”Р В»РЎР‹РЎвЂЎ')) return 'muted';
    return 'muted';
  }

  // ====== Storage ======
  function load(){
    try{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return demo();
      const arr = JSON.parse(raw);
      return Array.isArray(arr)?arr:demo();
    }catch(e){ return demo(); }
  }
  function save(){ localStorage.setItem(STORAGE_KEY, JSON.stringify(coupons)); }
  function demo(){
    return [
      { id:uid(), title:'-15% Р Р…Р В° Р С”Р С•РЎвЂћР Вµ', code:'COFFEE15', discountType:'percent', value:15, start:todayStr(), end:'', maxUses:0, used:0, minPurchase:0, published:true, description:'' },
      { id:uid(), title:'200 РІвЂљР… Р Р…Р В° Р С•Р В±Р ВµР Т‘', code:'LUNCH200', discountType:'amount', value:200, start:todayStr(), end:'', maxUses:100, used:3, minPurchase:800, published:true, description:'' },
      { id:uid(), title:'-10% РЎвЂћР С‘РЎвЂљР Р…Р ВµРЎРѓ', code:'FIT10', discountType:'percent', value:10, start:'', end:'', maxUses:0, used:0, minPurchase:0, published:false, description:'' },
    ];
  }

  // ====== Render ======
  function render(){
    // filter
    let rows = coupons.filter(c=>{
      if (filter.q){
        const t = (c.title+' '+c.code).toLowerCase();
        if (!t.includes(filter.q)) return false;
      }
      if (filter.status){
        if (statusOf(c) !== filter.status) return false;
      }
      return true;
    });

    // sort
    rows.sort((a,b)=>{
      const dir = (sort.dir==='asc')?1:-1;
      let va, vb;
      switch (sort.by){
        case 'title': va=a.title||''; vb=b.title||''; break;
        case 'code': va=a.code||''; vb=b.code||''; break;
        case 'discountType': va=a.discountType||''; vb=b.discountType||''; break;
        case 'value': va=Number(a.value||0); vb=Number(b.value||0); break;
        case 'status': va=statusOf(a); vb=statusOf(b); break;
        case 'usage': va=Number(a.used||0); vb=Number(b.used||0); break;
        case 'period':
          va=(a.start||'')+'|'+(a.end||''); vb=(b.start||'')+'|'+(b.end||''); break;
        default: va=''; vb='';
      }
      return (va>vb?1:va<vb?-1:0)*dir;
    });

    // draw
    tbody.innerHTML='';
    rows.forEach(c=>{
      const st = statusOf(c);
      const tr = document.createElement('tr');
      tr.innerHTML = 
        <td></td>
        <td><code></code></td>
        <td></td>
        <td></td>
        <td> РІР‚вЂќ </td>
        <td></td>
        <td><span class="status "></span></td>
        <td class="row-actions">
          <button class="btn btn-xs" data-qr="">QR</button>
          <button class="btn btn-xs" data-edit="">Р ВР В·Р С.</button>
          <button class="btn btn-xs btn-danger" data-del="">Р Р€Р Т‘Р В°Р В».</button>
        </td>
      ;
      tbody.appendChild(tr);
    });

    emptyState.style.display = rows.length ? 'none' : 'block';
  }

  // ====== Modals ======
  function openModal(m){ m.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; }
  function closeModal(m){ m.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }

  editModal.addEventListener('click', e=>{ if(e.target.hasAttribute('data-close')) closeModal(editModal); });
  qrModal.addEventListener('click',  e=>{ if(e.target.hasAttribute('data-close')) closeModal(qrModal);  });

  // ====== CRUD ======
  function toForm(c){
    f.id.value = c.id||'';
    f.title.value = c.title||'';
    f.code.value = c.code||'';
    f.discountType.value = c.discountType||'percent';
    f.value.value = c.value ?? '';
    f.start.value = c.start||'';
    f.end.value = c.end||'';
    f.maxUses.value = c.maxUses ?? 0;
    f.minPurchase.value = c.minPurchase ?? 0;
    f.published.checked = !!c.published;
    f.description.value = c.description||'';
  }
  function fromForm(){
    const title = f.title.value.trim();
    const code  = f.code.value.trim().toUpperCase();
    if (!title){ alert('Р вЂ™Р Р†Р ВµР Т‘Р С‘РЎвЂљР Вµ Р Р…Р В°Р В·Р Р†Р В°Р Р…Р С‘Р Вµ'); f.title.focus(); return null; }
    if (!code){ alert('Р вЂ™Р Р†Р ВµР Т‘Р С‘РЎвЂљР Вµ Р С”Р С•Р Т‘'); f.code.focus(); return null; }
    const value = f.value.value===''?null:Number(f.value.value);
    if (value===null || isNaN(value) || value<=0){ alert('Р СњР ВµР Р†Р ВµРЎР‚Р Р…Р С•Р Вµ Р В·Р Р…Р В°РЎвЂЎР ВµР Р…Р С‘Р Вµ РЎРѓР С”Р С‘Р Т‘Р С”Р С‘'); f.value.focus(); return null; }
    const start = f.start.value.trim();
    const end   = f.end.value.trim();
    if (start && end && new Date(start) > new Date(end)){ alert('Р вЂќР В°РЎвЂљР В° Р Р…Р В°РЎвЂЎР В°Р В»Р В° Р С—Р С•Р В·Р В¶Р Вµ Р Т‘Р В°РЎвЂљРЎвЂ№ Р С•Р С”Р С•Р Р…РЎвЂЎР В°Р Р…Р С‘РЎРЏ'); return null; }
    const obj = {
      id: f.id.value || uid(),
      title, code,
      discountType: f.discountType.value || 'percent',
      value,
      start, end,
      maxUses: Number(f.maxUses.value||0),
      used: coupons.find(x=>x.id===f.id.value)?.used || 0,
      minPurchase: Number(f.minPurchase.value||0),
      published: f.published.checked,
      description: f.description.value.trim(),
      updatedAt: new Date().toISOString(),
      createdAt: coupons.find(x=>x.id===f.id.value)?.createdAt || new Date().toISOString(),
    };
    return obj;
  }

  btnAdd.addEventListener('click', ()=>{
    form.reset();
    f.id.value='';
    f.discountType.value='percent';
    f.value.value='';
    f.start.value=todayStr();
    openModal(editModal);
  });

  btnGenCode.addEventListener('click', ()=>{
    const abc='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let out=''; for(let i=0;i<8;i++) out+=abc[Math.floor(Math.random()*abc.length)];
    f.code.value = out;
  });

  btnSave.addEventListener('click', ()=>{
    const obj = fromForm(); if(!obj) return;
    const pos = coupons.findIndex(x=>x.id===obj.id);
    if (pos>=0) coupons[pos]=obj; else coupons.unshift(obj);
    save(); render(); closeModal(editModal);
  });

  tbody.addEventListener('click', (e)=>{
    const t = e.target;
    if (t.matches('[data-edit]')){
      const id = t.getAttribute('data-edit');
      const c = coupons.find(x=>x.id===id);
      if (c){ toForm(c); openModal(editModal); }
    }
    if (t.matches('[data-del]')){
      const id = t.getAttribute('data-del');
      const c = coupons.find(x=>x.id===id);
      if (c && confirm(Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р С”РЎС“Р С—Р С•Р Р… Р’В«Р’В»?)){
        coupons = coupons.filter(x=>x.id!==id);
        save(); render();
      }
    }
    if (t.matches('[data-qr]')){
      const id = t.getAttribute('data-qr');
      const c = coupons.find(x=>x.id===id);
      if (c){ showQr(c); }
    }
  });

  // ====== QR ======
  function redeemUrl(code){
    // Р вЂќР ВµР СР С•Р Р…РЎРѓРЎвЂљРЎР‚Р В°РЎвЂ Р С‘Р С•Р Р…Р Р…Р В°РЎРЏ РЎРѓРЎРѓРЎвЂ№Р В»Р С”Р В° Р Р…Р В° РЎР‚Р ВµР Т‘Р ВµР СР С—РЎв‚¬Р Р… (Р С—Р С•Р С”Р В° Р В±Р ВµР В· РЎРѓР ВµРЎР‚Р Р†Р ВµРЎР‚Р В°)
    return window.location.origin + '/coupon?code=' + encodeURIComponent(code);
  }

  let qrInstance = null;
  function showQr(c){
    qrTitle.textContent = c.title || 'Р С™РЎС“Р С—Р С•Р Р…';
    qrCodeText.textContent = c.code || '';
    qrBox.innerHTML = '';
    qrInstance = new QRCode(qrBox, {
      text: redeemUrl(c.code||''),
      width: 220,
      height: 220,
      correctLevel: QRCode.CorrectLevel.M
    });
    openModal(qrModal);

    btnCopyLink.onclick = async ()=>{
      try{
        await navigator.clipboard.writeText(redeemUrl(c.code||''));
        alert('Р РЋРЎРѓРЎвЂ№Р В»Р С”Р В° РЎРѓР С”Р С•Р С—Р С‘РЎР‚Р С•Р Р†Р В°Р Р…Р В°');
      }catch{ alert('Р СњР Вµ РЎС“Р Т‘Р В°Р В»Р С•РЎРѓРЎРЉ РЎРѓР С”Р С•Р С—Р С‘РЎР‚Р С•Р Р†Р В°РЎвЂљРЎРЉ'); }
    };

    btnDownloadPng.onclick = ()=>{
      // QRCode.js РЎР‚Р С‘РЎРѓРЎС“Р ВµРЎвЂљ <img> Р Р†Р Р…РЎС“РЎвЂљРЎР‚Р С‘ qrBox
      const img = qrBox.querySelector('img') || qrBox.querySelector('canvas');
      if (!img){ alert('QR Р Р…Р Вµ Р С–Р С•РЎвЂљР С•Р Р†'); return; }
      const link = document.createElement('a');
      link.download = (c.code||'coupon') + '.png';
      link.href = img.src || img.toDataURL('image/png');
      link.click();
    };

    btnPrint.onclick = ()=>{
      const w = window.open('', '_blank');
      const img = qrBox.querySelector('img') || qrBox.querySelector('canvas');
      const src = img?.src || img?.toDataURL?.('image/png') || '';
      w.document.write('<html><head><title>Р СџР ВµРЎвЂЎР В°РЎвЂљРЎРЉ QR</title></head><body style="font-family:Inter,sans-serif;padding:24px;text-align:center">');
      w.document.write('<div style="font-weight:800;margin-bottom:12px">'+escapeHtml(c.title||'Р С™РЎС“Р С—Р С•Р Р…')+'</div>');
      w.document.write('<img src="'+src+'" style="width:260px;height:260px"/><div style="margin-top:10px">Р С™Р С•Р Т‘: <b>'+escapeHtml(c.code||'')+'</b></div>');
      w.document.write('</body></html>');
      w.document.close(); w.focus(); w.print();
    };
  }

  // ====== Filters / Sorting ======
  searchInput.addEventListener('input', ()=>{ filter.q = searchInput.value.trim().toLowerCase(); render(); });
  statusFilter.addEventListener('change', ()=>{ filter.status = statusFilter.value; render(); });

  $cabQrHtml('#couponsTable thead th[data-sort]').forEach(th=>{
    th.style.cursor='pointer';
    th.addEventListener('click', ()=>{
      const by = th.getAttribute('data-sort');
      sort.dir = (sort.by===by && sort.dir==='asc') ? 'desc' : 'asc';
      sort.by = by;
      render();
    });
  });

  // ====== Export / Import CSV ======
  btnExport.addEventListener('click', ()=>{
    const fields = ['id','title','code','discountType','value','start','end','maxUses','used','minPurchase','published','description','createdAt','updatedAt'];
    const lines = [fields.join(',')];
    coupons.forEach(c=>{
      const row = fields.map(k=>{
        let v = (c[k]===undefined||c[k]===null)?'':c[k];
        if (typeof v === 'string') v = '"' + v.replace(/"/g,'""') + '"';
        return v;
      });
      lines.push(row.join(','));
    });
    const blob = new Blob([lines.join('\r\n')], {type:'text/csv;charset=utf-8;'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'coupons.csv';
    a.click(); URL.revokeObjectURL(a.href);
  });

  importInput.addEventListener('change', async ()=>{
    const file = importInput.files?.[0]; if(!file) return;
    const text = await file.text();
    const rows = text.split(/\r?\n/).filter(Boolean).map(line=>{
      const out=[]; let cur=''; let q=false;
      for(let i=0;i<line.length;i++){
        const ch=line[i];
        if(q){
          if(ch=='"' && line[i+1]=='"'){ cur+='"'; i++; }
          else if(ch=='"'){ q=false; }
          else cur+=ch;
        }else{
          if(ch==','){ out.push(cur); cur=''; }
          else if(ch=='"'){ q=true; }
          else cur+=ch;
        }
      }
      out.push(cur); return out;
    });
    const header = rows.shift()||[];
    const idx = k => header.indexOf(k);
    rows.forEach(r=>{
      if (!r.length) return;
      const obj = {
        id: r[idx('id')] || uid(),
        title: r[idx('title')] || '',
        code: (r[idx('code')]||'').toUpperCase(),
        discountType: r[idx('discountType')] || 'percent',
        value: r[idx('value')] ? Number(r[idx('value')]) : null,
        start: r[idx('start')] || '',
        end: r[idx('end')] || '',
        maxUses: r[idx('maxUses')] ? Number(r[idx('maxUses')]) : 0,
        used: r[idx('used')] ? Number(r[idx('used')]) : 0,
        minPurchase: r[idx('minPurchase')] ? Number(r[idx('minPurchase')]) : 0,
        published: (r[idx('published')]||'').toLowerCase()==='true',
        description: r[idx('description')] || '',
        createdAt: r[idx('createdAt')] || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      if (obj.title && obj.code){
        const pos = coupons.findIndex(x=>x.id===obj.id);
        if (pos>=0) coupons[pos]=obj; else coupons.push(obj);
      }
    });
    save(); render(); importInput.value='';
    alert('Р ВР СР С—Р С•РЎР‚РЎвЂљ Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬РЎвЂР Р…');
  });

  // ====== Boot ======
  render();

})();