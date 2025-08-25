document.addEventListener("DOMContentLoaded", ()=>{
  const layout = document.querySelector(".dashboard-layout");
  const toggle = document.querySelector(".nav-toggle");
  toggle?.addEventListener("click", ()=> layout?.classList.toggle("menu-open"));
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(a=>{
    a.addEventListener("click", ()=> layout?.classList.remove("menu-open"));
  });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape") layout?.classList.remove("menu-open"); });

  // DEMO (если нет данных)
  const demoCards = [
    {name:"Кофейня «У Ашота»", cat:"Кафе",    dist:"Центр", st:"-15%"},
    {name:"Ресторан «МариВанна»", cat:"Ресторан", dist:"Север", st:"-10%"},
    {name:"Фитнес-центр «Атлет»", cat:"Фитнес", dist:"Запад", st:"-20%"}
  ];
  function load(key, fallback){ try{ const v = JSON.parse(localStorage.getItem(key)||"null"); return Array.isArray(v)?v:fallback }catch{ return fallback } }
  function save(key, data){ localStorage.setItem(key, JSON.stringify(data)); }

  // Обзор
  if (document.getElementById("page-overview")){
    const rows = load("ks_cards", demoCards);
    const tb   = document.getElementById("cards-tbody");
    if (tb){
      tb.innerHTML = rows.map(r=>`<tr><td>${r.name}</td><td>${r.cat}</td><td>${r.dist}</td><td><span class="status ok">${r.st||""}</span></td></tr>`).join("")
        || '<tr><td colspan="4" class="muted" style="padding:16px">Нет данных</td></tr>';
    }
    const S=(id,val)=>{ const el=document.getElementById(id); if(el) el.textContent=String(val) };
    S("stat-visitors",12630); S("stat-scans",3450); S("stat-cvr","27,3 %"); S("stat-avg","1 280 ₽");
  }

  // Карточки
  if (document.getElementById("page-cards")){
    const key="ks_cards"; let rows = load(key, demoCards.slice());
    const tbody = document.getElementById("cards-tbody");
    function render(){
      tbody.innerHTML = rows.map((r,i)=>`
        <tr>
          <td>${r.name}</td><td>${r.cat}</td><td>${r.dist}</td>
          <td><span class="status ${r.st?'ok':'muted'}">${r.st||'—'}</span></td>
          <td style="text-align:right">
            <button class="btn xs outline" data-ed="${i}">Редакт.</button>
            <button class="btn xs" data-del="${i}">Удалить</button>
          </td>
        </tr>`).join("") || '<tr><td colspan="5" class="muted" style="padding:16px">Пусто</td></tr>';
    }
    function promptCard(base){
      const name = prompt("Название", base?.name||""); if(!name) return null;
      const cat  = prompt("Категория (Кафе/Ресторан/Фитнес)", base?.cat||"");
      const dist = prompt("Район (Центр/Юг/Север/Запад)", base?.dist||"");
      const st   = prompt("Статус/скидка (например -15%)", base?.st||"");
      return {name, cat, dist, st};
    }
    document.getElementById("card-add")?.addEventListener("click", ()=>{
      const c = promptCard(null); if(!c) return; rows.push(c); save(key, rows); render();
    });
    tbody?.addEventListener("click",(e)=>{
      const t=e.target; if(!(t instanceof HTMLElement)) return;
      if(t.hasAttribute("data-del")){ const i=+t.getAttribute("data-del"); rows.splice(i,1); save(key,rows); render(); }
      else if(t.hasAttribute("data-ed")){ const i=+t.getAttribute("data-ed"); const c=promptCard(rows[i]); if(!c) return; rows[i]=c; save(key,rows); render(); }
    });
    render();
  }

  // Купоны
  if (document.getElementById("page-qr")){
    const key="ks_coupons"; let rows = load(key, []);
    const tbody=document.getElementById("coupon-tbody");
    function render(){
      tbody.innerHTML = rows.map((r,i)=>`
        <tr><td>${r.code}</td><td>${r.off||0}%</td><td>${r.exp||'—'}</td><td>${r.limit||'—'}</td>
        <td style="text-align:right"><button class="btn xs" data-del="${i}">Удалить</button></td></tr>
      `).join("") || '<tr><td colspan="5" class="muted" style="padding:16px">Нет купонов</td></tr>';
    }
    document.getElementById("coupon-add")?.addEventListener("click", ()=>{
      const code=prompt("Код купона"); if(!code) return;
      const off=+prompt("Скидка %","10")||0; const exp=prompt("Действует до (YYYY-MM-DD)",""); const limit=+prompt("Лимит, шт","100")||0;
      rows.push({code,off,exp,limit}); save(key,rows); render();
    });
    tbody?.addEventListener("click",(e)=>{ const t=e.target; if(!(t instanceof HTMLElement)) return;
      if(t.hasAttribute("data-del")){ const i=+t.getAttribute("data-del"); rows.splice(i,1); save(key,rows); render(); }
    });
    render();
  }

  // Районы (фильтр читает карточки)
  if (document.getElementById("page-districts")){
    const list=document.getElementById("filtered");
    const selD=document.getElementById("sel-district");
    const selC=document.getElementById("sel-category");
    const rows = load("ks_cards", []);
    function render(){
      const d=selD.value.trim(), c=selC.value.trim();
      const f=rows.filter(r => (!d||r.dist===d) && (!c||r.cat===c));
      list.innerHTML = f.map(r=>`<div class="drow"><b>${r.name}</b> — ${r.cat}, ${r.dist} <span class="muted">${r.st||''}</span></div>`).join("")
        || '<div class="drow muted">Нет карточек под выбранный фильтр.</div>';
    }
    selD?.addEventListener("change", render);
    selC?.addEventListener("change", render);
    render();
  }
});