// Simple data to populate the table
const demoRows = [
  { name: 'Кафе "Ваниль"', category: 'Кафе', district: 'Центральный', status: 'Черновик' },
  { name: 'Кафе "Триндово"', category: 'Ресторанный', district: 'Васильевский', status: 'На модерации' },
  { name: 'Кафе "Ритак"', category: 'Ресторан', district: 'Электрозавод', status: '20 %' },
  { name: 'Кафе "Белнзий"', category: 'Опубликовано', district: 'Опубликовано', status: '10 %' },
  { name: 'Кафе "Какао"', category: 'Кафе', district: 'Сестрорецк', status: '5 %' },
  { name: 'Кафе "Гейя"', category: 'Рестора', district: 'Опубликовано', status: '18 %' },
];

function fillTable() {
  const tbody = document.getElementById('cards-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  demoRows.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.name}</td>
      <td>${row.category}</td>
      <td>${row.district}</td>
      <td><span class="status ${getStatusClass(row.status)}">${row.status}</span></td>
      <td class="row-actions">⋮</td>
    `;
    tbody.appendChild(tr);
  });
}

function getStatusClass(status) {
  if (/опублик/i.test(status)) return 'ok';
  if (/модера/i.test(status)) return 'warn';
  if (/черновик/i.test(status)) return 'muted';
  if (/%/.test(status)) return 'ok';
  return 'muted';
}

// Tabs
function setupTabs() {
  const tabs = document.querySelectorAll('.tab');
  const panes = document.querySelectorAll('.tab-pane');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      panes.forEach(p => p.classList.remove('visible'));
      const target = document.getElementById(tab.dataset.tab);
      if (target) target.classList.add('visible');
    });
  });
}

// Sidebar navigation
function setupSidebarNav() {
  const items = document.querySelectorAll('.sidebar .nav-item');
  const pages = document.querySelectorAll('.page');
  const title = document.querySelector('.topbar-title');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const pageId = 'page-' + item.dataset.page;
      pages.forEach(p => p.classList.remove('visible'));
      const el = document.getElementById(pageId);
      if (el) el.classList.add('visible');
      if (title) title.textContent = item.textContent.replace(/^[^\s]+\s/, '');
    });
  });
}

// Simple bar chart
function drawBarChart() {
  const canvas = document.getElementById('barChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const data = [4, 5, 6, 7, 8, 9];
  const max = Math.max(...data) + 1;
  const padding = 32;
  const barW = (W - padding * 2) / data.length * 0.6;
  const gap = (W - padding * 2) / data.length * 0.4;

  // grid lines
  ctx.globalAlpha = 0.15;
  ctx.strokeStyle = '#BFC9CC';
  for (let i = 0; i <= 4; i++) {
    const y = padding + i * ((H - padding * 2) / 4);
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(W - padding, y);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  // bars
  ctx.fillStyle = '#C8FF9E';
  data.forEach((v, i) => {
    const h = (v / max) * (H - padding * 2);
    const x = padding + i * (barW + gap) + gap / 2;
    const y = H - padding - h;
    ctx.fillRect(x, y, barW, h);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  fillTable();
  setupTabs();
  setupSidebarNav();
  drawBarChart();
});
