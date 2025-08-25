document.addEventListener("DOMContentLoaded", () => {
  // Mobile menu
  const toggle = document.querySelector(".nav-toggle");
  const header = document.querySelector(".site-header");
  toggle?.addEventListener("click", () => header?.classList.toggle("open"));

  // Р СњР В°Р С—Р С•Р В»Р Р…Р ВµР Р…Р С‘Р Вµ Р С”Р В°РЎР‚РЎС“РЎРѓР ВµР В»Р С‘
  const ADS = [
    {title:"-20% Р Р…Р В° Р С”Р С•РЎвЂћР Вµ", desc:"Р РЋР ВµР С–Р С•Р Т‘Р Р…РЎРЏ Р Р† Р’В«Р Р€ Р С’РЎв‚¬Р С•РЎвЂљР В°Р’В» Р Т‘Р С• 18:00", tag:"Р С™Р В°РЎвЂћР Вµ"},
    {title:"Р вЂР ВµРЎРѓР С—Р В»Р В°РЎвЂљР Р…РЎвЂ№Р в„– Р Т‘Р ВµРЎРѓР ВµРЎР‚РЎвЂљ", desc:"Р СџРЎР‚Р С‘ Р В·Р В°Р С”Р В°Р В·Р Вµ Р С•РЎвЂљ 800 РІвЂљР…", tag:"Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…"},
    {title:"3 Р Р†Р С‘Р В·Р С‘РЎвЂљР В° = Р В°Р В±Р С•Р Р…Р ВµР СР ВµР Р…РЎвЂљ -30%", desc:"Р В¤Р С‘РЎвЂљР Р…Р ВµРЎРѓ Р’В«Р С’РЎвЂљР В»Р ВµРЎвЂљР’В»", tag:"Р В¤Р С‘РЎвЂљР Р…Р ВµРЎРѓ"},
    {title:"-10% Р Т‘Р В»РЎРЏ Р Р…Р С•Р Р†РЎвЂ№РЎвЂ¦ Р С–Р С•РЎРѓРЎвЂљР ВµР в„–", desc:"Р’В«Р СљР В°РЎР‚Р С‘Р вЂ™Р В°Р Р…Р Р…Р В°Р’В»", tag:"Р В Р ВµРЎРѓРЎвЂљР С•РЎР‚Р В°Р Р…"},
    {title:"Happy Hours", desc:"Р РЋ 16:00 Р Т‘Р С• 18:00", tag:"Р С™Р В°РЎвЂћР Вµ"},
    {title:"Р С™РЎС“Р С—Р С•Р Р… -200 РІвЂљР…", desc:"Р СњР В° Р С—Р ВµРЎР‚Р Р†РЎвЂ№Р в„– Р В·Р В°Р С”Р В°Р В·", tag:"Р вЂќР С•РЎРѓРЎвЂљР В°Р Р†Р С”Р В°"}
  ];
  const track = document.getElementById("adsTrack");
  if (track) {
    track.innerHTML = ADS.map(a => `
      <article class="carousel-card">
        <div>
          <div class="carousel-title">${a.title}</div>
          <div class="carousel-desc">${a.desc}</div>
        </div>
        <div class="carousel-meta">
          <span style="font-size:12px;color:#6B7280">${a.tag}</span>
          <a class="btn" style="padding:6px 10px" href="/cabinet">Р СџР С•Р Т‘РЎР‚Р С•Р В±Р Р…Р ВµР Вµ</a>
        </div>
      </article>
    `).join("");
  }

  // Р С™Р Р…Р С•Р С—Р С”Р С‘ Р С”Р В°РЎР‚РЎС“РЎРѓР ВµР В»Р С‘
  const scroller = document.getElementById("adsCarousel");
  const prev = document.querySelector('.carousel-btn[data-dir="prev"]');
  const next = document.querySelector('.carousel-btn[data-dir="next"]');
  function scrollByOne(dir=1){
    if (!track) return;
    const card = track.querySelector(".carousel-card");
    if (!card) return;
    const step = card.getBoundingClientRect().width + 16; // РЎв‚¬Р С‘РЎР‚Р С‘Р Р…Р В° + gap
    track.scrollBy({left: step * dir, behavior: "smooth"});
  }
  prev?.addEventListener("click", ()=>scrollByOne(-1));
  next?.addEventListener("click", ()=>scrollByOne(1));

  // Р РЋР Р†Р В°Р в„–Р С— Р Р…Р В° Р СР С•Р В±Р С‘Р В»Р Вµ
  let sx=0, sl=0, dragging=false;
  track?.addEventListener("pointerdown", e=>{dragging=true; sx=e.clientX; sl=track.scrollLeft; track.setPointerCapture(e.pointerId);});
  track?.addEventListener("pointermove", e=>{ if(!dragging) return; track.scrollLeft = sl - (e.clientX - sx);});
  track?.addEventListener("pointerup",   ()=>{dragging=false});
  track?.addEventListener("pointercancel",()=>{dragging=false});
});// DASHBOARD MOBILE SIDEBAR (v2)
(function(){
  if (!document.body.classList.contains('dashboard-body')) return;

  const sidebar = document.querySelector('.sidebar');
  const topbar  = document.querySelector('.topbar');
  if (!sidebar || !topbar) return;

  // Р В±РЎС“РЎР‚Р С–Р ВµРЎР‚-Р С”Р Р…Р С•Р С—Р С”Р В° (Р ВµРЎРѓР В»Р С‘ Р Р…Р ВµРЎвЂљ РІР‚вЂќ Р Т‘Р С•Р В±Р В°Р Р†Р С‘Р С)
  let btn = topbar.querySelector('#menuToggle');
  if (!btn){
    btn = document.createElement('button');
    btn.id = 'menuToggle';
    btn.className = 'hamburger';
    btn.setAttribute('aria-label','Р СљР ВµР Р…РЎР‹');
    btn.innerHTML = '<span></span>';
    topbar.prepend(btn);
  }

  // РЎвЂћР С•Р Р…-Р В±Р ВµР С”Р Т‘РЎР‚Р С•Р С—
  let backdrop = document.querySelector('#sidebarBackdrop');
  if (!backdrop){
    backdrop = document.createElement('div');
    backdrop.id = 'sidebarBackdrop';
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
  }

  const open  = ()=>{ sidebar.classList.add('open'); backdrop.classList.add('visible'); document.body.classList.add('menu-open'); };
  const close = ()=>{ sidebar.classList.remove('open'); backdrop.classList.remove('visible'); document.body.classList.remove('menu-open'); };

  btn.addEventListener('click', ()=>{ sidebar.classList.contains('open') ? close() : open(); });
  backdrop.addEventListener('click', close);

  // Р В·Р В°Р С”РЎР‚РЎвЂ№Р Р†Р В°РЎвЂљРЎРЉ Р С—РЎР‚Р С‘ Р С”Р В»Р С‘Р С”Р Вµ Р С—Р С• Р С—РЎС“Р Р…Р С”РЎвЂљР В°Р С Р СР ВµР Р…РЎР‹
  document.querySelectorAll('.sidebar .nav-item').forEach(a=>{
    a.addEventListener('click', ()=> close());
  });

  // ESC Р В·Р В°Р С”РЎР‚РЎвЂ№Р Р†Р В°Р ВµРЎвЂљ
  document.addEventListener('keydown', e=>{ if (e.key === 'Escape') close(); });

  // Р С—РЎР‚Р С‘ РЎР‚Р В°РЎРѓРЎв‚¬Р С‘РЎР‚Р ВµР Р…Р С‘Р С‘ Р С•Р С”Р Р…Р В° >900px РІР‚вЂќ Р С—РЎР‚Р С‘Р Р…РЎС“Р Т‘Р С‘РЎвЂљР ВµР В»РЎРЉР Р…Р С• Р В·Р В°Р С”РЎР‚РЎвЂ№РЎвЂљРЎРЉ Р СР С•Р В±Р С‘Р В»РЎРЉР Р…Р С•Р Вµ Р СР ВµР Р…РЎР‹
  const applyCloseOnWide = ()=>{ if (window.innerWidth > 900) close(); };
  window.addEventListener('resize', applyCloseOnWide);
})();
