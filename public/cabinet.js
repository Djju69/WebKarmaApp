const rows = [
  { name:'Кафе «Ваниль»',   category:'Кафе',     district:'Центральный', status:'Черновик'      },
  { name:'Кафе «Триндово»', category:'Ресторан', district:'Северный',    status:'На модерации' },
  { name:'«Атлет»',         category:'Фитнес',   district:'Западный',    status:'Опубликовано' },
  { name:'«МариВанна»',     category:'Ресторан', district:'Северный',    status:'Опубликовано' },
  { name:'«Какао»',         category:'Кафе',     district:'Сестрорецк',  status:'Опубликовано' },
  { name:'«Гейя»',          category:'Ресторан', district:'Центральный', status:'Опубликовано' },
];

const qs = s => document.querySelector(s);
const qsa = s => Array.from(document.querySelectorAll(s));

function statusClass(s){
  if (/опублик/i.test(s)) return 'ok';
  if (/модера/i.test(s))  return 'warn';
  if (/черновик/i.test(s))return 'muted';
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
      <td class="row-actions">⋮</td>
    </tr>
  ).join('');
}

function drawBarChart(){
  const c = document.getElementById('barChart'); if (!c) return;
  const ctx = c.getContext('2d'), W=c.width, H=c.height;
  ctx.clearRect(0,0,W,H);
  const data = [4,5,6,7,8,9], max = Math.max(...data)+1, p=32, bw=(W-p*2)/data.length*.6, g=(W-p*2)/data.length*.4;

  // сетка
  ctx.globalAlpha=.15; ctx.strokeStyle='#9CA3AF';
  for(let i=0;i<=4;i++){const y=p+i*((H-p*2)/4); ctx.beginPath(); ctx.moveTo(p,y); ctx.lineTo(W-p,y); ctx.stroke();}
  ctx.globalAlpha=1;

  // ч/б столбики
  const css = getComputedStyle(document.documentElement);
  const barColor = (css.getPropertyValue('--chart-bar') || css.getPropertyValue('--accent-primary') || '#111').trim();
  ctx.fillStyle = barColor;

  data.forEach((v,i)=>{
    const h=(v/max)*(H-p*2), x=p+i*(bw+g)+g/2, y=H-p-h;
    ctx.fillRect(x,y,bw,h);
  });
}

// Делегация кликов (работает даже если верстку поменять)
function handleClick(e){
  const target = e.target.closest('.sidebar .nav-item, .tab, #create-card');
  if (!target) return;

  // переход по разделам сайдбара
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

  // табы в «Карточки / QR / QRR / Аналитика»
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

  // «Создать карточку»
  if (target.matches('#create-card')){
    e.preventDefault();
    alert('Здесь откроется конструктор карточки (заглушка).');
    return;
  }
}

// Поддержка клавиатуры: Enter/Space = клик
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
  // делегирование событий
  document.addEventListener('click', handleClick);
  document.addEventListener('keydown', handleKeydown);

  // первичный рендер
  setupFilters();
  renderTable();
  drawBarChart();
});