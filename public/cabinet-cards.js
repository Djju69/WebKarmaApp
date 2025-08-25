(function(){
  'use strict';

  const STORAGE_KEY = 'ks_cards_v1';
  const CATEGORIES = ['Р С™Р В°РЎвЂћР Вµ','Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…','Р В¤Р С‘РЎвЂљР Р…Р ВµРЎРѓ','Р С™РЎР‚Р В°РЎРѓР С•РЎвЂљР В°','Р РЋРЎС“Р С—Р ВµРЎР‚Р СР В°РЎР‚Р С”Р ВµРЎвЂљ','Р вЂР В°РЎР‚','Р СџР С‘РЎвЂ РЎвЂ Р В°','Р вЂќР С•РЎРѓРЎвЂљР В°Р Р†Р С”Р В°'];
  const DISTRICTS  = ['Р В¦Р ВµР Р…РЎвЂљРЎР‚Р В°Р В»РЎРЉР Р…РЎвЂ№Р в„–','Р РЋР ВµР Р†Р ВµРЎР‚Р Р…РЎвЂ№Р в„–','Р В®Р В¶Р Р…РЎвЂ№Р в„–','Р вЂ™Р С•РЎРѓРЎвЂљР С•РЎвЂЎР Р…РЎвЂ№Р в„–','Р вЂ”Р В°Р С—Р В°Р Т‘Р Р…РЎвЂ№Р в„–','Р С’Р Т‘Р СР С‘РЎР‚Р В°Р В»РЎвЂљР ВµР в„–РЎРѓР С”Р С‘Р в„–','Р СџР ВµРЎвЂљРЎР‚Р С•Р С–РЎР‚Р В°Р Т‘РЎРѓР С”Р С‘Р в„–','Р СџРЎР‚Р С‘Р СР С•РЎР‚РЎРѓР С”Р С‘Р в„–','Р В¤РЎР‚РЎС“Р Р…Р В·Р ВµР Р…РЎРѓР С”Р С‘Р в„–'];

  // State
  let cards = load();
  let sort = { by: 'name', dir: 'asc' };
  let filters = { q: '', category: '', district: '', status: '' };

  // Shortcuts
  const $ = sel => document.querySelector(sel);
  const $cabCardsHtml = sel => Array.from(document.querySelectorAll(sel));

  // Elements
  const tbody = #cardsTbody;
  const emptyState = #emptyState;
  const btnAdd = #btnAdd;
  const btnExport = #btnExport;
  const importInput = #importCsvInput;

  const editModal = #editModal;
  const btnSave = #btnSave;
  const form = #cardForm;

  // Form fields
  const fId = #cardId;
  const fName = #name;
  const fCategory = #category;
  const fDistrict = #district;
  const fDiscount = #discount;
  const fDesc = #description;
  const fPublished = #published;
  const fStatus = #status;

  // Filters
  const sInput = #searchInput;
  const sCategory = #filterCategory;
  const sDistrict = #filterDistrict;
  const sStatus = #filterStatus;

  // Init selects
  function fillSelect(select, list, placeholder){
    if (placeholder) {
      const opt = document.createElement('option');
      opt.value = ''; opt.textContent = placeholder;
      select.appendChild(opt);
    }
    list.forEach(v=>{
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v;
      select.appendChild(opt);
    });
  }
  fillSelect(fCategory, CATEGORIES);
  fillSelect(fDistrict, DISTRICTS);
  fillSelect(sCategory, CATEGORIES, 'Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ: Р Р†РЎРѓР Вµ');
  fillSelect(sDistrict, DISTRICTS, 'Р В Р В°Р в„–Р С•Р Р…: Р Р†РЎРѓР Вµ');

  // Render
  function render(){
    // filtering
    let rows = cards.filter(c=>{
      if (filters.q && !c.name.toLowerCase().includes(filters.q)) return false;
      if (filters.category && c.category !== filters.category) return false;
      if (filters.district && c.district !== filters.district) return false;
      if (filters.status && c.status !== filters.status) return false;
      return true;
    });
    // sorting
    rows.sort((a,b)=>{
      const dir = (sort.dir === 'asc') ? 1 : -1;
      let va = a[sort.by], vb = b[sort.by];
      if (sort.by === 'discount') { va = Number(va||0); vb = Number(vb||0); }
      return (va>vb?1:va<vb?-1:0)*dir;
    });

    // draw
    tbody.innerHTML = '';
    rows.forEach(row=>{
      const tr = document.createElement('tr');
      tr.innerHTML = 
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td><span class="status "></span></td>
        <td class="row-actions">
          <button class="btn btn-xs" data-edit="">Р ВР В·Р С.</button>
          <button class="btn btn-xs btn-danger" data-del="">Р Р€Р Т‘Р В°Р В».</button>
        </td>
      ;
      tbody.appendChild(tr);
    });

    emptyState.style.display = rows.length ? 'none' : 'block';
  }

  function statusClass(s){
    if (!s) return 'muted';
    s = s.toLowerCase();
    if (s.includes('Р С•Р С—РЎС“Р В±Р В»Р С‘Р С”')) return 'ok';
    if (s.includes('Р СР С•Р Т‘Р ВµРЎР‚Р В°'))  return 'warn';
    if (s.includes('РЎвЂЎР ВµРЎР‚Р Р…Р С•Р Р†'))  return 'muted';
    return 'muted';
  }

  function escapeHtml(str=''){
    return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  // Storage
  function load(){
    try{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return demo();
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) return arr;
      return demo();
    }catch(e){ return demo(); }
  }
  function save(){ localStorage.setItem(STORAGE_KEY, JSON.stringify(cards)); }

  function demo(){
    return [
      { id: uid(), name:'Р С™Р С•РЎвЂћР ВµР в„–Р Р…РЎРЏ Р’В«Р вЂ™Р В°Р Р…Р С‘Р В»РЎРЉР’В»', category:'Р С™Р В°РЎвЂћР Вµ', district:'Р В¦Р ВµР Р…РЎвЂљРЎР‚Р В°Р В»РЎРЉР Р…РЎвЂ№Р в„–', discount:15, status:'Р В§Р ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”', published:false, description:'' },
      { id: uid(), name:'Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р… Р’В«Р СљР В°РЎР‚Р С‘Р вЂ™Р В°Р Р…Р Р…Р В°Р’В»', category:'Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…', district:'Р РЋР ВµР Р†Р ВµРЎР‚Р Р…РЎвЂ№Р в„–', discount:10, status:'Р С›Р С—РЎС“Р В±Р В»Р С‘Р С”Р С•Р Р†Р В°Р Р…Р С•', published:true, description:'' },
      { id: uid(), name:'Р В¤Р С‘РЎвЂљР Р…Р ВµРЎРѓ Р’В«Р С’РЎвЂљР В»Р ВµРЎвЂљР’В»', category:'Р В¤Р С‘РЎвЂљР Р…Р ВµРЎРѓ', district:'Р вЂ”Р В°Р С—Р В°Р Т‘Р Р…РЎвЂ№Р в„–', discount:20, status:'Р СњР В° Р СР С•Р Т‘Р ВµРЎР‚Р В°РЎвЂ Р С‘Р С‘', published:false, description:'' }
    ];
  }
  function uid(){ return 'id_'+Math.random().toString(36).slice(2)+Date.now().toString(36); }

  // Modal helpers
  function openModal(){
    editModal.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
  }
  function closeModal(){
    editModal.setAttribute('aria-hidden','true');
    document.body.style.overflow='';
    form.reset();
    fId.value='';
  }

  // CRUD
  function toForm(card){
    fId.value = card.id||'';
    fName.value = card.name||'';
    fCategory.value = card.category||'';
    fDistrict.value = card.district||'';
    fDiscount.value = card.discount ?? '';
    fDesc.value = card.description||'';
    fPublished.checked = !!card.published;
    fStatus.value = card.status||'Р В§Р ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”';
  }
  function fromForm(){
    const name = fName.value.trim();
    if (!name) { alert('Р вЂ™Р Р†Р ВµР Т‘Р С‘РЎвЂљР Вµ Р Р…Р В°Р В·Р Р†Р В°Р Р…Р С‘Р Вµ'); fName.focus(); return null; }
    let discount = fDiscount.value.trim()==='' ? null : Number(fDiscount.value);
    if (discount!=null && (isNaN(discount) || discount<0 || discount>99)) {
      alert('Р РЋР С”Р С‘Р Т‘Р С”Р В° Р Т‘Р С•Р В»Р В¶Р Р…Р В° Р В±РЎвЂ№РЎвЂљРЎРЉ РЎвЂЎР С‘РЎРѓР В»Р С•Р С 0..99'); fDiscount.focus(); return null;
    }
    const obj = {
      id: fId.value || uid(),
      name,
      category: fCategory.value || '',
      district: fDistrict.value || '',
      discount,
      description: fDesc.value.trim(),
      published: fPublished.checked,
      status: fStatus.value || (fPublished.checked ? 'Р С›Р С—РЎС“Р В±Р В»Р С‘Р С”Р С•Р Р†Р В°Р Р…Р С•':'Р В§Р ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”'),
      updatedAt: new Date().toISOString(),
      createdAt: fId.value ? (cards.find(x=>x.id===fId.value)?.createdAt || new Date().toISOString()) : new Date().toISOString(),
    };
    return obj;
  }

  // Events
  btnAdd.addEventListener('click', ()=>{
    form.reset();
    fId.value = '';
    fStatus.value = 'Р В§Р ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”';
    fPublished.checked = false;
    openModal();
  });

  btnSave.addEventListener('click', ()=>{
    const obj = fromForm();
    if (!obj) return;
    const idx = cards.findIndex(x=>x.id===obj.id);
    if (idx>=0) cards[idx]=obj; else cards.unshift(obj);
    save(); render(); closeModal();
  });

  editModal.addEventListener('click', (e)=>{
    if (e.target.hasAttribute('data-close')) { closeModal(); }
  });

  tbody.addEventListener('click', (e)=>{
    const t = e.target;
    if (t.matches('[data-edit]')) {
      const id = t.getAttribute('data-edit');
      const card = cards.find(x=>x.id===id);
      if (card){ toForm(card); openModal(); }
    }
    if (t.matches('[data-del]')) {
      const id = t.getAttribute('data-del');
      const card = cards.find(x=>x.id===id);
      if (card && confirm(Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р’В«Р’В»?)) {
        cards = cards.filter(x=>x.id!==id);
        save(); render();
      }
    }
  });

  // Sorting
  $cabCardsHtml('#cardsTable thead th[data-sort]').forEach(th=>{
    th.style.cursor='pointer';
    th.addEventListener('click', ()=>{
      const by = th.getAttribute('data-sort');
      sort.dir = (sort.by===by && sort.dir==='asc') ? 'desc' : 'asc';
      sort.by = by;
      render();
    });
  });

  // Filters
  sInput.addEventListener('input', ()=>{ filters.q = sInput.value.trim().toLowerCase(); render(); });
  sCategory.addEventListener('change', ()=>{ filters.category = sCategory.value; render(); });
  sDistrict.addEventListener('change', ()=>{ filters.district = sDistrict.value; render(); });
  sStatus.addEventListener('change', ()=>{ filters.status = sStatus.value; render(); });

  // Export / Import CSV
  btnExport.addEventListener('click', ()=>{
    const header = ['id','name','category','district','discount','status','published','description','createdAt','updatedAt'];
    const lines = [header.join(',')];
    cards.forEach(c=>{
      const row = header.map(k=>{
        let v = c[k];
        if (typeof v === 'string') {
          v = '"' + v.replace(/"/g,'""') + '"';
        }
        return v===undefined||v===null ? '' : v;
      });
      lines.push(row.join(','));
    });
    const blob = new Blob([lines.join('\r\n')], {type:'text/csv;charset=utf-8;'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'cards.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  importInput.addEventListener('change', async ()=>{
    const file = importInput.files?.[0];
    if (!file) return;
    const text = await file.text();
    const rows = text.split(/\r?\n/).filter(Boolean).map(line => {
      // Р С—РЎР‚Р С•РЎРѓРЎвЂљР ВµР Р…РЎРЉР С”Р С‘Р в„– Р С—Р В°РЎР‚РЎРѓР ВµРЎР‚ CSV (Р В±Р ВµР В· ;), Р С—Р С•Р В»РЎРЏ Р Р† Р С”Р В°Р Р†РЎвЂ№РЎвЂЎР С”Р В°РЎвЂ¦ Р С—Р С•Р Т‘Р Т‘Р ВµРЎР‚Р В¶Р С‘Р Р†Р В°Р ВµР С
      const out = []; let cur = ''; let inQ = false;
      for (let i=0;i<line.length;i++){
        const ch = line[i];
        if (inQ){
          if (ch === '"' && line[i+1] === '"'){ cur+='"'; i++; }
          else if (ch === '"'){ inQ=false; }
          else cur += ch;
        } else {
          if (ch === ','){ out.push(cur); cur=''; }
          else if (ch === '"'){ inQ=true; }
          else cur += ch;
        }
      }
      out.push(cur);
      return out;
    });
    const header = rows.shift();
    const idx = (k)=> header.indexOf(k);
    rows.forEach(r=>{
      if (!r.length) return;
      const obj = {
        id: r[idx('id')] || uid(),
        name: r[idx('name')] || '',
        category: r[idx('category')] || '',
        district: r[idx('district')] || '',
        discount: r[idx('discount')] ? Number(r[idx('discount')]) : null,
        status: r[idx('status')] || 'Р В§Р ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”',
        published: (r[idx('published')]||'').toString().toLowerCase()==='true',
        description: r[idx('description')] || '',
        createdAt: r[idx('createdAt')] || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      if (obj.name) {
        const pos = cards.findIndex(x=>x.id===obj.id);
        if (pos>=0) cards[pos]=obj; else cards.push(obj);
      }
    });
    save(); render();
    importInput.value = '';
    alert('Р ВР СР С—Р С•РЎР‚РЎвЂљ Р В·Р В°Р Р†Р ВµРЎР‚РЎв‚¬РЎвЂР Р…');
  });

  // First render
  render();
})();