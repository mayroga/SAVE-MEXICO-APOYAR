const $=id=>document.getElementById(id);
let state={
 servicio:"",
 caso:"",
 pregunta_id:"",
 respuestas:{},
 perfil:{},
 resultado:null
};

const inicio=$("inicio"),servicios=$("servicios"),pregunta=$("pregunta"),resultado=$("resultado");
const preguntaTexto=$("preguntaTexto"),opciones=$("opciones"),textoEntrada=$("textoEntrada");
const textoUsuario=$("textoUsuario"),paso=$("paso"),respuesta=$("respuesta");
const infoOficial=$("infoOficial"),salida=$("salida");

function ocultarTodo(){
 [inicio,servicios,pregunta,resultado].forEach(x=>x?.classList.add("oculto"));
}

function mostrar(x){
 ocultarTodo();
 x?.classList.remove("oculto");
 window.scrollTo({top:0,behavior:"smooth"});
}

function toast(t){
 let x=$("toast");
 if(!x){
  x=document.createElement("div");
  x.id="toast";
  x.className="toast";
  document.body.appendChild(x);
 }
 x.textContent=t;
 x.classList.add("show");
 clearTimeout(window._toast);
 window._toast=setTimeout(()=>x.classList.remove("show"),2800);
}

async function api(url,data={},method="POST"){
 const o={method,headers:{}};
 if(method!=="GET"){
  o.headers["Content-Type"]="application/json";
  o.body=JSON.stringify(data);
 }
 const res=await fetch(url,o);
 let j={};
 try{j=await res.json()}catch(e){}
 if(!res.ok)throw new Error(j.detail||j.error||`Error ${res.status}`);
 return j;
}

function guardar(j){
 if(j.respuestas)state.respuestas=j.respuestas;
 if(j.perfil)state.perfil=j.perfil;
 if(j.caso)state.caso=j.caso;
 if(j.pregunta_id)state.pregunta_id=j.pregunta_id;
 if(j.servicio)state.servicio=j.servicio;
 if(j.resultado)state.resultado=j.resultado;
}

function esc(t){
 return String(t??"")
  .replace(/&/g,"&amp;")
  .replace(/</g,"&lt;")
  .replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;")
  .replace(/'/g,"&#039;");
}

function lista(arr){
 return Array.isArray(arr)?arr.filter(Boolean):[];
}

function renderLista(arr){
 const a=lista(arr);
 if(!a.length)return `<p class="vacio">PENDIENTE DE COMPLETAR</p>`;
 return `<ul>${a.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`;
}

function renderDatos(p){
 p=p||{};
 const rows=[
  ["Nombre",p.nombre],
  ["Nacionalidad",p.nacionalidad],
  ["Teléfono",p.telefono],
  ["Dirección",p.direccion],
  ["Estado",p.estado],
  ["ZIP",p.zip],
  ["Correo",p.email]
 ];
 return `<div class="datos">${
  rows.map(x=>`<div><strong>${x[0]}</strong><span>${esc(x[1]||"PENDIENTE DE COMPLETAR")}</span></div>`).join("")
 }</div>`;
}

function renderPregunta(j){
 guardar(j);
 mostrar(pregunta);
 paso.textContent=j.paso||"SIGUIENTE PASO";
 preguntaTexto.textContent=j.pregunta||"¿Qué necesitas?";
 opciones.innerHTML="";
 textoEntrada.style.display=j.tipo==="opciones"?"none":"block";

 lista(j.opciones).forEach(v=>{
  const b=document.createElement("button");
  b.type="button";
  b.className="opcion";
  b.textContent=v;
  b.onclick=()=>responder(v);
  opciones.appendChild(b);
 });

 if(j.tipo==="texto"){
  textoUsuario.value="";
  setTimeout(()=>textoUsuario.focus(),80);
 }
}

async function responder(valor){
 try{
  const j=await api("/api/responder",{
   caso:state.caso,
   pregunta_id:state.pregunta_id,
   texto:String(valor??""),
   respuestas:state.respuestas
  });
  procesar(j);
 }catch(e){
  toast(e.message||"No se pudo procesar la respuesta.");
 }
}

async function iniciarServicio(servicio){
 state={servicio,caso:"",pregunta_id:"",respuestas:{},perfil:{},resultado:null};
 try{
  const j=await api(`/api/inicio/${encodeURIComponent(servicio)}`,{
   servicio,
   respuestas:{},
   texto:""
  });
  guardar(j);
  if(j.seleccionar)renderSeleccion(j);
  else procesar(j);
 }catch(e){
  toast(e.message||"No se pudo iniciar.");
 }
}

function renderSeleccion(j){
 mostrar(servicios);
 const old=servicios.querySelector(".seleccionDinamica");
 if(old)old.remove();

 const box=document.createElement("div");
 box.className="seleccionDinamica";
 box.innerHTML=`<div class="tituloCaso">${esc(j.pregunta||"Elige la opción que más se parece a tu situación.")}</div>`;

 lista(j.opciones).forEach(o=>{
  const b=document.createElement("button");
  b.type="button";
  b.className="opcion";
  b.textContent=o.titulo||o.nombre||o.label||"Elegir";
  b.onclick=()=>seleccionar(o.id);
  box.appendChild(b);
 });
 servicios.appendChild(box);
 window.scrollTo({top:0,behavior:"smooth"});
}

async function seleccionar(caso){
 try{
  const j=await api("/api/seleccionar",{
   caso,
   respuestas:state.respuestas,
   texto:""
  });
  procesar(j);
 }catch(e){
  toast(e.message||"No se pudo seleccionar el trámite.");
 }
}

function procesar(j){
 guardar(j);
 if(j.final&&j.resultado){
  renderResultado(j.resultado);
  return;
 }
 if(j.seleccionar){
  renderSeleccion(j);
  return;
 }
 if(j.pregunta_id){
  renderPregunta(j);
  return;
 }
 if(j.resultado){
  renderResultado(j.resultado);
  return;
 }
 toast("No se recibió una respuesta válida.");
}

function renderResultado(r){
 state.resultado=r;
 mostrar(resultado);

 const nivel=r.nivel||"amarillo";
 const estado=r.estado_texto||"TE FALTA ALGO";

 respuesta.innerHTML=`
 <div class="resultadoCabecera estado-${esc(nivel)}">${esc(estado)}</div>

 <div class="bloque">
  <h3>DATOS PERSONALES</h3>
  ${renderDatos(r.perfil)}
 </div>

 <div class="bloque">
  <h3>TU TRÁMITE</h3>
  <p><strong>${esc(r.tramite||r.titulo)}</strong></p>
 </div>

 <div class="bloque">
  <h3>PERSONAS QUE DEBEN PRESENTARSE</h3>
  ${renderLista(r.personas_obligatorias)}
 </div>

 <div class="bloque">
  <h3>REQUISITOS OBLIGATORIOS</h3>
  ${renderLista(r.requisitos_obligatorios)}
 </div>

 ${lista(r.opcionales).length?`
 <div class="bloque">
  <h3>OTROS REQUISITOS</h3>
  ${renderLista(r.opcionales)}
 </div>`:""}

 <div class="bloque">
  <h3>LO QUE YA TIENES</h3>
  ${renderLista(r.tiene)}
 </div>

 <div class="bloque">
  <h3>LO QUE TE FALTA</h3>
  ${renderLista(r.falta)}
 </div>

 <div class="bloque">
  <h3>LO QUE DEBES CONFIRMAR</h3>
  ${renderLista(r.revisar)}
 </div>

 <div class="bloque">
  <h3>¿QUÉ DEBES HACER?</h3>
  ${renderLista(r.acciones)}
 </div>

 <div class="bloque">
  <h3>CITA</h3>
  ${renderLista(r.cita,"Confirma si necesitas cita.")}
 </div>

 <div class="bloque">
  <h3>DOCUMENTOS ORIGINALES</h3>
  ${renderLista(r.originales)}
 </div>

 <div class="bloque">
  <h3>COPIAS</h3>
  ${renderLista(r.copias,"No se identificaron copias obligatorias.")}
 </div>

 <div class="bloque">
  <h3>PAGO</h3>
  <p>${esc(r.pago||"Confirma la tarifa vigente.")}</p>
 </div>

 <div class="bloque">
  <h3>ANTES DE FIRMAR O IMPRIMIR</h3>
  <p>${esc(r.revision||"Revisa cuidadosamente todos tus datos.")}</p>
 </div>

 ${r.vigencia?`
 <div class="bloque">
  <h3>VIGENCIA</h3>
  <p>${esc(r.vigencia)}</p>
 </div>`:""}

 ${r.entrega?`
 <div class="bloque">
  <h3>ENTREGA</h3>
  <p>${esc(r.entrega)}</p>
 </div>`:""}

 <div class="bloque">
  <h3>INFORMACIÓN IMPORTANTE</h3>
  ${renderLista(r.importante)}
 </div>
 `;

 const fuente=$("fuenteOficial");
 if(fuente){
  fuente.href=r.fuente||"#";
  fuente.style.display=r.fuente?"block":"none";
 }
}

async function enviarTexto(){
 const texto=textoUsuario.value.trim();
 if(!texto){
  toast("Escribe o dicta tu respuesta.");
  textoUsuario.focus();
  return;
 }

 try{
  const j=await api("/api/responder",{
   caso:state.caso,
   pregunta_id:state.pregunta_id,
   texto,
   respuestas:state.respuestas
  });
  textoUsuario.value="";
  procesar(j);
 }catch(e){
  toast(e.message||"No se pudo procesar.");
 }
}

async function entenderTextoInicial(texto){
 texto=String(texto||"").trim();
 if(!texto)return;
 try{
  const j=await api("/api/entender",{
   servicio:state.servicio||"cita",
   texto,
   respuestas:state.respuestas,
   pregunta_id:state.pregunta_id
  });
  procesar(j);
 }catch(e){
  toast(e.message||"No se pudo entender la información.");
 }
}

function descargarPDF(){
 if(!state.resultado){
  toast("Primero completa el trámite.");
  return;
 }

 fetch("/api/pdf",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify(state.resultado)
 })
 .then(async res=>{
  if(!res.ok){
   let j={};
   try{j=await res.json()}catch(e){}
   throw new Error(j.detail||j.error||"No se pudo generar el PDF.");
  }
  return res.blob();
 })
 .then(blob=>{
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download="hoja_ruta_mexicano_apoya_mexicano.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 })
 .catch(e=>toast(e.message));
}

function hablar(){
 if(!("SpeechRecognition" in window||"webkitSpeechRecognition" in window)){
  toast("Tu navegador no permite entrada por voz.");
  return;
 }

 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 const rec=new SR();
 rec.lang="es-MX";
 rec.interimResults=false;
 rec.continuous=false;

 const b=$("voz");
 if(b)b.disabled=true;

 rec.onresult=e=>{
  const texto=e.results?.[0]?.[0]?.transcript||"";
  textoUsuario.value=texto;
  textoEntrada.style.display="block";
  enviarTexto();
 };

 rec.onerror=()=>toast("No se pudo escuchar. Puedes escribir la respuesta.");
 rec.onend=()=>{if(b)b.disabled=false};

 try{rec.start()}catch(e){if(b)b.disabled=false}
}

function cerrarModal(x){
 x?.classList.add("oculto");
}

function reiniciar(){
 state={
  servicio:"",
  caso:"",
  pregunta_id:"",
  respuestas:{},
  perfil:{},
  resultado:null
 };
 textoUsuario.value="";
 respuesta.innerHTML="";
 cerrarModal(infoOficial);
 cerrarModal(salida);
 mostrar(inicio);
}

function salir(){
 salida.classList.remove("oculto");
}

function confirmarSalida(){
 reiniciar();
}

document.addEventListener("DOMContentLoaded",async()=>{
 $("entrar")?.addEventListener("click",()=>mostrar(servicios));

 $("servicioCita")?.addEventListener("click",()=>iniciarServicio("cita"));
 $("servicioDocumento")?.addEventListener("click",()=>iniciarServicio("documento"));

 $("continuar")?.addEventListener("click",enviarTexto);
 $("voz")?.addEventListener("click",hablar);

 $("pdf")?.addEventListener("click",descargarPDF);

 $("oficial")?.addEventListener("click",()=>{
  if(state.resultado?.fuente){
   $("fuenteOficial").href=state.resultado.fuente;
   infoOficial.classList.remove("oculto");
  }else toast("No hay una fuente oficial disponible.");
 });

 $("cerrarOficial")?.addEventListener("click",()=>cerrarModal(infoOficial));

 $("nuevo")?.addEventListener("click",reiniciar);
 $("salir")?.addEventListener("click",salir);
 $("confirmarSalida")?.addEventListener("click",confirmarSalida);
 $("cancelarSalida")?.addEventListener("click",()=>cerrarModal(salida));

 textoUsuario?.addEventListener("keydown",e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){
   e.preventDefault();
   enviarTexto();
  }
 });

 try{
  await api("/api/estado",{}, "GET");
 }catch(e){
  console.warn("Servidor:",e.message);
 }
});
