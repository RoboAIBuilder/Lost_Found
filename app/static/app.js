(() => {
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const DAY = 86400000;
const PIN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>';

const S = {
  me:null, mode:"student", items:[], loaded:false, myClaims:[], staffClaims:[], cats:[],
  draft:{photos:[], ai:null, ctl:null, busy:false}, search:{results:null, busy:false, ctl:null, note:""},
  tab:"log", filter:"available", editing:null, confirmDel:null, claimItem:null, showAllRecent:false
};

/* ---------- helpers ---------- */
async function api(path, {method="GET", json, form, signal} = {}){
  const opts = {method, headers:{"X-Requested-With":"fetch"}, signal, credentials:"same-origin"};
  if(json){ opts.headers["Content-Type"]="application/json"; opts.body=JSON.stringify(json); }
  if(form) opts.body = form;
  const r = await fetch(path, opts);
  let body = null; try{ body = await r.json(); }catch{}
  if(r.status===401 && path!=="/api/me"){ location.reload(); throw new Error("signed out"); }
  if(!r.ok) throw Object.assign(new Error((body && body.error) || "Something went wrong. Try again."), {status:r.status});
  return body;
}
const fmtDate = ms => ms ? new Date(ms).toLocaleDateString(undefined,{month:"short",day:"numeric"}) : "";
const age = ms => Math.floor((Date.now()-ms)/DAY);
const ago = ms => { const d=age(ms); return d<=0 ? "today" : d===1 ? "yesterday" : d+" days ago"; };
const itemById = id => S.items.find(i=>i.id===id);
let toastT;
function toast(msg){ const t=$("#toast"); t.textContent=msg; t.hidden=false; clearTimeout(toastT); toastT=setTimeout(()=>t.hidden=true,4200); }
const isStaff = () => S.me && S.me.role==="staff";

/* ---------- boot ---------- */
async function boot(){
  const me = await api("/api/me").catch(()=>null);
  if(!me || !me.signedIn) return showSignIn(me || {});
  S.me = me; S.cats = me.categories || [];
  $("#fCat").innerHTML = S.cats.map(c=>`<option>${esc(c)}</option>`).join("");
  $("#signin").hidden = true; $("#app").hidden = false; $("#signOut").hidden = false;
  S.mode = isStaff() ? "staff" : "student";
  renderShots(); render(); await loadAll();
  setInterval(()=>{ if(!document.hidden) loadAll(); }, 60000);
  document.addEventListener("visibilitychange", ()=>{ if(!document.hidden) loadAll(); });
}
function showSignIn(me){
  $("#app").hidden = true; $("#signin").hidden = false; $("#rolePill").textContent = "Signed out";
  const err = new URLSearchParams(location.search).get("error");
  $("#signinErr").hidden = err!=="domain";
  $("#googleBtn").hidden = !me.googleLogin;
  $("#devLogins").hidden = !me.devLogin;
  $("#noLogin").hidden = !!(me.googleLogin || me.devLogin);
}
async function loadAll(){
  try{
    const jobs = [api("/api/items"), api("/api/claims/mine")];
    if(isStaff()) jobs.push(api("/api/claims"));
    const [items, mine, staff] = await Promise.all(jobs);
    S.items = items; S.myClaims = mine; S.staffClaims = staff || []; S.loaded = true;
    render();
  }catch(e){ if(e.message!=="signed out") toast("Couldn't load items. Check your connection."); }
}

/* ---------- render ---------- */
function render(){
  const staffMode = isStaff() && S.mode==="staff";
  $("#studentView").hidden = staffMode; $("#staffView").hidden = !staffMode;
  $("#rolePill").textContent = isStaff() ? (staffMode ? "Office staff" : "Staff · student preview") : "Student";
  const mb=$("#modeBtn"); mb.hidden=!isStaff(); mb.textContent = staffMode ? "Preview student view" : "Back to staff tools";
  staffMode ? renderStaff() : renderStudent();
}
function statusPill(st){
  const t = {pending:"Claim sent · waiting for office", approved:"Approved · pick up at the office", declined:"Not approved"}[st] || st;
  return `<span class="st ${esc(st)}">${esc(t)}</span>`;
}
function cardHTML(it, {why, conf, staff} = {}){
  const ph = it.photos||[], d = age(it.found_at);
  let foot;
  if(staff){
    const pend = S.staffClaims.filter(c=>c.item_id===it.id && c.status==="pending").length;
    const editing = S.editing===it.id;
    foot = `<div class="body" style="padding-top:0"><div class="loc">${PIN}<div class="val"><b>Stored at</b>${editing
      ? `<div class="locedit"><input type="text" id="loc-${esc(it.id)}" value="${esc(it.location)}" aria-label="Storage spot"><button class="btn sm" data-action="saveLoc" data-id="${esc(it.id)}">Save</button></div>`
      : `${esc(it.location||"Not set")} <button class="linkish" data-action="editLoc" data-id="${esc(it.id)}">Change</button>`}</div></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">${it.status==="returned" ? `<span class="st returned">Returned ${fmtDate(it.returned_at)}</span>`
        : d>=30 ? `<span class="st old">${d} days · donate soon</span>` : `<span class="st available">On the shelf</span>`}
      ${pend ? `<span class="st pending">${pend} claim${pend>1?"s":""}</span>` : ""}</div></div>
      <div class="foot">${it.status==="returned"
        ? `<button class="btn sec sm" data-action="markAvail" data-id="${esc(it.id)}">Put back on shelf</button>`
        : `<button class="btn sec sm" data-action="markReturned" data-id="${esc(it.id)}">Mark returned</button>`}
      <button class="btn bad sm" data-action="delItem" data-id="${esc(it.id)}">${S.confirmDel===it.id ? "Confirm delete" : "Delete"}</button></div>`;
  } else {
    const mine = S.myClaims.find(c=>c.item_id===it.id);
    foot = `<div class="foot">${mine ? statusPill(mine.status) : `<button class="btn sm" data-action="claim" data-id="${esc(it.id)}">This is mine</button>`}</div>`;
  }
  return `<article class="card">
    <button class="ph" data-action="photos" data-id="${esc(it.id)}" aria-label="View photos of ${esc(it.title)}">
      ${ph.length ? `<img src="${esc(ph[0])}" alt="" loading="lazy">` : `<span class="noph">No photo</span>`}
      <span class="tag">${esc(it.tag)}</span>${ph.length>1 ? `<span class="more">+${ph.length-1}</span>` : ""}
    </button>
    <div class="body">
      <h3>${esc(it.title||"Unlabeled item")}</h3>
      ${why ? `<p class="why"><span class="conf ${esc(conf)}">${esc(conf)}</span>${esc(why)}</p>` : ""}
      <p class="desc">${esc(it.description||"")}</p>
      <p class="meta">Found ${fmtDate(it.found_at)} · ${ago(it.found_at)}${it.found_where ? " · "+esc(it.found_where) : ""}</p>
    </div>${foot}</article>`;
}
function renderStudent(){
  const avail = S.items.filter(i=>i.status!=="returned");
  const rec = $("#recent");
  if(!S.loaded) rec.innerHTML = `<div class="status"><span class="spin"></span>Loading items…</div>`;
  else if(!avail.length) rec.innerHTML = `<div class="empty"><strong>Nothing has been turned in yet</strong>When the office logs a found item, it shows up here.</div>`;
  else {
    const list = S.showAllRecent ? avail : avail.slice(0,8);
    rec.innerHTML = `<div class="grid">${list.map(i=>cardHTML(i)).join("")}</div>` +
      (avail.length>8 ? `<p style="margin-top:14px"><button class="btn sec sm" data-action="toggleRecent">${S.showAllRecent ? "Show fewer" : `Show all ${avail.length} items`}</button></p>` : "");
  }
  $("#recentNote").textContent = S.loaded && avail.length ? `${avail.length} item${avail.length>1?"s":""} waiting for owners` : "";
  const rs = S.search;
  $("#resultsSec").hidden = !rs.results;
  const ex = $("#aiExpand");
  if(rs.results){
    $("#resultsNote").textContent = rs.note;
    const found = rs.results.map(r=>[r,itemById(r.id)]).filter(([,it])=>it);
    const canAi = rs.mode==="keyword" && rs.aiAvailable;
    $("#results").innerHTML = found.length
      ? `<div class="grid">${found.map(([r,it])=>cardHTML(it,{why:r.reason,conf:r.confidence})).join("")}</div>`
      : canAi ? `<div class="empty"><strong>No items match those words</strong>AI can look for items described differently.</div>`
      : `<div class="empty"><strong>No match yet</strong>Nothing turned in looks like that. Check back in a few days, or add more detail like brand, size, or stickers.</div>`;
    // Offer AI only after a keyword search, so it's used for the hard cases
    ex.hidden = !canAi;
    // weak word matches: put the AI offer above them so students see it first
    const weak = !rs.results.some(r=>r.confidence!=="low");
    weak ? $("#results").before(ex) : $("#results").after(ex);
    if(canAi){
      const left = rs.aiLeft;
      ex.innerHTML = left===0
        ? `<p><b>Don't see yours?</b><span class="meta">You've used today's AI searches. Try again tomorrow, or ask the office.</span></p>`
        : `<p><b>${found.length ? "Don't see yours?" : "Try a smarter search"}</b><span class="meta">AI reads every item on the shelf and catches things described in different words.${left!=null ? ` ${left} AI search${left===1?"":"es"} left today.` : ""}</span></p>
           <button class="btn" data-action="aiSearch" ${rs.busy?"disabled":""}>Search with AI</button>`;
    }
  } else ex.hidden = true;
  $("#myClaimsSec").hidden = !S.myClaims.length;
  $("#myClaims").innerHTML = S.myClaims.map(c=>{
    const msg = c.status==="approved" ? `Go to the office and ask for <span class="mono">${esc(c.tag)}</span>.`
      : c.status==="declined" ? `The office didn't approve this claim. ${c.note ? esc(c.note)+". " : ""}Talk to them if you think it's a mistake.`
      : "The office will compare your details with the item.";
    return `<div class="crow"><div class="thumb">${c.photo ? `<img src="${esc(c.photo)}" alt="">` : ""}</div>
      <div class="info"><div class="top"><h3>${esc(c.title)}</h3><span class="mono">${esc(c.tag)}</span></div>
      <div>${statusPill(c.status)}</div><p class="meta">${msg}</p></div></div>`;
  }).join("");
  $("#searchBtn").disabled = rs.busy;
  $("#searchStatus").innerHTML = rs.busy ? `<span class="spin"></span>${rs.busy==="ai" ? "AI is checking every item on the shelf…" : "Searching…"}` : "";
}
function renderStaff(){
  document.querySelectorAll(".tab").forEach(t=>t.setAttribute("aria-selected", String(t.dataset.tab===S.tab)));
  ["log","inv","claims"].forEach(t=>$("#tab-"+t).hidden = S.tab!==t);
  $("#invCount").textContent = S.items.filter(i=>i.status!=="returned").length;
  const pending = S.staffClaims.filter(c=>c.status==="pending");
  const cc=$("#claimCount"); cc.hidden=!pending.length; cc.textContent=pending.length;
  $("#locs").innerHTML = [...new Set(S.items.map(i=>i.location).filter(Boolean))].slice(0,30).map(l=>`<option value="${esc(l)}">`).join("");
  $("#saveBtn").disabled = S.draft.busy;
  document.querySelectorAll("[data-action=filter]").forEach(b=>b.setAttribute("aria-pressed", String(b.dataset.f===S.filter)));
  const f = S.filter;
  const list = S.items.filter(i => f==="all" ? true : f==="returned" ? i.status==="returned" : f==="old" ? (i.status!=="returned" && age(i.found_at)>=30) : i.status!=="returned");
  $("#invNote").textContent = S.loaded ? `${list.length} item${list.length===1?"":"s"}` : "";
  $("#inventory").innerHTML = !S.loaded ? `<div class="status"><span class="spin"></span>Loading items…</div>`
    : list.length ? `<div class="grid">${list.map(i=>cardHTML(i,{staff:true})).join("")}</div>`
    : `<div class="empty"><strong>${S.items.length ? "Nothing in this view" : "No items logged yet"}</strong>${S.items.length ? "Try another filter." : "Use Log an item to add the first one."}</div>`;
  $("#staffClaims").innerHTML = S.staffClaims.length ? S.staffClaims.map(c=>`<div class="crow">
      <div class="thumb">${c.photo ? `<button class="ph" style="aspect-ratio:1" data-action="photos" data-id="${esc(c.item_id)}" aria-label="View photos"><img src="${esc(c.photo)}" alt=""></button>` : ""}</div>
      <div class="info">
        <div class="top"><h3>${esc(c.title)}</h3><span class="mono">${esc(c.tag)}</span><span class="st ${esc(c.status)}">${{pending:"Needs review",approved:"Approved",declined:"Declined"}[c.status]||esc(c.status)}</span></div>
        <p><b>${esc(c.name)}</b>${c.grade ? " · "+esc(c.grade) : ""} <span class="meta">· ${esc(c.email)} · ${ago(c.created_at)}</span></p>
        <p class="proof">${esc(c.proof)}</p>
        <p class="compare">Item on file: ${esc(c.item_description||c.title)}</p>
        <div class="loc">${PIN}<div class="val"><b>Stored at</b>${esc(c.location)}</div></div>
        ${c.status==="pending" ? `<div class="acts">
          ${c.item_status!=="returned" ? `<button class="btn ok sm" data-action="approve" data-id="${c.id}">Approve &amp; mark returned</button>` : ""}
          <button class="btn bad sm" data-action="decline" data-id="${c.id}">Decline</button></div>` : ""}
      </div></div>`).join("")
    : `<div class="empty"><strong>No claims yet</strong>When a student says an item is theirs, it lands here for you to check.</div>`;
}

/* ---------- staff: logging ---------- */
function renderShots(){
  const ph = S.draft.photos;
  let h = ph.map((p,i)=>`<div class="shot has"><img src="${p.url}" alt="Photo ${i+1}"><button type="button" class="x" data-action="rmShot" data-i="${i}" aria-label="Remove photo ${i+1}">×</button></div>`).join("");
  for(let i=ph.length;i<3;i++) h += i===ph.length
    ? `<label class="shot addph" for="photoIn">${i===0 ? "Tap to take or add photos" : "Add another"}<input type="file" id="photoIn" accept="image/*" capture="environment" multiple></label>`
    : `<div class="shot" aria-hidden="true">Photo ${i+1}</div>`;
  $("#shots").innerHTML = h;
}
async function shrink(file, max=1600){
  const url = URL.createObjectURL(file);
  try{
    const img = await new Promise((res,rej)=>{ const i=new Image(); i.onload=()=>res(i); i.onerror=rej; i.src=url; });
    const s = Math.min(1, max/Math.max(img.naturalWidth,img.naturalHeight));
    const c = document.createElement("canvas"); c.width=Math.round(img.naturalWidth*s); c.height=Math.round(img.naturalHeight*s);
    c.getContext("2d").drawImage(img,0,0,c.width,c.height);
    return await new Promise(r=>c.toBlob(r,"image/jpeg",0.85));
  } finally { URL.revokeObjectURL(url); }
}
async function addPhotos(files){
  $("#logErr").textContent="";
  for(const f of files){
    if(S.draft.photos.length>=3) break;
    try{ const blob = await shrink(f); if(blob) S.draft.photos.push({blob,url:URL.createObjectURL(blob)}); }
    catch{ $("#logErr").textContent = "One photo couldn't be opened. Try a JPEG or PNG."; }
  }
  renderShots(); scheduleDescribe();
}
// One AI call per item: wait until staff stop adding photos, then describe once.
let describeTimer;
function scheduleDescribe(){
  clearTimeout(describeTimer);
  if(!S.draft.photos.length){ setAi("Add photos and the description fills in automatically."); return; }
  if(!S.me.ai){ setAi("AI isn't set up on this server. Type a name and details.","warn"); return; }
  if(S.draft.described){
    setAi(`Filled in from the photos. Fix anything that's off. <button type="button" class="linkish" data-action="redescribe">Read the photos again</button>`,"ok");
    return;
  }
  setAi(S.draft.photos.length<3 ? "Add more photos, or wait a moment and AI will read these." : `<span class="spin"></span>Reading the photos…`);
  describeTimer = setTimeout(()=>describe(), S.draft.photos.length>=3 ? 0 : 2500);
}
// "Sweatshirt, Jacket,  pull-over;Nike" -> ["sweatshirt","jacket","pull-over","nike"]
const parseKeywords = s => [...new Set(String(s).split(/[,;\n]+/).map(w=>w.trim().toLowerCase()).filter(Boolean))].slice(0,16);
const setAi = (html, cls="") => { const a=$("#aiStatus"); a.className="ai "+cls; a.innerHTML=html; };
function photoForm(){ const fd = new FormData(); S.draft.photos.forEach((p,i)=>fd.append("photos", p.blob, `photo${i+1}.jpg`)); return fd; }
async function describe(){
  clearTimeout(describeTimer);
  if(!S.draft.photos.length || !S.me.ai) return scheduleDescribe();
  if(S.draft.busyAi) return;
  if(S.draft.ctl) S.draft.ctl.abort();
  const ctl = new AbortController(); S.draft.ctl = ctl; S.draft.busyAi = true;
  setAi(`<span class="spin"></span>Reading the photos…`);
  try{
    const out = await api("/api/describe",{method:"POST", form:photoForm(), signal:ctl.signal});
    const fill = (id,v)=>{ const el=$(id); if(v && !el.dataset.touched) el.value=String(v).slice(0,400); };
    fill("#fTitle", out.title); fill("#fColor", out.color);
    fill("#fDesc", [out.brand && !String(out.description||"").toLowerCase().includes(String(out.brand).toLowerCase()) ? out.brand+"." : "", out.description].filter(Boolean).join(" "));
    if(S.cats.includes(out.category) && !$("#fCat").dataset.touched) $("#fCat").value = out.category;
    if(Array.isArray(out.keywords)) fill("#fKw", out.keywords.map(String).join(", "));
    S.draft.ai = {brand:out.brand||""}; S.draft.described = true;
    scheduleDescribe();
  }catch(e){
    if(e.name==="AbortError") return;
    setAi(esc(e.message),"warn");
  }finally{ S.draft.busyAi = false; }
}
function resetLog(){
  S.draft.ctl && S.draft.ctl.abort(); clearTimeout(describeTimer);
  S.draft.photos.forEach(p=>URL.revokeObjectURL(p.url));
  S.draft = {photos:[], ai:null, ctl:null, busy:false};
  ["#fTitle","#fColor","#fDesc","#fWhere","#fCat","#fKw"].forEach(id=>{ const el=$(id); delete el.dataset.touched; if(el.tagName!=="SELECT") el.value=""; });
  $("#fCat").selectedIndex = 0; $("#logErr").textContent="";
  renderShots(); setAi("Add photos and the description fills in automatically.");
}
async function saveItem(){
  const err=$("#logErr"); err.textContent="";
  const loc=$("#fLoc").value.trim(), title=$("#fTitle").value.trim();
  if(!S.draft.photos.length) return err.textContent="Add at least one photo.";
  if(!loc){ $("#fLoc").focus(); return err.textContent="Say where you're storing it."; }
  if(!title){ $("#fTitle").focus(); return err.textContent="Give the item a name."; }
  S.draft.busy=true; $("#saveBtn").textContent="Saving…"; render();
  const fd = photoForm();
  fd.append("title",title); fd.append("category",$("#fCat").value); fd.append("color",$("#fColor").value.trim());
  fd.append("description",$("#fDesc").value.trim()); fd.append("location",loc); fd.append("found_where",$("#fWhere").value.trim());
  fd.append("brand",(S.draft.ai&&S.draft.ai.brand)||""); fd.append("keywords",JSON.stringify(parseKeywords($("#fKw").value)));
  try{
    const r = await api("/api/items",{method:"POST", form:fd});
    resetLog(); toast(`Saved. Write ${r.tag} on a sticky note and put it with the item.`); loadAll();
  }catch(e){ err.textContent = e.message; }
  finally{ S.draft.busy=false; $("#saveBtn").textContent="Save item"; render(); }
}

/* ---------- student: search & claim ---------- */
// Word search first (free). AI only when the student asks for it.
async function runSearch(ai=false){
  const q = ai ? (S.search.q || $("#q").value.trim()) : $("#q").value.trim();
  if(!q){ $("#q").focus(); return; }
  const rs = S.search; if(rs.ctl) rs.ctl.abort();
  const ctl = new AbortController(); rs.ctl = ctl; rs.busy = ai ? "ai" : "word"; render();
  try{
    const out = await api("/api/search",{method:"POST", json:{q, ai}, signal:ctl.signal});
    Object.assign(rs, {results:out.matches, note:out.note, mode:out.mode, aiAvailable:out.aiAvailable, aiLeft:out.aiLeft, q});
  }catch(e){
    if(e.name==="AbortError") return;
    if(ai){ toast(e.message); if(e.status===429) rs.aiLeft = 0; }   // keep the word results on screen
    else { rs.results=[]; rs.note=e.message; rs.mode="keyword"; }
  }
  rs.busy=false; render();
  $("#resultsSec").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block:"start"});
}
function openClaim(id){
  const it=itemById(id); if(!it) return; S.claimItem=it;
  $("#cTitle").textContent = "Claim: "+(it.title||"item");
  $("#cSub").textContent = `${it.tag} · found ${fmtDate(it.found_at)}`;
  if(!$("#cName").value) $("#cName").value = S.me.name || "";
  $("#cProof").value=""; $("#cErr").textContent="";
  $("#claimModal").hidden=false; setTimeout(()=>$("#cProof").focus(),30);
}
async function submitClaim(){
  const it=S.claimItem; if(!it) return;
  const btn=$("#cSubmit"); btn.disabled=true; btn.textContent="Sending…";
  try{
    await api("/api/claims",{method:"POST", json:{item_id:it.id, name:$("#cName").value.trim(), grade:$("#cGrade").value.trim(), proof:$("#cProof").value.trim()}});
    $("#claimModal").hidden=true; toast("Claim sent. The office will check it."); loadAll();
  }catch(e){ $("#cErr").textContent=e.message; }
  finally{ btn.disabled=false; btn.textContent="Send claim"; }
}

/* ---------- lightbox ---------- */
function openPhotos(id){
  const it=itemById(id); if(!it || !(it.photos||[]).length) return;
  const lb=$("#lightbox");
  lb.innerHTML = `<div class="lb">${it.photos.map(p=>`<img src="${esc(p)}" alt="">`).join("")}<div class="cap"><span><span class="mono">${esc(it.tag)}</span> · ${esc(it.title)}</span><button class="btn sec sm" data-action="closeLb">Close</button></div></div>`;
  lb.hidden=false;
}

/* ---------- events ---------- */
async function act(fn, ok){ try{ await fn(); if(ok) toast(ok); }catch(e){ toast(e.message); } loadAll(); }
document.addEventListener("click", async e=>{
  const el = e.target.closest("[data-action]"); const a = el && el.dataset.action;
  if(a!=="delItem" && S.confirmDel){ S.confirmDel=null; if(!a) render(); }
  if(!a) return;
  const id = el.dataset.id;
  switch(a){
    case "example": $("#q").value = el.textContent; runSearch(); break;
    case "aiSearch": runSearch(true); break;
    case "redescribe": S.draft.described=false; describe(); break;
    case "claim": openClaim(id); break;
    case "closeModal": $("#claimModal").hidden=true; break;
    case "photos": openPhotos(id); break;
    case "closeLb": if(e.target===el || el.tagName==="BUTTON") $("#lightbox").hidden=true; break;
    case "toggleRecent": S.showAllRecent=!S.showAllRecent; render(); break;
    case "tab": S.tab=el.dataset.tab; S.editing=null; render(); break;
    case "filter": S.filter=el.dataset.f; render(); break;
    case "rmShot": { const p=S.draft.photos.splice(+el.dataset.i,1)[0]; p && URL.revokeObjectURL(p.url); renderShots(); if(!S.draft.described) scheduleDescribe(); else if(!S.draft.photos.length){ S.draft.described=false; scheduleDescribe(); } break; }
    case "resetLog": resetLog(); $("#fLoc").value=""; break;
    case "editLoc": S.editing=id; render(); setTimeout(()=>{ const i=$("#loc-"+CSS.escape(id)); i && i.focus(); },0); break;
    case "saveLoc": { const v=$("#loc-"+CSS.escape(id)).value.trim(); S.editing=null; render(); if(v) act(()=>api(`/api/items/${id}`,{method:"PATCH",json:{location:v}}),"Storage spot updated."); break; }
    case "markReturned": act(()=>api(`/api/items/${id}`,{method:"PATCH",json:{status:"returned"}}),"Marked returned."); break;
    case "markAvail": act(()=>api(`/api/items/${id}`,{method:"PATCH",json:{status:"available"}}),"Back on the shelf."); break;
    case "delItem":
      if(S.confirmDel!==id){ S.confirmDel=id; render(); break; }
      S.confirmDel=null; act(()=>api(`/api/items/${id}`,{method:"DELETE"}),"Item deleted."); break;
    case "approve": el.disabled=true; act(()=>api(`/api/claims/${id}/decide`,{method:"POST",json:{approve:true}}),"Approved. Hand the item over and you're done."); break;
    case "decline": el.disabled=true; act(()=>api(`/api/claims/${id}/decide`,{method:"POST",json:{approve:false}}),"Claim declined."); break;
  }
});
$("#modeBtn").addEventListener("click",()=>{ S.mode = S.mode==="staff" ? "student" : "staff"; render(); });
$("#askForm").addEventListener("submit",e=>{ e.preventDefault(); runSearch(); });
$("#q").addEventListener("keydown",e=>{ if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); runSearch(); } });
$("#claimForm").addEventListener("submit",e=>{ e.preventDefault(); submitClaim(); });
$("#logForm").addEventListener("submit",e=>{ e.preventDefault(); saveItem(); });
$("#shots").addEventListener("change",e=>{ if(e.target.id==="photoIn" && e.target.files.length) addPhotos([...e.target.files]); });
["#fTitle","#fColor","#fDesc","#fCat","#fKw"].forEach(id=>$(id).addEventListener("input",ev=>ev.target.dataset.touched="1"));
$("#claimModal").addEventListener("click",e=>{ if(e.target.id==="claimModal") $("#claimModal").hidden=true; });
document.addEventListener("keydown",e=>{
  if(e.key==="Escape"){ $("#claimModal").hidden=true; $("#lightbox").hidden=true; }
  if(e.key==="Enter" && e.target.id && e.target.id.startsWith("loc-")){ e.preventDefault(); const b=e.target.parentElement.querySelector("[data-action=saveLoc]"); b && b.click(); }
});

boot();
})();
