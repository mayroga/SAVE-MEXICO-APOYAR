const $=id=>document.getElementById(id);
const KEY="mexicano_apoya_mexicano_perfil";

const state={
 caso:"",servicio:"",pregunta_id:"",pregunta:null,
 respuestas:{},perfil:{},resultado:null,
 historial:[],pdfTexto:"",pdfUrl:""
};

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
 window._toast=setTimeout(()=>e.classList.remove("show"),2800);
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
 }catch(e){toast("No se pudo cargar la información.");}
}

function renderCatalogo(lista){
 const box=$("listaTramites");
 if(!box)return;
 box.innerHTML="";
 if(!lista.length){
  box.innerHTML="<p class='muted'>No hay trámites disponibles.</p>";
  return;
 }
 lista.forEach(x=>{
  const id=x.caso||x.id;
  if(!id)return;
  const b=document.createElement("button");
  b.className="tramite";
  b.type="button";
  b.innerHTML=`<strong>${esc(x.nombre||x.titulo||id)}</strong><small>${esc(x.descripcion||"Preparación del trámite.")}</small>`;
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
 $("progresoBarra").style.width=total?
  `${Math.max(0,Math.min(100,(paso-1)/total*100))}%`:"0%";

 const box=$("opciones");
 box.innerHTML="";

 (q.opciones||[]).forEach(v=>{
  const label=document.createElement("label");
  label.className="opcion";
  label.innerHTML=`<input type="radio" name="q" value="${esc(v)}"><span>${esc(v)}</span>`;
  box.appendChild(label);
 });

 $("textoEntrada").value="";
 $("textoEntrada").placeholder=q.placeholder||"Escribe, pega o agrega información aquí...";
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
  state.historial.push({
   pregunta_id:state.pregunta_id,
   pregunta:state.pregunta,
   respuesta:v
  });

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
 if(state.historial.length<=1){
  renderIdentificacion();
  mostrar("identificacion");
  return;
 }

 state.historial.pop();
 const a=state.historial[state.historial.length-1];
 if(!a)return;

 state.pregunta_id=a.pregunta_id;
 state.pregunta=a.pregunta;
 state.respuestas[a.pregunta_id]=a.respuesta||"";

 renderPregunta(a.pregunta);
 mostrar("preguntas");

 setTimeout(()=>{
  const v=a.respuesta||"";
  document.querySelectorAll("input[name='q']").forEach(x=>{
   x.checked=x.value===v;
  });
  if(!document.querySelector("input[name='q']:checked")){
   $("textoEntrada").value=v;
  }
 },30);
}

function reconocimiento(campo){
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
  const t=e.results?.[0]?.[0]?.transcript||"";
  if(campo){
   const el=$(campo);
   if(el)el.value=t;
  }else $("textoEntrada").value=t;
 };
 r.start();
}

function hablar(){reconocimiento("textoEntrada");}

function hablarPerfil(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){
  toast("Tu navegador no permite usar el micrófono.");
  return;
 }

 const r=new SR();
 r.lang="es-MX";
 r.interimResults=false;
 r.continuous=false;
 r.onstart=()=>toast("Di tus datos...");
 r.onerror=()=>toast("No se pudo usar el micrófono.");
 r.onresult=e=>{
  const t=e.results?.[0]?.[0]?.transcript||"";
  const el=$("id_nombre_completo");
  if(el){
   el.value=t;
   toast("Información recibida. Revisa y completa los demás campos.");
  }
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

async function pegarPerfil(){
 try{
  const t=await navigator.clipboard.readText();
  if(!t){
   toast("No hay texto para pegar.");
   return;
  }

  const el=$("id_nombre_completo");
  if(el)el.value=t;
  toast("Información pegada. Revísala antes de continuar.");
 }catch(e){
  toast("Pega la información directamente en los campos.");
 }
}

async function enviarPDF(inputId,mensajeId,textareaId,usar){
 const input=$(inputId);
 if(!input?.files?.length){
  toast("Selecciona un PDF.");
  return;
 }

 const file=input.files[0];

 if(file.type!=="application/pdf"&&!file.name.toLowerCase().endsWith(".pdf")){
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
  $(mensajeId).textContent="Leyendo PDF...";
  const r=await fetch("/api/documento",{method:"POST",body:fd});
  const d=await r.json().catch(()=>({}));

  if(!r.ok)throw Error(d.detail||"No se pudo leer el PDF.");

  state.pdfTexto=d.texto||"";

  if(!state.pdfTexto){
   $(mensajeId).textContent="No se encontró texto extraíble. Puedes copiar la información manualmente.";
   toast("El PDF no contiene texto extraíble.");
   return;
  }

  if(textareaId){
   $(textareaId).value=state.pdfTexto;
   $(textareaId).classList.remove("oculto");
  }

  $(mensajeId).textContent="PDF leído. Revisa la información encontrada.";

  if(usar){
   $(usar).classList.remove("oculto");
   $(usar).dataset.texto=state.pdfTexto;
  }

  toast("PDF leído correctamente.");
 }catch(e){
  $(mensajeId).textContent="";
  toast(e.message);
 }
}

async function leerPDFPrincipal(){
 await enviarPDF("archivoPdf","pdfMensaje","pdfTexto","usarPdf");
}

function usarPDFPrincipal(){
 if(!state.pdfTexto){
  toast("Primero selecciona y lee un PDF.");
  return;
 }

 state.perfil._texto_pdf=state.pdfTexto;

 mostrar("identificacion");
 renderIdentificacion();

 const campo=$("id_nombre_completo");
 if(campo)campo.value=state.pdfTexto;

 toast("Información del PDF cargada. Revisa y completa tus datos.");
}

async function leerPDFPregunta(){
 await enviarPDF("pdfPregunta","pdfPreguntaMensaje","textoEntrada",null);
 if(state.pdfTexto){
  $("textoEntrada").value=state.pdfTexto;
  $("pdfPreguntaMensaje").textContent="PDF leído. Revisa el texto antes de continuar.";
 }
}

function renderLista(v){
 if(!Array.isArray(v)||!v.length)return "<p class='muted'>No hay información registrada.</p>";

 return `<ul class="lista-simple">${
  v.map(x=>{
   const t=typeof x==="string"?x:(x?.texto||x?.nombre||x?.descripcion||"");
   return t?`<li>${esc(t)}</li>`:"";
  }).join("")
 }</ul>`;
}

function renderDatos(v){
 if(!Array.isArray(v)||!v.length)return "<p class='muted'>No hay datos registrados.</p>";

 return `<ul class="lista-simple">${
  v.map(x=>{
   const t=typeof x==="string"?x:(x?.texto||x?.nombre||"");
   return `<li>${esc(t)}</li>`;
  }).join("")
 }</ul>`;
}

function renderResultado(r){
 state.resultado=r||{};

 $("nombreResultado").textContent=r.nombre_tramite||"Tu trámite";

 const estado=r.estado||"REVISIÓN";
 $("estadoResultado").textContent=estado;

 let mensaje="Revisa cuidadosamente toda la información.";

 if(estado==="INCOMPLETO")
  mensaje="Todavía hay información que debes completar.";

 if(estado==="REVISAR DATOS")
  mensaje="Hay datos que no coinciden o necesitan corrección.";

 if(estado==="PREPARADO PARA REVISIÓN")
  mensaje="La preparación está lista. Revisa todo antes de guardar tu Hoja de Ruta.";

 $("mensajeResultado").textContent=mensaje;

 $("resultadoDatos").innerHTML=
  `<h3>TUS DATOS</h3>${renderDatos(r.datos)}`;

 $("resultadoNecesitas").innerHTML=
  `<h3>REQUISITOS</h3>${renderLista(r.requisitos||r.originales)}`;

 const falt=r.faltantes||[];

 $("resultadoFaltantes").innerHTML=
  `<h3>${falt.length?"LO QUE TE FALTA":"LO QUE ESTÁ COMPLETO"}</h3>`+
  (falt.length?
   renderLista(falt):
   "<p>No se detectan pendientes en la información proporcionada.</p>");

 const confirmar=r.confirmar||r.revision||r.acciones||[];

 $("resultadoAcciones").innerHTML=
  `<h3>REVISA Y CONFIRMA</h3>${renderLista(confirmar)}`;

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

  if(!r.ok){
   const d=await r.json().catch(()=>({}));
   throw Error(d.detail||"No se pudo preparar la Hoja de Ruta.");
  }

  const blob=await r.blob();

  if(state.pdfUrl)URL.revokeObjectURL(state.pdfUrl);

  state.pdfUrl=URL.createObjectURL(blob);

  $("pdfFrame").src=state.pdfUrl;
  $("visorPdf").classList.add("active");
 }catch(e){
  toast(e.message);
 }
}

function cerrarPreview(){
 $("visorPdf").classList.remove("active");

 if($("pdfFrame"))$("pdfFrame").src="";

 if(state.pdfUrl){
  URL.revokeObjectURL(state.pdfUrl);
  state.pdfUrl="";
 }
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

  if(!r.ok){
   const d=await r.json().catch(()=>({}));
   throw Error(d.detail||"No se pudo generar el PDF.");
  }

  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");

  a.href=url;
  a.download="Hoja_de_Ruta_EDITABLE.pdf";
  a.style.display="none";

  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(()=>URL.revokeObjectURL(url),3000);
  toast("PDF guardado.");
 }catch(e){
  toast(e.message);
 }
}

async function guardarDesdePdf(){
 await descargarPDF();
}

function aceptarLegal(){
 const b=$("comenzar");
 if(b)b.disabled=!$("aceptarLegal")?.checked;
}

function nuevoTramite(){
 cerrarPreview();

 state.caso="";
 state.servicio="";
 state.pregunta_id="";
 state.pregunta=null;
 state.respuestas={};
 state.resultado=null;
 state.historial=[];
 state.pdfTexto="";

 mostrar("tramites");
}

function salir(){
 cerrarPreview();

 state.caso="";
 state.servicio="";
 state.pregunta_id="";
 state.pregunta=null;
 state.respuestas={};
 state.resultado=null;
 state.historial=[];
 state.pdfTexto="";

 mostrar("inicio");
}

function volverResultado(){
 if(state.pregunta)mostrar("preguntas");
 else mostrar("tramites");
}

function init(){
 cargarLocal();
 cargarCatalogo();

 $("aceptarLegal")?.addEventListener("change",aceptarLegal);

 $("comenzar")?.addEventListener("click",()=>{
  if(!$("aceptarLegal")?.checked){
   toast("Primero debes aceptar la información.");
   return;
  }
  mostrar("tramites");
 });

 $("guardarPerfil")?.addEventListener("click",guardarPerfil);
 $("continuar")?.addEventListener("click",continuar);

 $("voz")?.addEventListener("click",hablar);
 $("vozPerfil")?.addEventListener("click",hablarPerfil);

 $("pegar")?.addEventListener("click",pegar);
 $("pegarPerfil")?.addEventListener("click",pegarPerfil);

 $("leerPdf")?.addEventListener("click",leerPDFPrincipal);
 $("usarPdf")?.addEventListener("click",usarPDFPrincipal);

 $("subirPdfPregunta")?.addEventListener("click",()=>$("pdfPregunta")?.click());
 $("pdfPregunta")?.addEventListener("change",leerPDFPregunta);

 $("pdfPreview")?.addEventListener("click",abrirPreview);
 $("pdf")?.addEventListener("click",descargarPDF);
 $("guardarDesdePdf")?.addEventListener("click",guardarDesdePdf);

 $("cerrarPdf")?.addEventListener("click",cerrarPreview);
 $("cerrarPdf2")?.addEventListener("click",cerrarPreview);

 $("nuevo")?.addEventListener("click",nuevoTramite);
 $("salir")?.addEventListener("click",salir);

 $("volverInicio")?.addEventListener("click",()=>mostrar("inicio"));
 $("volverTramites")?.addEventListener("click",()=>mostrar("tramites"));
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
