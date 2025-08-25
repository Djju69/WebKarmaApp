const S={get:(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}},set:(k,v)=>localStorage.setItem(k,JSON.stringify(v))};
const DEF_CARDS=[
  {id:"c1",name:"Кафе «Ваниль»",category:"Кафе",district:"Центральный",status:"Опубликовано",createdAt:Date.now()-3e7},
  {id:"c2",name:"Кафе «Триндово»",category:"Ресторан",district:"Северный",status:"На модерации",createdAt:Date.now()-2e7},
  {id:"c3",name:"«Атлет»",category:"Фитнес",district:"Западный",status:"Черновик",createdAt:Date.now()-1e7}
];
let cards=S.get("ks_cards",DEF_CARDS.slice());
const qs=s=>document.querySelector(s),uid=(p="id")=>p+Math.random().toString(36).slice(2,9);
const statusClass=s=>/опублик/i.test(s)?"ok":/модера/i.test(s)?"warn":/черновик/i.test(s)?"muted":"muted";
function updateBadges(){qs("#stat-total").textContent=cards.length;qs("#stat-pub").textContent=cards.filter(x=>/опублик/i.test(x.status)).length;qs("#stat-draft").textContent=cards.filter(x=>/черновик/i.test(x.status)).length;qs("#stat-mod").textContent=cards.filter(x=>/модера/i.test(x.status)).length}
function filters(){return{term:(qs("#search")?.value||"").trim().toLowerCase(),cat:qs("#filter-category")?.value||"",dist:qs("#filter-district")?.value||"",st:qs("#filter-status")?.value||"",sort:qs("#sort")?.value||"created_desc"}}
function list(){const tbody=qs("#cards-list"); if(!tbody) return; const f=filters(); let arr=cards.filter(r=>(!f.term||r.name.toLowerCase().includes(f.term))&&(!f.cat||r.category===f.cat)&&(!f.dist||r.district===f.dist)&&(!f.st||r.status===f.st));
  switch(f.sort){case"created_asc":arr.sort((a,b)=>a.createdAt-b.createdAt);break;case"created_desc":arr.sort((a,b)=>b.createdAt-a.createdAt);break;case"name_asc":arr.sort((a,b)=>a.name.localeCompare(b.name,"ru"));break;case"name_desc":arr.sort((a,b)=>b.name.localeCompare(a.name,"ru"));break;case"status":arr.sort((a,b)=>a.status.localeCompare(b.status,"ru"));break;}
  tbody.innerHTML=arr.map(c=>`<tr data-id="${c.id}"><td>${c.name}</td><td>${c.category}</td><td>${c.district}</td><td><span class="chip ${statusClass(c.status)}">${c.status}</span></td><td class="right"><a href="#" data-act="edit" class="link">Редактировать</a> · ${/опублик/i.test(c.status)?`<a href="#" data-act="unpub" class="link">Снять с публикации</a>`:`<a href="#" data-act="pub" class="link">Опубликовать</a>`} · <a href="#" data-act="del" class="link">Удалить</a></td></tr>`).join(""); updateBadges();}
function openForm(id){const f=qs("#card-form"); f.classList.remove("hidden"); f.dataset.editId=id||""; if(id){const c=cards.find(x=>x.id===id); if(!c) return; qs("#f-name").value=c.name; qs("#f-category").value=c.category; qs("#f-district").value=c.district; qs("#f-status").value=c.status;}else{qs("#f-name").value="";qs("#f-category").value="Кафе";qs("#f-district").value="Центральный";qs("#f-status").value="Опубликовано";}}
function closeForm(){const f=qs("#card-form"); f.classList.add("hidden"); f.dataset.editId="";}
function saveForm(e){e.preventDefault(); const name=(qs("#f-name")?.value||"").trim(); if(!name) return alert("Название обязательно"); const data={name,category:qs("#f-category")?.value||"Кафе",district:qs("#f-district")?.value||"Центральный",status:qs("#f-status")?.value||"Опубликовано"}; const id=qs("#card-form").dataset.editId; if(id){const i=cards.findIndex(x=>x.id===id); if(i>=0) cards[i]={...cards[i],...data};} else {cards.unshift({id:uid("c"),createdAt:Date.now(),...data});} S.set("ks_cards",cards); list(); closeForm();}
function setPub(id,val){const c=cards.find(x=>x.id===id); if(!c) return; c.status=val?"Опубликовано":"Черновик"; S.set("ks_cards",cards); list();}
function delCard(id){ if(!confirm("Удалить карточку?")) return; cards=cards.filter(x=>x.id!==id); S.set("ks_cards",cards); list(); }
document.addEventListener("click",e=>{const a=e.target.closest("a,button"); if(!a) return;
  if(a.id==="btn-create"){e.preventDefault(); openForm(""); return;}
  if(a.id==="cancel-card"){e.preventDefault(); closeForm(); return;}
  if(a.id==="save-card"){return;}
  if(a.dataset.act){e.preventDefault(); const tr=a.closest("tr"), id=tr?.dataset.id; if(!id) return; if(a.dataset.act==="edit") openForm(id); if(a.dataset.act==="pub") setPub(id,true); if(a.dataset.act==="unpub") setPub(id,false); if(a.dataset.act==="del") delCard(id); return;}
  if(a.id==="btn-export"){e.preventDefault(); const blob=new Blob([JSON.stringify(cards,null,2)],{type:"application/json"}); const url=URL.createObjectURL(blob); const link=document.createElement("a"); link.href=url; link.download="cards.json"; link.click(); URL.revokeObjectURL(url);}
});
document.addEventListener("change",e=>{const el=e.target; if(el.id==="imp"&&el.files&&el.files[0]){const r=new FileReader(); r.onload=()=>{try{const arr=JSON.parse(r.result); if(Array.isArray(arr)){cards=arr; S.set("ks_cards",cards); list();} else alert("Неверный JSON");}catch{alert("Ошибка JSON")}}; r.readAsText(el.files[0],"utf-8");}});
["#search","#filter-category","#filter-district","#filter-status","#sort"].forEach(sel=>{const el=qs(sel); if(!el) return; el.addEventListener(sel==="#search"?"input":"change", list);});
document.addEventListener("submit",e=>{if((e.target&&e.target.id)==="card-form") saveForm(e);});
document.addEventListener("DOMContentLoaded", list);
