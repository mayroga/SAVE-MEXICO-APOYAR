const $=id=>document.getElementById(id);
const inicio=$("inicio"),servicios=$("servicios"),pregunta=$("pregunta"),resultado=$("resultado");
const preguntaTexto=$("preguntaTexto"),opciones=$("opciones"),textoEntrada=$("textoEntrada"),textoUsuario=$("textoUsuario"),paso=$("paso");
const respuesta=$("respuesta"),toastBox=$("toast"),infoOficial=$("infoOficial"),salida=$("salida");
let state={servicio:"",caso:"",pregunta_id:"",pregunta:null,respuestas:{},perfil:{},resultado:null};

const t=(x)=>String(x??"").trim();
const esc=x=>t(x).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const arr=x=>Array.isArray(x)?x.filter(v=>t(v)):t(x)?[t(x)]:[];
const mostrar=e=>e?.classList.remove("oculto");
const ocultar=e=>e?.classList.add("oculto");

function toast(m){
 if(!toastBox)return;
 toastBox.textContent=m;
 toastBox.classList.add("show");
 clearTimeout(window.__toast);
 window.__toast=setTimeout(()=>toastBox.classList.remove("show"),2800);
}
async function api(url,data){
 const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data||{})});
 let j={};
 try{j=await r.json()}catch{}
 if(!r.ok)throw new Error(j.detail||"No se pudo completar la operación.");
 return j;
}
function limpiar(){
 state={servicio:"",caso:"",pregunta_id:"",pregunta:null,respuestas:{},perfil:{},resultado:null};
 textoUsuario.value="";
 opciones.innerHTML="";
 respuesta.innerHTML="";
 ocultar(servicios);ocultar(pregunta);ocultar(resultado);ocultar(infoOficial);ocultar(salida);
 mostrar(inicio);
 window.scrollTo({top:0,behavior:"smooth"});
}
function comenzar(){
 ocultar(inicio);mostrar(servicios);
 window.scrollTo({top:0,behavior:"smooth"});
}
function servicio(s){
 state.servicio=s;
 ocultar(servicios);mostrar(pregunta);
 pedirInicio();
}
async function pedirInicio(){
 try{
  const j=await api("/api/iniciar",{servicio:state.servicio,respuestas:state.respuestas,texto:""});
  procesar(j);
 }catch(e){toast(e.message)}
}
function procesar(j){
 if(!j)return;
 if(j.error){toast(j.error);return}
 if(j.tipo==="resultado"||j.estado||j.tiene||j.falta||j.confirmar){
  mostrarResultado(j);return;
 }
 if(j.perfil)state.perfil=j.perfil;
 if(j.caso)state.caso=j.caso;
 if(j.pregunta_id)state.pregunta_id=j.pregunta_id;
 if(j.pregunta)state.pregunta=j.pregunta;
 else state.pregunta=j;
 mostrarPregunta(j);
}
function mostrarPregunta(j){
 ocultar(resultado);mostrar(pregunta);
 opciones.innerHTML="";
 textoEntrada.style.display="none";
 const q=j.pregunta||j;
 state.pregunta=q;
 state.pregunta_id=q.id||j.pregunta_id||"";
 state.caso=j.caso||state.caso;
 preguntaTexto.textContent=q.texto||q.pregunta||"¿Qué necesitas?";
 paso.textContent=q.paso?`PASO ${q.paso}`:"";
 const ops=q.opciones||j.opciones||[];
 if(ops.length){
  opciones.innerHTML=ops.map((o,i)=>{
   const val=typeof o==="string"?o:(o.value??o.id??o.texto??o.label??"");
   const lab=typeof o==="string"?o:(o.label??o.texto??o.nombre??val);
   return `<button class="opcion" type="button" data-value="${esc(val)}">${esc(lab)}</button>`;
  }).join("");
  opciones.querySelectorAll("button").forEach(b=>b.onclick=()=>responder(b.dataset.value));
 }else{
  textoEntrada.style.display="block";
  textoUsuario.focus();
 }
 window.scrollTo({top:pregunta.offsetTop-10,behavior:"smooth"});
}
async function responder(valor){
 valor=t(valor);
 if(!valor)return;
 state.respuestas[state.pregunta_id]=valor;
 try{
  const j=await api("/api/continuar",{
   servicio:state.servicio,
   caso:state.caso,
   pregunta_id:state.pregunta_id,
   texto:"",
   respuestas:state.respuestas,
   perfil:state.perfil
  });
  procesar(j);
 }catch(e){toast(e.message)}
}
async function enviarTexto(){
 const v=t(textoUsuario.value);
 if(!v){toast("Escribe o habla antes de continuar.");return}
 const id=state.pregunta_id;
 try{
  const j=await api("/api/interpretar",{
   servicio:state.servicio,
   caso:state.caso,
   pregunta_id:id,
   texto:v,
   respuestas:state.respuestas,
   perfil:state.perfil
  });
  textoUsuario.value="";
  procesar(j);
 }catch(e){toast(e.message)}
}
function mostrarResultado(j){
 state.resultado=j;
 state.caso=j.caso||state.caso;
 ocultar(inicio);ocultar(servicios);ocultar(pregunta);mostrar(resultado);
 let codigo=j.estado_codigo||(j.estado||{}).codigo||"amarillo";
 const titulo=codigo==="verde"?"PARECES LISTO":codigo==="rojo"?"ATENCIÓN: TODAVÍA NO VAYAS":"TE FALTA CONFIRMAR ALGO";
 const cls=codigo==="verde"?"estado-verde":codigo==="rojo"?"estado-rojo":"estado-amarillo";
 $("resultadoIcono").textContent=codigo==="verde"?"✓":codigo==="rojo"?"!":"?";
 let h=`<div class="resultadoCabecera ${cls}">${titulo}</div>`;
 if(j.mensaje)h+=`<p>${esc(j.mensaje)}</p>`;
 h+=bloqueDatos("DATOS PERSONALES",j.datos_personales);
 h+=bloqueLista("LO QUE YA TIENES",j.tiene,"No se registró todavía un documento como disponible.");
 h+=bloqueLista("LO QUE TE FALTA",j.falta,"No aparece un requisito faltante con las respuestas proporcionadas.");
 h+=bloqueLista("LO QUE DEBES CONFIRMAR",j.confirmar,"No aparece información pendiente de confirmación.");
 h+=bloqueLista("REQUISITOS OBLIGATORIOS",j.obligatorios);
 h+=bloqueLista("PERSONAS QUE DEBEN PRESENTARSE",j.personas);
 if(j.datos_menor?.length)h+=bloqueDatos("INFORMACIÓN DEL MENOR",j.datos_menor);
 if(j.datos_padre_madre_tutor?.length)h+=bloqueDatos("PADRE, MADRE O TUTOR",j.datos_padre_madre_tutor);
 h+=bloqueLista("DOCUMENTOS ORIGINALES",j.documentos_originales);
 if(j.copias?.length)h+=bloqueLista("COPIAS",j.copias);
 if(j.especiales?.length)h+=bloqueLista("INFORMACIÓN IMPORTANTE",j.especiales);
 if(j.instrucciones?.length)h+=bloqueLista("¿QUÉ DEBES HACER?",j.instrucciones);
 if(j.cita?.necesaria)h+=`<div class="bloque"><h3>CITA</h3><p>${esc(j.cita.mensaje||"Debes confirmar la cita.")}</p>${j.cita.telefono?`<p><strong>Teléfono:</strong> ${esc(j.cita.telefono)}</p>`:""}</div>`;
 if(j.pago?.necesario)h+=`<div class="bloque"><h3>PAGO</h3><p>${esc(j.pago.cantidad||"Confirma la tarifa vigente.")}</p><p>${esc(j.pago.mensaje||"")}</p></div>`;
 respuesta.innerHTML=h;
 const url=j.fuente_oficial||j.boton_oficial?.url||j.fuente||"";
 $("fuenteOficial").href=url||"#";
 $("oficial").disabled=!url;
 window.scrollTo({top:resultado.offsetTop-10,behavior:"smooth"});
}
function bloqueDatos(titulo,d){
 if(!Array.isArray(d)||!d.length)return"";
 return `<div class="bloque"><h3>${esc(titulo)}</h3><div class="datos">${d.map(x=>`<div><strong>${esc(x[0])}</strong><span>${esc(x[1])}</span></div>`).join("")}</div></div>`;
}
function bloqueLista(titulo,d,empty=""){
 const a=arr(d);
 if(!a.length)return empty?`<div class="bloque"><h3>${esc(titulo)}</h3><p class="vacio">${esc(empty)}</p></div>`:"";
 return `<div class="bloque"><h3>${esc(titulo)}</h3><ul>${a.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
}
async function descargarPDF(){
 if(!state.resultado||!state.caso){toast("Primero completa el trámite.");return}
 const b=$("pdf");b.disabled=true;b.textContent="PREPARANDO PDF...";
 try{
  const r=await fetch("/api/pdf",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
   servicio:state.servicio,caso:state.caso,respuestas:state.respuestas,perfil:state.perfil
  })});
  if(!r.ok){
   let x={};try{x=await r.json()}catch{}
   throw new Error(x.detail||"No se pudo generar el PDF.");
  }
  const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="hoja_de_ruta_mexicano_apoya_mexicano.pdf";
  document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
 }catch(e){toast(e.message)}
 finally{b.disabled=false;b.textContent="DESCARGAR HOJA DE RUTA PDF"}
}
function hablar(){
 if(!("webkitSpeechRecognition"in window||"SpeechRecognition"in window)){toast("Tu navegador no permite entrada por voz.");return}
 const R=window.SpeechRecognition||window.webkitSpeechRecognition,r=new R();
 r.lang="es-MX";r.continuous=false;r.interimResults=false;
 $("voz").disabled=true;$("voz").textContent="🎤 ESCUCHANDO...";
 r.onresult=e=>{textoUsuario.value=e.results[0][0].transcript;textoEntrada.style.display="block"};
 r.onerror=()=>toast("No se pudo reconocer la voz. Intenta nuevamente.");
 r.onend=()=>{$("voz").disabled=false;$("voz").textContent="🎤 HABLAR"};
 r.start();
}
function salir(){
 ocultar(infoOficial);mostrar(salida);
}
$("entrar").onclick=comenzar;
$("servicioCita").onclick=()=>servicio("tramite");
$("servicioDocumento").onclick=()=>servicio("documento");
$("continuar").onclick=enviarTexto;
$("voz").onclick=hablar;
$("pdf").onclick=descargarPDF;
$("oficial").onclick=()=>mostrar(infoOficial);
$("cerrarOficial").onclick=()=>ocultar(infoOficial);
$("nuevo").onclick=limpiar;
$("salir").onclick=salir;
$("cancelarSalida").onclick=()=>ocultar(salida);
$("confirmarSalida").onclick=limpiar;
textoUsuario.addEventListener("keydown",e=>{if(e.key==="Enter"&&e.ctrlKey)enviarTexto()});
window.addEventListener("load",async()=>{
 try{await fetch("/api/estado")}catch{}
});
