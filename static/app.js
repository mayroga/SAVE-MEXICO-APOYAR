const $=id=>document.getElementById(id);
let state={servicio:"",caso:"",pregunta_id:"",respuestas:{},perfil:{},resultado:null};

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
 x.textContent=t||"";
 x.classList.add("show");
 clearTimeout(window.__toast);
 window.__toast=setTimeout(()=>x.classList.remove("show"),2600);
}
async function api(url,data={},method="POST"){
 try{
  const o={method,headers:{"Content-Type":"application/json"}};
  if(method!=="GET")o.body=JSON.stringify(data);
  const r=await fetch(url,o);
  let j={};
  try{j=await r.json()}catch(_){}
  if(!r.ok)throw new Error(j.error||"No se pudo completar la operación.");
  return j;
 }catch(e){
  toast(e.message||"Error de conexión.");
  throw e;
 }
}
function guardar(j){
 if(!j||typeof j!=="object")return;
 if(j.servicio)state.servicio=j.servicio;
 if(j.caso)state.caso=j.caso;
 if(j.pregunta_id!==undefined)state.pregunta_id=j.pregunta_id||"";
 if(j.respuestas)state.respuestas={...state.respuestas,...j.respuestas};
 if(j.perfil)state.perfil={...state.perfil,...j.perfil};
 if(j.resultado)state.resultado=j.resultado;
}
function esc(v){
 return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
}
function rich(v){
 let s=esc(v);
 s=s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
  '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
 const parts=s.split(/(<a\b[^>]*>.*?<\/a>)/gi);
 for(let i=0;i<parts.length;i++){
  if(/^<a\b/i.test(parts[i]))continue;
  parts[i]=parts[i].replace(/(https?:\/\/[^\s<]+)/g,
   '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
 }
 return parts.join("");
}
function lista(a){
 return Array.isArray(a)?a.filter(x=>String(x??"").trim()):[];
}
function renderLista(a,vacio="No hay información pendiente."){
 a=lista(a);
 if(!a.length)return `<p class="vacio">${rich(vacio)}</p>`;
 return `<ul>${a.map(x=>`<li>${rich(x)}</li>`).join("")}</ul>`;
}
function renderDatos(p){
 p=p||{};
 const filas=[
  ["Nombre",p.nombre],
  ["Nacionalidad",p.nacionalidad],
  ["Teléfono",p.telefono],
  ["Dirección",p.direccion],
  ["Estado",p.estado],
  ["ZIP",p.zip],
  ["Correo",p.email]
 ];
 const usadas=filas.filter(x=>x[1]);
 if(!usadas.length)return `<p class="vacio">No proporcionaste todavía datos personales para personalizar la hoja de ruta.</p>`;
 return `<div class="datos">${usadas.map(x=>`<div><strong>${esc(x[0])}</strong><span>${rich(x[1])}</span></div>`).join("")}</div>`;
}
function bloque(t,contenido){
 return `<div class="bloque"><h3>${esc(t)}</h3>${contenido}</div>`;
}
function renderPregunta(j){
 guardar(j);
 mostrar(pregunta);
 const q=j.pregunta||j.question||{};
 const total=j.total||j.preguntas_total||"";
 const actual=j.numero||j.paso||j.indice;
 paso.textContent=actual&&total?`PASO ${actual} DE ${total}`:"PREPARANDO TU CASO";
 preguntaTexto.textContent=q.texto||q.pregunta||j.texto||"¿Qué necesitas?";
 opciones.innerHTML="";
 textoEntrada.style.display="none";
 textoUsuario.value="";
 const ops=lista(q.opciones||j.opciones);
 if(ops.length){
  ops.forEach(o=>{
   const b=document.createElement("button");
   b.type="button";
   b.className="opcion";
   b.textContent=o.label||o.texto||o.valor||o;
   b.onclick=()=>responder(o.valor??o.value??o.label??o.texto??o);
   opciones.appendChild(b);
  });
 }else{
  textoEntrada.style.display="block";
  setTimeout(()=>textoUsuario.focus(),80);
 }
}
async function responder(valor){
 if(state.pregunta_id===undefined)return;
 const pid=state.pregunta_id;
 state.respuestas[pid]=valor;
 try{
  const j=await api("/api/responder",{
   servicio:state.servicio,
   caso:state.caso,
   pregunta_id:pid,
   valor,
   respuestas:state.respuestas,
   perfil:state.perfil
  });
  guardar(j);
  procesar(j);
 }catch(_){}
}
async function iniciarServicio(servicio){
 state={servicio,caso:"",pregunta_id:"",respuestas:{},perfil:{},resultado:null};
 try{
  const j=await api(`/api/inicio/${encodeURIComponent(servicio)}`,{
   respuestas:{},
   texto:""
  });
  guardar(j);
  if(j.seleccionar||j.casos||j.opciones_caso)renderSeleccion(j);
  else procesar(j);
 }catch(_){}
}
function renderSeleccion(j){
 guardar(j);
 mostrar(servicios);
 let box=$("seleccionDinamica");
 if(!box){
  box=document.createElement("div");
  box.id="seleccionDinamica";
  servicios.appendChild(box);
 }
 box.innerHTML="";
 const titulo=j.titulo||j.texto||"ELIGE EL TRÁMITE QUE MÁS SE PARECE A TU CASO";
 box.innerHTML=`<div class="tituloCaso">${rich(titulo)}</div>`;
 const arr=j.casos||j.opciones_caso||j.opciones||[];
 lista(arr).forEach(o=>{
  const b=document.createElement("button");
  b.type="button";
  b.className="opcion";
  b.textContent=o.nombre||o.label||o.texto||o;
  b.onclick=()=>seleccionar(o.id||o.valor||o.value||o);
  box.appendChild(b);
 });
}
async function seleccionar(caso){
 try{
  const j=await api("/api/seleccionar",{
   servicio:state.servicio,
   caso,
   respuestas:state.respuestas,
   perfil:state.perfil
  });
  guardar(j);
  procesar(j);
 }catch(_){}
}
function procesar(j){
 if(!j)return;
 guardar(j);
 if(j.resultado||j.final||j.terminado||j.completo){
  state.resultado=j.resultado||j;
  renderResultado(state.resultado);
  return;
 }
 if(j.seleccionar||j.casos||j.opciones_caso){
  renderSeleccion(j);
  return;
 }
 if(j.pregunta||j.question||j.pregunta_id!==undefined){
  renderPregunta(j);
  return;
 }
 if(j.mensaje)toast(j.mensaje);
}
function seccionResultado(t,contenido){
 return bloque(t,contenido);
}
function renderResultado(r){
 r=r||state.resultado||{};
 guardar(r);
 mostrar(resultado);

 const estado=r.estado||r.nivel||"";
 let clase="estado-amarillo";
 if(/verde|listo/i.test(estado))clase="estado-verde";
 if(/rojo|atención|atencion|no vayas/i.test(estado))clase="estado-rojo";

 let html="";
 if(estado){
  html+=`<div class="resultadoCabecera ${clase}">${rich(estado)}</div>`;
 }

 html+=seccionResultado("DATOS PERSONALES",renderDatos(r.perfil||state.perfil));

 const tramite=r.tramite||r.nombre_tramite||r.caso_nombre||r.titulo||"";
 html+=seccionResultado("TU TRÁMITE",
  tramite?`<p>${rich(tramite)}</p>`:`<p class="vacio">No identificado.</p>`);

 const personas=r.personas||[];
 html+=seccionResultado("PERSONAS QUE DEBEN PRESENTARSE",
  renderLista(personas,"Consulta la información oficial para confirmar quién debe presentarse."));

 const req=r.requisitos_obligatorios||r.requisitos||[];
 html+=seccionResultado("REQUISITOS OBLIGATORIOS",
  renderLista(req,"No se identificaron requisitos en el caso seleccionado."));

 if(r.menor||r.informacion_menor){
  html+=seccionResultado("INFORMACIÓN DEL MENOR",
   renderLista(r.menor||r.informacion_menor,"No aplica o no fue proporcionada."));
 }

 if(r.padre_tutor||r.padre_madre_tutor){
  html+=seccionResultado("PADRE, MADRE O TUTOR",
   renderLista(r.padre_tutor||r.padre_madre_tutor,"No aplica o no fue proporcionada."));
 }

 const otros=r.otros||r.requisitos_adicionales||[];
 if(lista(otros).length)
  html+=seccionResultado("OTROS",renderLista(otros));

 const tiene=r.tiene||r.lo_que_ya_tienes||r.confirmados||[];
 html+=seccionResultado("LO QUE YA TIENES",
  renderLista(tiene,"Todavía no has confirmado documentos o información."));

 const falta=r.falta||r.lo_que_te_falta||r.faltantes||[];
 html+=seccionResultado("LO QUE TE FALTA",
  renderLista(falta,"No se identificaron requisitos pendientes con la información proporcionada."));

 const confirmar=r.confirmar||r.revisar||r.lo_que_debes_confirmar||[];
 html+=seccionResultado("LO QUE DEBES CONFIRMAR",
  renderLista(confirmar,"No hay puntos adicionales pendientes de confirmación."));

 const acciones=r.acciones||r.que_debes_hacer||r.pasos||[];
 html+=seccionResultado("¿QUÉ DEBES HACER?",
  renderLista(acciones,"Sigue los requisitos oficiales y confirma cualquier punto que la autoridad pueda revisar según tu caso."));

 const cita=r.cita||r.citas||[];
 html+=seccionResultado("CITA",
  renderLista(cita,"Confirma si tu trámite requiere cita y utiliza únicamente el sistema oficial indicado."));

 const originales=r.documentos_originales||r.originales||[];
 html+=seccionResultado("DOCUMENTOS ORIGINALES",
  renderLista(originales,"No se identificaron instrucciones adicionales sobre originales."));

 const copias=r.copias||r.documentos_copias||[];
 html+=seccionResultado("COPIAS",
  renderLista(copias,"No se identificaron copias obligatorias con la información disponible."));

 const pago=r.pago||r.pagos||[];
 html+=seccionResultado("PAGO",
  renderLista(pago,"Confirma la tarifa vigente y la forma de pago oficial para tu trámite."));

 const antes=r.antes_de_firmar||r.antes||[];
 html+=seccionResultado("ANTES DE FIRMAR O IMPRIMIR",
  renderLista(antes,"Revisa cuidadosamente tus datos antes de firmar o imprimir."));

 const vig=r.vigencia||[];
 if(lista(vig).length)
  html+=seccionResultado("VIGENCIA",renderLista(vig));

 const entrega=r.entrega||[];
 if(lista(entrega).length)
  html+=seccionResultado("ENTREGA",renderLista(entrega));

 const imp=r.importante||r.informacion_importante||[];
 html+=seccionResultado("INFORMACIÓN IMPORTANTE",
  renderLista(imp,"Consulta la fuente oficial antes de acudir."));

 const fuente=r.fuente||r.url_oficial||r.enlace_oficial||"";
 if(fuente){
  html+=seccionResultado("INFORMACIÓN OFICIAL",
   `<p><a href="${esc(fuente)}" target="_blank" rel="noopener noreferrer">${rich(fuente)}</a></p>`);
 }
 respuesta.innerHTML=html;
 window.scrollTo({top:0,behavior:"smooth"});
}
async function enviarTexto(){
 const texto=textoUsuario.value.trim();
 if(!texto){
  toast("Escribe o dicta tu respuesta.");
  textoUsuario.focus();
  return;
 }
 if(!state.pregunta_id){
  await entenderTextoInicial(texto);
  return;
 }
 await responder(texto);
}
async function entenderTextoInicial(texto){
 try{
  const j=await api("/api/entender",{
   servicio:state.servicio||"",
   texto,
   respuestas:state.respuestas,
   perfil:state.perfil
  });
  guardar(j);
  if(j.pregunta||j.pregunta_id!==undefined||j.resultado||j.seleccionar||j.casos){
   procesar(j);
  }else if(j.mensaje){
   toast(j.mensaje);
  }
 }catch(_){}
}
async function descargarPDF(){
 const r=state.resultado||{};
 try{
  const data={
   ...r,
   servicio:state.servicio,
   caso:state.caso,
   respuestas:state.respuestas,
   perfil:r.perfil||state.perfil
  };
  const res=await fetch("/api/pdf",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify(data)
  });
  if(!res.ok){
   let e={};
   try{e=await res.json()}catch(_){}
   throw new Error(e.error||"No se pudo generar el PDF.");
  }
  const blob=await res.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download="Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){toast(e.message||"No se pudo generar el PDF.");}
}
function hablar(){
 if(!("webkitSpeechRecognition"in window||"SpeechRecognition"in window)){
  toast("Tu navegador no permite reconocimiento de voz.");
  return;
 }
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 const r=new SR();
 r.lang="es-MX";
 r.interimResults=false;
 r.maxAlternatives=1;
 const b=$("voz");
 if(b)b.disabled=true;
 r.onresult=e=>{
  const t=e.results?.[0]?.[0]?.transcript||"";
  textoUsuario.value=(textoUsuario.value+" "+t).trim();
 };
 r.onerror=()=>toast("No se pudo reconocer la voz.");
 r.onend=()=>{if(b)b.disabled=false;};
 r.start();
}
function cerrarModal(x){
 x?.classList.add("oculto");
}
function reiniciar(){
 state={servicio:"",caso:"",pregunta_id:"",respuestas:{},perfil:{},resultado:null};
 if(textoUsuario)textoUsuario.value="";
 if(respuesta)respuesta.innerHTML="";
 if($("seleccionDinamica"))$("seleccionDinamica").remove();
 mostrar(inicio);
}
function salir(){
 salida?.classList.remove("oculto");
}
function confirmarSalida(){
 cerrarModal(salida);
 reiniciar();
}
function cancelarSalida(){
 cerrarModal(salida);
}
async function despertar(){
 try{await fetch("/api/estado",{cache:"no-store"})}catch(_){}
}

document.addEventListener("DOMContentLoaded",async()=>{
 despertar();

 $("entrar")?.addEventListener("click",()=>mostrar(servicios));

 $("servicioCita")?.addEventListener("click",()=>iniciarServicio("cita"));
 $("servicioDocumento")?.addEventListener("click",()=>iniciarServicio("documento"));

 $("continuar")?.addEventListener("click",enviarTexto);
 $("voz")?.addEventListener("click",hablar);

 textoUsuario?.addEventListener("keydown",e=>{
  if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){
   e.preventDefault();
   enviarTexto();
  }
 });

 $("pdf")?.addEventListener("click",descargarPDF);
 $("nuevo")?.addEventListener("click",reiniciar);
 $("salir")?.addEventListener("click",salir);

 $("confirmarSalida")?.addEventListener("click",confirmarSalida);
 $("cancelarSalida")?.addEventListener("click",cancelarSalida);

 $("oficial")?.addEventListener("click",()=>{
  const r=state.resultado||{};
  const u=r.fuente||r.url_oficial||r.enlace_oficial||"";
  if(!u){
   toast("No hay una fuente oficial disponible para este caso.");
   return;
  }
  $("fuenteOficial").href=u;
  $("fuenteOficial").textContent=u;
  infoOficial?.classList.remove("oculto");
 });

 $("cerrarOficial")?.addEventListener("click",()=>cerrarModal(infoOficial));

 infoOficial?.addEventListener("click",e=>{
  if(e.target===infoOficial)cerrarModal(infoOficial);
 });
 salida?.addEventListener("click",e=>{
  if(e.target===salida)cerrarModal(salida);
 });
});
