const $=id=>document.getElementById(id);
const state={servicio:"",caso:"",pregunta_id:"",respuestas:{},perfil:{},resultado:null};

async function api(url,opt={}){
 const r=await fetch(url,{headers:{"Content-Type":"application/json",...(opt.headers||{})},...opt});
 let d={};
 try{d=await r.json()}catch(e){}
 if(!r.ok)throw new Error(d.detail||d.mensaje||"No se pudo completar la operación.");
 return d;
}

function mostrar(id){
 ["inicio","servicios","pregunta","resultado"].forEach(x=>$(x)?.classList.add("oculto"));
 $(id)?.classList.remove("oculto");
 window.scrollTo({top:0,behavior:"smooth"});
}

function toast(txt){
 let x=$("toast");
 if(!x){
  x=document.createElement("div");
  x.id="toast";x.className="toast";
  document.body.appendChild(x);
 }
 x.textContent=txt;x.classList.add("show");
 clearTimeout(window.__toast);
 window.__toast=setTimeout(()=>x.classList.remove("show"),2800);
}

function guardar(d){
 if(d.respuestas)state.respuestas={...d.respuestas};
 if(d.perfil)state.perfil={...d.perfil};
 if(d.caso)state.caso=d.caso;
 if(d.pregunta_id)state.pregunta_id=d.pregunta_id;
 if(d.resultado)state.resultado=d.resultado;
}

function limpiar(){
 state.servicio="";state.caso="";state.pregunta_id="";
 state.respuestas={};state.perfil={};state.resultado=null;
 if($("textoUsuario"))$("textoUsuario").value="";
}

function textoSeguro(x){
 return String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
}

function renderOpciones(opciones=[]){
 const box=$("opciones");
 if(!box)return;
 box.innerHTML="";
 (opciones||[]).forEach(o=>{
  const id=typeof o==="string"?o:o.id;
  const texto=typeof o==="string"?o:(o.texto||o.titulo||o.nombre||o.id);
  const b=document.createElement("button");
  b.type="button";b.className="opcion";b.textContent=texto;
  b.onclick=()=>seleccionarOpcion(id,texto,o);
  box.appendChild(b);
 });
}

function renderPregunta(d){
 guardar(d);
 state.caso=d.caso||state.caso;
 state.pregunta_id=d.pregunta_id||"";
 if($("paso"))$("paso").textContent=d.titulo?`TRÁMITE: ${d.titulo}`:"";
 if($("preguntaTexto"))$("preguntaTexto").textContent=d.pregunta||"";
 if($("textoEntrada"))$("textoEntrada").style.display=(d.opciones&&d.opciones.length)?"none":"block";
 renderOpciones(d.opciones||[]);
 if($("textoUsuario")){
  $("textoUsuario").value="";
  $("textoUsuario").focus();
 }
 mostrar("pregunta");
}

function renderCatalogo(d){
 guardar(d);
 state.pregunta_id="tramite";
 if($("paso"))$("paso").textContent="ELIGE TU TRÁMITE";
 if($("preguntaTexto"))$("preguntaTexto").textContent=d.pregunta||"¿Qué trámite necesitas preparar?";
 if($("textoEntrada"))$("textoEntrada").style.display="none";
 renderOpciones(d.opciones||[]);
 mostrar("pregunta");
}

async function entrar(){
 try{
  mostrar("servicios");
 }catch(e){toast(e.message)}
}

async function iniciarServicio(servicio){
 try{
  state.servicio=servicio;state.caso="";state.respuestas={};state.perfil={};state.resultado=null;
  const d=await api(`/api/inicio/${encodeURIComponent(servicio)}`);
  if(d.tipo==="catalogo"||d.catalogo||d.estado==="seleccionar"){
   renderCatalogo(d);return;
  }
  procesar(d);
 }catch(e){toast(e.message)}
}

async function seleccionarOpcion(id,texto,obj){
 if(state.pregunta_id==="tramite"||!state.caso){
  if(!id)return;
  await iniciarCaso(id);
  return;
 }
 const valor=texto||id;
 await responder(valor);
}

async function iniciarCaso(caso){
 try{
  const d=await api("/api/iniciar",{
   method:"POST",
   body:JSON.stringify({
    servicio:state.servicio,
    caso:caso,
    respuestas:state.respuestas
   })
  });
  if(d.estado==="error"){toast(d.mensaje||"No se pudo iniciar el trámite.");return}
  state.caso=caso;
  state.pregunta_id=d.pregunta_id||"";
  guardar(d);
  procesar(d);
 }catch(e){toast(e.message)}
}

async function responder(texto){
 texto=String(texto||"").trim();
 if(!texto){
  toast("Escribe o selecciona una respuesta.");
  return;
 }
 if(!state.caso){
  toast("Primero selecciona el trámite.");
  return;
 }
 const pid=state.pregunta_id;
 if(!pid){
  toast("No hay una pregunta activa.");
  return;
 }
 try{
  const d=await api("/api/responder",{
   method:"POST",
   body:JSON.stringify({
    servicio:state.servicio,
    caso:state.caso,
    pregunta_id:pid,
    texto:texto,
    respuestas:state.respuestas
   })
  });
  procesar(d);
 }catch(e){toast(e.message)}
}

function procesar(d){
 if(!d)return;
 if(d.estado==="error"){
  toast(d.mensaje||"Ocurrió un error.");
  return;
 }
 guardar(d);

 if(d.tipo==="catalogo"||d.tipo==="seleccionar_caso"||d.catalogo){
  renderCatalogo(d);return;
 }

 if(d.tipo==="pregunta"){
  renderPregunta(d);return;
 }

 if(d.tipo==="resultado"&&d.estado==="resuelto"){
  renderResultado(d);return;
 }

 if(d.pregunta){
  renderPregunta(d);return;
 }

 toast("La aplicación no recibió una respuesta válida.");
}

function bloque(t,html){
 return `<div class="bloque"><h3>${t}</h3>${html}</div>`;
}

function lista(arr){
 if(!arr||!arr.length)return `<p class="vacio">PENDIENTE DE COMPLETAR</p>`;
 return `<ul>${arr.map(x=>`<li>${textoSeguro(x)}</li>`).join("")}</ul>`;
}

function datosPerfil(p){
 const filas=[
  ["Nombre",p.nombre],
  ["Nacionalidad",p.nacionalidad],
  ["Teléfono",p.telefono],
  ["Dirección",p.direccion],
  ["Estado",p.estado],
  ["ZIP",p.zip||p.codigo_postal],
  ["Correo",p.email||p.correo]
 ];
 return `<div class="datos">${filas.map(x=>`<div><strong>${x[0]}</strong><span>${textoSeguro(x[1]||"PENDIENTE DE COMPLETAR")}</span></div>`).join("")}</div>`;
}

function renderResultado(d){
 state.resultado=d;
 const nivel=d.nivel||"amarillo";
 const clase=nivel==="verde"?"estado-verde":nivel==="rojo"?"estado-rojo":"estado-amarillo";
 const titulo=d.estado_texto||"TE FALTA ALGO";
 const c=d.checklist||{};
 const personas=d.personas_obligatorias||[];
 const requisitos=d.requisitos_obligatorios||[];
 const originales=d.originales||[];
 const cita=d.cita||[];
 const importantes=d.importante||[];
 let html="";

 html+=`<div class="resultadoCabecera ${clase}">${textoSeguro(titulo)}</div>`;

 html+=bloque("1. DATOS PERSONALES",datosPerfil(d.perfil||{}));
 html+=bloque("2. TRÁMITE",`<p>${textoSeguro(d.tramite||d.titulo||"PENDIENTE DE COMPLETAR")}</p>`);

 if(personas.length)
  html+=bloque("3. PERSONAS QUE DEBEN PRESENTARSE",lista(personas));

 html+=bloque("4. REQUISITOS OBLIGATORIOS",lista(requisitos));
 html+=bloque("5. LO QUE YA TIENES",lista(c.tiene));
 html+=bloque("6. LO QUE TE FALTA",lista(c.falta));
 html+=bloque("7. LO QUE DEBES CONFIRMAR",lista([...(c.revisar||[]),...(d.especiales||[])]));
 html+=bloque("8. ¿QUÉ DEBES HACER?",`<p>${textoSeguro(d.prepara||"PENDIENTE DE COMPLETAR")}</p>`);
 html+=bloque("9. CITA",lista(cita.length?cita:["Confirma la necesidad de cita según tu trámite y conserva la confirmación."]));
 html+=bloque("10. DOCUMENTOS ORIGINALES",lista(originales));
 if(d.copias&&d.copias.length)html+=bloque("11. COPIAS",lista(d.copias));
 html+=bloque("12. PAGO",`<p>${textoSeguro(d.pago||"Confirma la tarifa y forma de pago vigente.")}</p>`);
 html+=bloque("13. ANTES DE FIRMAR O IMPRIMIR",`<p>${textoSeguro(d.revision||"Revisa cuidadosamente todos los datos.")}</p>`);
 if(d.vigencia)html+=bloque("14. VIGENCIA",`<p>${textoSeguro(d.vigencia)}</p>`);
 if(d.entrega)html+=bloque("15. ENTREGA",`<p>${textoSeguro(d.entrega)}</p>`);
 html+=bloque("16. INFORMACIÓN IMPORTANTE",lista(importantes.concat(d.confirma?[d.confirma]:[])));
 if(d.fuente){
  html+=`<div class="bloque"><h3>INFORMACIÓN OFICIAL</h3><a class="fuente" href="${textoSeguro(d.fuente)}" target="_blank" rel="noopener noreferrer">ABRIR INFORMACIÓN OFICIAL</a></div>`;
 }

 if($("respuesta"))$("respuesta").innerHTML=html;
 if($("fuenteOficial")){
  $("fuenteOficial").href=d.fuente||"#";
  $("fuenteOficial").style.display=d.fuente?"block":"none";
 }
 mostrar("resultado");
}

async function descargarPDF(){
 const b=$("pdf");
 if(!state.resultado){
  toast("Primero termina la consulta.");
  return;
 }
 try{
  if(b)b.disabled=true;
  const r=await fetch("/api/pdf",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    servicio:state.servicio,
    caso:state.caso,
    respuestas:state.respuestas,
    resultado:state.resultado
   })
  });
  if(!r.ok){
   let e={};
   try{e=await r.json()}catch(x){}
   throw new Error(e.detail||"No se pudo generar el PDF.");
  }
  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;
  a.download="Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){toast(e.message)}
 finally{if(b)b.disabled=false}
}

function nuevo(){
 limpiar();
 mostrar("inicio");
}

function salir(){
 $("salida")?.classList.remove("oculto");
}

function cancelarSalida(){
 $("salida")?.classList.add("oculto");
}

function confirmarSalida(){
 $("salida")?.classList.add("oculto");
 limpiar();
 mostrar("inicio");
}

function abrirOficial(){
 $("infoOficial")?.classList.remove("oculto");
}

function cerrarOficial(){
 $("infoOficial")?.classList.add("oculto");
}

function usarTexto(){
 const x=$("textoUsuario");
 if(!x)return;
 responder(x.value);
}

let reconocimiento=null;

function voz(){
 const b=$("voz"),x=$("textoUsuario");
 if(!x)return;

 if(!("webkitSpeechRecognition" in window||"SpeechRecognition" in window)){
  toast("Tu navegador no permite entrada por voz.");
  return;
 }

 const R=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(reconocimiento){
  reconocimiento.stop();
  reconocimiento=null;
  if(b)b.textContent="🎤 HABLAR";
  return;
 }

 reconocimiento=new R();
 reconocimiento.lang="es-MX";
 reconocimiento.interimResults=false;
 reconocimiento.continuous=false;

 if(b)b.textContent="🔴 ESCUCHANDO...";

 reconocimiento.onresult=e=>{
  const t=e.results?.[0]?.[0]?.transcript||"";
  x.value=t;
  responder(t);
 };

 reconocimiento.onerror=e=>{
  toast("No se pudo reconocer la voz.");
 };

 reconocimiento.onend=()=>{
  reconocimiento=null;
  if(b)b.textContent="🎤 HABLAR";
 };
 reconocimiento.start();
}

function teclado(e){
 if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){
  e.preventDefault();
  usarTexto();
 }
}

document.addEventListener("DOMContentLoaded",async()=>{
 $("entrar")?.addEventListener("click",entrar);

 $("servicioCita")?.addEventListener("click",()=>iniciarServicio("cita"));
 $("servicioDocumento")?.addEventListener("click",()=>iniciarServicio("documento"));

 $("continuar")?.addEventListener("click",usarTexto);
 $("voz")?.addEventListener("click",voz);
 $("textoUsuario")?.addEventListener("keydown",teclado);

 $("pdf")?.addEventListener("click",descargarPDF);
 $("nuevo")?.addEventListener("click",nuevo);
 $("salir")?.addEventListener("click",salir);

 $("confirmarSalida")?.addEventListener("click",confirmarSalida);
 $("cancelarSalida")?.addEventListener("click",cancelarSalida);

 $("oficial")?.addEventListener("click",abrirOficial);
 $("cerrarOficial")?.addEventListener("click",cerrarOficial);

 try{
  await api("/api/estado");
 }catch(e){
  console.warn("Servidor:",e.message);
 }
});
