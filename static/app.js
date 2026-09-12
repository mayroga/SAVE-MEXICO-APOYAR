const $=id=>document.getElementById(id);
const KEY="mexicano_apoya_mexicano_perfil";
const state={caso:"",servicio:"",pregunta_id:"",pregunta:null,respuestas:{},perfil:{},resultado:null,identificacion:[],historial:[],pdfTexto:""};

const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const txt=v=>String(v??"").trim();

async function api(url,opt={}){
 const r=await fetch(url,{headers:{"Content-Type":"application/json",...(opt.headers||{})},...opt});
 const d=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(d.detail||"No se pudo completar la acción.");
 return d;
}

function mostrar(id){
 document.querySelectorAll(".pantalla").forEach(x=>x.classList.remove("active"));
 $(id)?.classList.add("active");
 window.scrollTo({top:0,behavior:"smooth"});
}

function toast(t){
 const e=$("toast");if(!e)return;
 e.textContent=t;e.classList.add("show");
 clearTimeout(window._toast);
 window._toast=setTimeout(()=>e.classList.remove("show"),2600);
}

function guardarLocal(){
 try{localStorage.setItem(KEY,JSON.stringify(state.perfil||{}));}catch(e){}
}

function cargarLocal(){
 try{
  const p=JSON.parse(localStorage.getItem(KEY)||"{}");
  if(p&&typeof p==="object")state.perfil=p;
 }catch(e){state.perfil={};}
}

function borrarLocal(){
 try{localStorage.removeItem(KEY)}catch(e){}
 state.perfil={};
}

function campo(id,label,type="text",value=""){
 return `<label class="campo"><span>${esc(label)}</span><input id="id_${esc(id)}" data-id="${esc(id)}" type="${type}" value="${esc(value)}" autocomplete="off"></label>`;
}

function renderIdentificacion(){
 const p=state.perfil||{};
 $("identificacionCampos").innerHTML=
  campo("nombre_completo","Nombre y apellidos","text",p.nombre_completo)+
  campo("fecha_nacimiento","Fecha de nacimiento — DD/MM/AAAA","text",p.fecha_nacimiento)+
  campo("edad","Edad","number",p.edad)+
  campo("direccion","Dirección donde vives","text",p.direccion)+
  campo("estado","Estado","text",p.estado)+
  campo("codigo_postal","Código postal","text",p.codigo_postal)+
  campo("telefono","Teléfono","tel",p.telefono)+
  campo("trabajo","Trabajo u ocupación","text",p.trabajo||p.ocupacion||"");
}

function leerIdentificacion(){
 document.querySelectorAll("#identificacionCampos [data-id]").forEach(e=>{
  state.perfil[e.dataset.id]=txt(e.value);
 });
 const edad=parseInt(state.perfil.edad,10);
 if(Number.isFinite(edad))state.perfil.edad=edad;
}

function perfilNecesario(){
 const p=state.perfil||{};
 return [
  ["nombre_completo","Nombre y apellidos"],
  ["fecha_nacimiento","Fecha de nacimiento"],
  ["edad","Edad"],
  ["direccion","Dirección"],
  ["estado","Estado"],
  ["codigo_postal","Código postal"],
  ["telefono","Teléfono"]
 ].filter(x=>!txt(p[x[0]])).map(x=>x[1]);
}

function focoPerfil(nombre){
 const ids={
  "Nombre y apellidos":"nombre_completo",
  "Fecha de nacimiento":"fecha_nacimiento",
  "Edad":"edad",
  "Dirección":"direccion",
  "Estado":"estado",
  "Código postal":"codigo_postal",
  "Teléfono":"telefono"
 };
 $("id_"+(ids[nombre]||"nombre_completo"))?.focus();
}

async function cargarCatalogo(){
 try{
  const d=await api("/api/catalogo");
  const lista=Array.isArray(d)?d:(d.casos||d.tramites||d.catalogo||[]);
  renderCatalogo(lista);
 }catch(e){
  toast("No se pudo cargar la información.");
 }
}

function renderCatalogo(lista){
 const box=$("listaTramites");
 if(!box)return;
 box.innerHTML="";
 if(!Array.isArray(lista)||!lista.length){
  box.innerHTML="<p class='muted'>No hay trámites disponibles.</p>";
  return;
 }
 lista.forEach(x=>{
  const id=x.caso||x.id;
  if(!id)return;
  const b=document.createElement("button");
  b.className="tramite";
  b.type="button";
  b.innerHTML=`<strong>${esc(x.nombre||x.titulo||id)}</strong><small>${esc(x.descripcion||"Preparación y revisión del trámite.")}</small>`;
  b.onclick=()=>seleccionar(id,x.nombre||"");
  box.appendChild(b);
 });
}

async function seleccionar(caso,nombre){
 state.caso=caso;
 state.servicio=nombre;
 state.respuestas={};
 state.resultado=null;
 state.historial=[];
 const faltantes=perfilNecesario();
 if(faltantes.length){
  renderIdentificacion();
  mostrar("identificacion");
  return;
 }
 await comenzarCaso();
}

async function comenzarCaso(){
 try{
  const d=await api("/api/seleccionar-caso",{
   method:"POST",
   body:JSON.stringify({
    caso:state.caso,
    perfil:state.perfil,
    respuestas:state.respuestas
   })
  });
  aplicar(d);
 }catch(e){toast(e.message);}
}

async function guardarPerfil(){
 leerIdentificacion();
 const faltantes=perfilNecesario();
 if(faltantes.length){
  toast("Falta: "+faltantes[0]);
  focoPerfil(faltantes[0]);
  return;
 }
 guardarLocal();
 await comenzarCaso();
}

function guardarEstadoPregunta(){
 if(state.pregunta_id){
  state.historial.push({
   pregunta_id:state.pregunta_id,
   pregunta:state.pregunta,
   respuesta:state.respuestas[state.pregunta_id]
  });
 }
}

function aplicar(d){
 if(d.caso)state.caso=d.caso;
 if(d.servicio)state.servicio=d.servicio;
 if(d.perfil)state.perfil={...state.perfil,...d.perfil};
 if(d.respuestas)state.respuestas={...state.respuestas,...d.respuestas};

 if(d.resultado){
  state.resultado=d.resultado;
  renderResultado(d.resultado);
  return;
 }

 if(d.pregunta){
  state.pregunta=d.pregunta;
  state.pregunta_id=d.pregunta.id||d.pregunta_id||"";
  renderPregunta(d.pregunta);
  mostrar("preguntas");
 }
}

function renderPregunta(q){
 state.pregunta=q;
 $("tramiteTitulo").textContent=state.servicio||"Tu trámite";
 $("preguntaTexto").textContent=q.pregunta||q.texto||"";
 const paso=Number(q.paso||0),total=Number(q.total||0);
 $("paso").textContent=total?`${paso} de ${total}`:"";
 $("progresoBarra").style.width=total?`${Math.max(0,Math.min(100,(paso-1)/total*100))}%`:"0%";

 const box=$("opciones");
 box.innerHTML="";
 (q.opciones||[]).forEach(v=>{
  const label=document.createElement("label");
  label.className="opcion";
  label.innerHTML=`<input type="radio" name="q" value="${esc(v)}"><span>${esc(v)}</span>`;
  box.appendChild(label);
 });

 $("textoEntrada").value="";
 $("textoEntrada").placeholder=q.placeholder||"Escribe, pega o usa HABLAR.";
}

function obtenerRespuesta(){
 const radio=document.querySelector("input[name='q']:checked");
 const escrito=txt($("textoEntrada")?.value);
 return escrito||radio?.value||"";
}

function qRequerida(){
 return state.pregunta?.required===true;
}

async function continuar(){
 const v=obtenerRespuesta();

 if(qRequerida()&&!v){
  toast("Necesitamos esta respuesta.");
  return;
 }

 if(state.pregunta_id)state.respuestas[state.pregunta_id]=v;

 try{
  guardarEstadoPregunta();
  const d=await api("/api/continuar",{
   method:"POST",
   body:JSON.stringify({
    caso:state.caso,
    pregunta_id:state.pregunta_id,
    respuesta:v,
    texto:v,
    respuestas:state.respuestas,
    perfil:state.perfil
   })
  });
  aplicar(d);
 }catch(e){toast(e.message);}
}

function anteriorPregunta(){
 if(state.historial.length<2){
  mostrar("identificacion");
  return;
 }

 state.historial.pop();
 const anterior=state.historial[state.historial.length-1];
 if(!anterior)return;

 state.pregunta_id=anterior.pregunta_id;
 state.pregunta=anterior.pregunta;
 state.respuestas[state.pregunta_id]=anterior.respuesta||"";
 renderPregunta(anterior.pregunta);
 mostrar("preguntas");

 setTimeout(()=>{
  const v=anterior.respuesta||"";
  document.querySelectorAll("input[name='q']").forEach(x=>{
   if(x.value===v)x.checked=true;
  });
  if(!document.querySelector("input[name='q']:checked"))$("textoEntrada").value=v;
 },0);
}

async function hablar(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){
  toast("Tu navegador no permite usar el micrófono.");
  return;
 }
 const r=new SR();
 r.lang="es-MX";
 r.interimResults=false;
 r.continuous=false;
 r.onstart=()=>toast("Habla ahora...");
 r.onerror=()=>toast("No se pudo usar el micrófono.");
 r.onresult=e=>{
  $("textoEntrada").value=e.results?.[0]?.[0]?.transcript||"";
 };
 r.start();
}

async function pegar(){
 try{
  const t=await navigator.clipboard.readText();
  if(t){
   $("textoEntrada").value=t;
   toast("Información pegada.");
  }else toast("No hay texto para pegar.");
 }catch(e){
  $("textoEntrada").focus();
  toast("Pega la información directamente en el cuadro.");
 }
}

function renderLista(v){
 if(!Array.isArray(v)||!v.length)return "<p class='muted'>No hay información registrada.</p>";
 return `<ul class="lista-simple">${v.map(x=>{
  const t=typeof x==="string"?x:(x?.texto||x?.nombre||x?.descripcion||"");
  return t?`<li>${esc(t)}</li>`:"";
 }).join("")}</ul>`;
}

function renderDatos(v){
 if(!Array.isArray(v)||!v.length)return "<p class='muted'>No hay datos registrados.</p>";
 return `<ul class="lista-simple">${v.map(x=>`<li>${esc(typeof x==="string"?x:(x?.texto||x?.nombre||""))}</li>`).join("")}</ul>`;
}

function renderResultado(r){
 state.resultado=r||{};
 $("nombreResultado").textContent=r.nombre_tramite||"Tu trámite";

 const estado=r.estado||"REVISIÓN";
 $("estadoResultado").textContent=estado;

 let mensaje="Revisa cuidadosamente toda la información antes de finalizar.";
 if(estado==="INCOMPLETO")mensaje="Todavía hay información que debes completar.";
 if(estado==="REVISAR DATOS")mensaje="Hay datos que no coinciden o necesitan corrección.";
 if(estado==="PREPARADO PARA REVISIÓN")mensaje="La preparación está lista. Ahora revisa todo antes de guardar tu Hoja de Ruta.";

 $("mensajeResultado").textContent=mensaje;

 $("resultadoDatos").innerHTML=
  `<h3>TUS DATOS</h3>${renderDatos(r.datos)}`;

 $("resultadoNecesitas").innerHTML=
  `<h3>NECESITAS</h3>${renderLista(r.requisitos||r.originales)}`;

 const falt=r.faltantes||[];
 $("resultadoFaltantes").innerHTML=
  `<h3>${falt.length?"TE FALTA":"LO QUE ESTÁ COMPLETO"}</h3>`+
  (falt.length?renderLista(falt):"<p>No se detectan pendientes en la información proporcionada.</p>");

 const confirmar=r.confirmar||r.revision||[];
 $("resultadoAcciones").innerHTML=
  `<h3>REVISA Y CONFIRMA</h3>${renderLista(confirmar.length?confirmar:(r.acciones||[]))}`;

 const url=r.fuente||(r.fuentes?.[0]?.url)||"";
 const oficial=$("oficial");
 if(url){
  oficial.href=url;
  oficial.style.display="inline-flex";
 }else{
  oficial.style.display="none";
 }

 mostrar("resultado");
}

async function abrirPreview(){
 try{
  const r=await fetch("/api/pdf-preview",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    caso:state.caso,
    respuestas:state.respuestas,
    perfil:state.perfil
   })
  });
  if(!r.ok)throw Error("No se pudo preparar la vista previa.");
  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  window.open(url,"_blank","noopener");
  setTimeout(()=>URL.revokeObjectURL(url),60000);
 }catch(e){toast(e.message);}
}

async function descargarPDF(){
 try{
  const r=await fetch("/api/pdf",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    caso:state.caso,
    respuestas:state.respuestas,
    perfil:state.perfil
   })
  });
  if(!r.ok)throw Error("No se pudo preparar la Hoja de Ruta.");
  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download="Hoja_de_Ruta_EDITABLE.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1500);
 }catch(e){toast(e.message);}
}

async function leerPDF(){
 const input=$("archivoPdf");
 const mensaje=$("pdfMensaje");
 const texto=$("pdfTexto");
 if(!input?.files?.length){
  toast("Selecciona un PDF.");
  return;
 }

 const file=input.files[0];
 if(file.type!=="application/pdf"){
  toast("El archivo debe ser PDF.");
  return;
 }

 if(file.size>15*1024*1024){
  toast("El PDF no puede superar 15 MB.");
  return;
 }

 const fd=new FormData();
 fd.append("file",file);

 try{
  mensaje.textContent="Leyendo PDF...";
  const r=await fetch("/api/documento",{method:"POST",body:fd});
  const d=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(d.detail||"No se pudo leer el PDF.");

  state.pdfTexto=d.texto||"";
  texto.value=state.pdfTexto;

  if(state.pdfTexto){
   texto.classList.remove("oculto");
   mensaje.textContent="PDF leído. Revisa la información antes de utilizarla.";
   $("textoEntrada")?.focus();
   toast("PDF leído correctamente.");
  }else{
   mensaje.textContent="El PDF no contiene texto que pueda leerse automáticamente. Puedes copiar su información y pegarla.";
   texto.classList.add("oculto");
  }
 }catch(e){
  mensaje.textContent="";
  toast(e.message);
 }
}

function aceptarLegal(){
 const b=$("comenzar");
 if(b)b.disabled=!$("aceptarLegal")?.checked;
}

function nuevoTramite(){
 state.caso="";
 state.servicio="";
 state.pregunta_id="";
 state.pregunta=null;
 state.respuestas={};
 state.resultado=null;
 state.historial=[];
 mostrar("tramites");
}

function salir(){
 state.caso="";
 state.servicio="";
 state.pregunta_id="";
 state.pregunta=null;
 state.respuestas={};
 state.resultado=null;
 state.historial=[];
 mostrar("inicio");
}

function volverInicio(){
 mostrar("inicio");
}

function volverTramites(){
 mostrar("tramites");
}

function volverResultado(){
 if(state.pregunta){
  mostrar("preguntas");
 }else{
  mostrar("tramites");
 }
}

function init(){
 cargarLocal();
 cargarCatalogo();

 $("aceptarLegal")?.addEventListener("change",aceptarLegal);

 $("comenzar")?.addEventListener("click",()=>{
  if(!$("aceptarLegal")?.checked){
   toast("Primero debes leer y aceptar la información.");
   return;
  }
  mostrar("tramites");
 });

 $("guardarPerfil")?.addEventListener("click",guardarPerfil);
 $("continuar")?.addEventListener("click",continuar);
 $("voz")?.addEventListener("click",hablar);
 $("pegar")?.addEventListener("click",pegar);
 $("pdf")?.addEventListener("click",descargarPDF);
 $("pdfPreview")?.addEventListener("click",abrirPreview);
 $("leerPdf")?.addEventListener("click",leerPDF);
 $("nuevo")?.addEventListener("click",nuevoTramite);
 $("salir")?.addEventListener("click",salir);
 $("volverInicio")?.addEventListener("click",volverInicio);
 $("volverTramites")?.addEventListener("click",volverTramites);
 $("volverPregunta")?.addEventListener("click",anteriorPregunta);
 $("volverResultado")?.addEventListener("click",volverResultado);

 $("textoEntrada")?.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){
   e.preventDefault();
   continuar();
  }
 });

 mostrar("inicio");
}

document.addEventListener("DOMContentLoaded",init);
