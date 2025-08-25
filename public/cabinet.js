const rows = [
  { name:'Р С™Р В°РЎвЂћР Вµ Р’В«Р вЂ™Р В°Р Р…Р С‘Р В»РЎРЉР’В»',   category:'Р С™Р В°РЎвЂћР Вµ',     district:'Р В¦Р ВµР Р…РЎвЂљРЎР‚Р В°Р В»РЎРЉР Р…РЎвЂ№Р в„–', status:'Р В§Р ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”'      },
  { name:'Р С™Р В°РЎвЂћР Вµ Р’В«Р СћРЎР‚Р С‘Р Р…Р Т‘Р С•Р Р†Р С•Р’В»', category:'Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…', district:'Р РЋР ВµР Р†Р ВµРЎР‚Р Р…РЎвЂ№Р в„–',    status:'Р СњР В° Р СР С•Р Т‘Р ВµРЎР‚Р В°РЎвЂ Р С‘Р С‘' },
  { name:'Р’В«Р С’РЎвЂљР В»Р ВµРЎвЂљР’В»',         category:'Р В¤Р С‘РЎвЂљР Р…Р ВµРЎРѓ',   district:'Р вЂ”Р В°Р С—Р В°Р Т‘Р Р…РЎвЂ№Р в„–',    status:'Р С›Р С—РЎС“Р В±Р В»Р С‘Р С”Р С•Р Р†Р В°Р Р…Р С•' },
  { name:'Р’В«Р СљР В°РЎР‚Р С‘Р вЂ™Р В°Р Р…Р Р…Р В°Р’В»',     category:'Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…', district:'Р РЋР ВµР Р†Р ВµРЎР‚Р Р…РЎвЂ№Р в„–',    status:'Р С›Р С—РЎС“Р В±Р В»Р С‘Р С”Р С•Р Р†Р В°Р Р…Р С•' },
  { name:'Р’В«Р С™Р В°Р С”Р В°Р С•Р’В»',         category:'Р С™Р В°РЎвЂћР Вµ',     district:'Р РЋР ВµРЎРѓРЎвЂљРЎР‚Р С•РЎР‚Р ВµРЎвЂ Р С”',  status:'Р С›Р С—РЎС“Р В±Р В»Р С‘Р С”Р С•Р Р†Р В°Р Р…Р С•' },
  { name:'Р’В«Р вЂњР ВµР в„–РЎРЏР’В»',          category:'Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…', district:'Р В¦Р ВµР Р…РЎвЂљРЎР‚Р В°Р В»РЎРЉР Р…РЎвЂ№Р в„–', status:'Р С›Р С—РЎС“Р В±Р В»Р С‘Р С”Р С•Р Р†Р В°Р Р…Р С•' },
];

const qs = s => document.querySelector(s);
const qsa = s => Array.from(document.querySelectorAll(s));

function statusClass(s){
  if (/Р С•Р С—РЎС“Р В±Р В»Р С‘Р С”/i.test(s)) return 'ok';
  if (/Р СР С•Р Т‘Р ВµРЎР‚Р В°/i.test(s))  return 'warn';
  if (/РЎвЂЎР ВµРЎР‚Р Р…Р С•Р Р†Р С‘Р С”/i.test(s))return 'muted';
  return 'muted';
}

function applyFilters(data){
  const term = (qs('#search')?.value || '').trim().toLowerCase();
  const cat  = qs('#filter-category')?.value || '';
  const dist = qs('#filter-district')?.value || '';
  const st   = qs('#filter-status')?.value || '';
  return data.filter(r =>
    (!term || r.name.toLowerCase().includes(term)) &&
    (!cat  || r.category === cat) &&
    (!dist || r.district === dist) &&
    (!st   || r.status === st)
  );
}

function renderTable(){
  const tbody = qs('#cards-tbody'); if (!tbody) return;
  const list = applyFilters(rows);
  tbody.innerHTML = list.map(r => 
    <tr>
      <td></td>
      <td></td>
      <td></td>
      <td><span class="chip "></span></td>
      <td class="row-actions">РІвЂ№В®</td>
    </tr>
  ).join('');
}

function drawBarChart(){
  const c = document.getElementById('barChart'); if (!c) return;
  const ctx = c.getContext('2d'), W=c.width, H=c.height;
  ctx.clearRect(0,0,W,H);
  const data = [4,5,6,7,8,9], max = Math.max(...data)+1, p=32, bw=(W-p*2)/data.length*.6, g=(W-p*2)/data.length*.4;

  // РЎРѓР ВµРЎвЂљР С”Р В°
  ctx.globalAlpha=.15; ctx.strokeStyle='#9CA3AF';
  for(let i=0;i<=4;i++){const y=p+i*((H-p*2)/4); ctx.beginPath(); ctx.moveTo(p,y); ctx.lineTo(W-p,y); ctx.stroke();}
  ctx.globalAlpha=1;

  // РЎвЂЎ/Р В± РЎРѓРЎвЂљР С•Р В»Р В±Р С‘Р С”Р С‘
  const css = getComputedStyle(document.documentElement);
  const barColor = (css.getPropertyValue('--chart-bar') || css.getPropertyValue('--accent-primary') || '#111').trim();
  ctx.fillStyle = barColor;

  data.forEach((v,i)=>{
    const h=(v/max)*(H-p*2), x=p+i*(bw+g)+g/2, y=H-p-h;
    ctx.fillRect(x,y,bw,h);
  });
}

// Р вЂќР ВµР В»Р ВµР С–Р В°РЎвЂ Р С‘РЎРЏ Р С”Р В»Р С‘Р С”Р С•Р Р† (РЎР‚Р В°Р В±Р С•РЎвЂљР В°Р ВµРЎвЂљ Р Т‘Р В°Р В¶Р Вµ Р ВµРЎРѓР В»Р С‘ Р Р†Р ВµРЎР‚РЎРѓРЎвЂљР С”РЎС“ Р С—Р С•Р СР ВµР Р…РЎРЏРЎвЂљРЎРЉ)
function handleClick(e){
  const target = e.target.closest('.sidebar .nav-item, .tab, #create-card');
  if (!target) return;

  // Р С—Р ВµРЎР‚Р ВµРЎвЂ¦Р С•Р Т‘ Р С—Р С• РЎР‚Р В°Р В·Р Т‘Р ВµР В»Р В°Р С РЎРѓР В°Р в„–Р Т‘Р В±Р В°РЎР‚Р В°
  if (target.matches('.sidebar .nav-item')){
    e.preventDefault();
    const items = qsa('.sidebar .nav-item'), pages = qsa('.page'), title = qs('.topbar-title');
    items.forEach(i=>i.classList.remove('active'));
    target.classList.add('active');
    const pid = 'page-' + target.dataset.page;
    pages.forEach(p=>p.classList.remove('visible'));
    const el = document.getElementById(pid);
    if (el) el.classList.add('visible');
    if (title) title.textContent = target.textContent.replace(/^[^\\s]+\\s/, '');
    return;
  }

  // РЎвЂљР В°Р В±РЎвЂ№ Р Р† Р’В«Р С™Р В°РЎР‚РЎвЂљР С•РЎвЂЎР С”Р С‘ / QR / QRR / Р С’Р Р…Р В°Р В»Р С‘РЎвЂљР С‘Р С”Р В°Р’В»
  if (target.matches('.tab')){
    e.preventDefault();
    const tabs = qsa('.tab'), panes = qsa('.tab-pane');
    tabs.forEach(t=>t.classList.remove('active'));
    target.classList.add('active');
    panes.forEach(p=>p.classList.remove('visible'));
    const pane = document.getElementById(target.dataset.tab);
    if (pane) pane.classList.add('visible');
    return;
  }

  // Р’В«Р РЋР С•Р В·Р Т‘Р В°РЎвЂљРЎРЉ Р С”Р В°РЎР‚РЎвЂљР С•РЎвЂЎР С”РЎС“Р’В»
  if (target.matches('#create-card')){
    e.preventDefault();
    alert('Р вЂ”Р Т‘Р ВµРЎРѓРЎРЉ Р С•РЎвЂљР С”РЎР‚Р С•Р ВµРЎвЂљРЎРѓРЎРЏ Р С”Р С•Р Р…РЎРѓРЎвЂљРЎР‚РЎС“Р С”РЎвЂљР С•РЎР‚ Р С”Р В°РЎР‚РЎвЂљР С•РЎвЂЎР С”Р С‘ (Р В·Р В°Р С–Р В»РЎС“РЎв‚¬Р С”Р В°).');
    return;
  }
}

// Р СџР С•Р Т‘Р Т‘Р ВµРЎР‚Р В¶Р С”Р В° Р С”Р В»Р В°Р Р†Р С‘Р В°РЎвЂљРЎС“РЎР‚РЎвЂ№: Enter/Space = Р С”Р В»Р С‘Р С”
function handleKeydown(e){
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.nav-item, .tab, #create-card')){
    e.preventDefault();
    e.target.click();
  }
}

function setupFilters(){
  ['#search','#filter-category','#filter-district','#filter-status'].forEach(sel=>{
    const el = qs(sel);
    if (!el) return;
    const ev = el.tagName === 'SELECT' ? 'change' : 'input';
    el.addEventListener(ev, renderTable);
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  // Р Т‘Р ВµР В»Р ВµР С–Р С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С‘Р Вµ РЎРѓР С•Р В±РЎвЂ№РЎвЂљР С‘Р в„–
  document.addEventListener('click', handleClick);
  document.addEventListener('keydown', handleKeydown);

  // Р С—Р ВµРЎР‚Р Р†Р С‘РЎвЂЎР Р…РЎвЂ№Р в„– РЎР‚Р ВµР Р…Р Т‘Р ВµРЎР‚
  setupFilters();
  renderTable();
  drawBarChart();
});