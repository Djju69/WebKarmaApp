document.addEventListener("DOMContentLoaded", () => {
  // Mobile menu
  const toggle = document.querySelector(".nav-toggle");
  const header = document.querySelector(".site-header");
  toggle?.addEventListener("click", () => header?.classList.toggle("open"));

  // Наполнение карусели
  const ADS = [
    {title:"-20% на кофе", desc:"Сегодня в «У Ашота» до 18:00", tag:"Кафе"},
    {title:"Бесплатный десерт", desc:"При заказе от 800 ₽", tag:"Ресторан"},
    {title:"3 визита = абонемент -30%", desc:"Фитнес «Атлет»", tag:"Фитнес"},
    {title:"-10% для новых гостей", desc:"«МариВанна»", tag:"Ресторан"},
    {title:"Happy Hours", desc:"С 16:00 до 18:00", tag:"Кафе"},
    {title:"Купон -200 ₽", desc:"На первый заказ", tag:"Доставка"}
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
          <a class="btn" style="padding:6px 10px" href="/cabinet">Подробнее</a>
        </div>
      </article>
    `).join("");
  }

  // Кнопки карусели
  const scroller = document.getElementById("adsCarousel");
  const prev = document.querySelector('.carousel-btn[data-dir="prev"]');
  const next = document.querySelector('.carousel-btn[data-dir="next"]');
  function scrollByOne(dir=1){
    if (!track) return;
    const card = track.querySelector(".carousel-card");
    if (!card) return;
    const step = card.getBoundingClientRect().width + 16; // ширина + gap
    track.scrollBy({left: step * dir, behavior: "smooth"});
  }
  prev?.addEventListener("click", ()=>scrollByOne(-1));
  next?.addEventListener("click", ()=>scrollByOne(1));

  // Свайп на мобиле
  let sx=0, sl=0, dragging=false;
  track?.addEventListener("pointerdown", e=>{dragging=true; sx=e.clientX; sl=track.scrollLeft; track.setPointerCapture(e.pointerId);});
  track?.addEventListener("pointermove", e=>{ if(!dragging) return; track.scrollLeft = sl - (e.clientX - sx);});
  track?.addEventListener("pointerup",   ()=>{dragging=false});
  track?.addEventListener("pointercancel",()=>{dragging=false});
});