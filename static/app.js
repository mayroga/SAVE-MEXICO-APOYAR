const $=id=>document.getElementById(id);
const state={servicio:"",caso:"",pregunta_id:"",respuestas:{},perfil:{},resultado:null};

async function api(url,opt={}){
 const r=await fetch(url,{headers:{"Content-Type":"application/json",...(opt.headers||{})},...opt});
 let d={};try{d=await r.json()}catch(e){}
 if(!r.ok)throw Error(d.detail||d.mensaje||"No se pudo completar la operación.");
 return d;
}
function mostrar(id){
 ["inicio","servicios","pregunta","resultado"].forEach(x=>$(x)?.classList.add("oculto"));
 $(id)?.classList.remove("oculto");
 window.scrollTo({top:0,behavior:"smooth"});
}
function toast(t){
 let x=$("toast");
 if(!x){x=document.createElement("div");x.id="toast";x.className="toast";document.body.appendChild(x)}
 x.textContent=t;x.classList.add("show");
 clearTimeout(window.__toast);
 window.__toast=setTimeout(()=>x.classList.remove("show"),2800);
}
function guardar(d){
 if(d.respuestas)state.respuestas={...d.respuestas};
 if(d.perfil)state.perfil={...d.perfil};
 if(d.respuestas?._perfil)state.perfil={...state.perfil,...d.respuestas._perfil};
 if(d.caso)state.caso=d.caso;
 if(d.pregunta_id!==undefined)state.pregunta_id=d.pregunta_id||"";
 if(d.resultado)state.resultado=d.resultado;
}
function limpiar(){
 state.servicio="";state.caso="";state.pregunta_id="";
 state.respuestas={};state.perfil={};state.resultado=null;
 if($("textoUsuario"))$("textoUsuario").value="";
}
function safe(x){
 return String(x??"").replace(/[&<>"']/g,m=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
 }[m]));
}
function lista(a,pendiente=true){
 a=Array.isArray(a)?a:[];
 if(!a.length)return pendiente?'<p class="vacio">PENDIENTE DE COMPLETAR</p>':"";
 return `<ul>${a.map(x=>`<li>${safe(x)}</li>`).join("")}</ul>`;
}
function bloque(t,h){
 return `<div class="bloque"><h3>${safe(t)}</h3>${h}</div>`;
}
function tabla(a){
 return `<div class="datos">${(a||[]).map(x=>`
 <div><strong>${safe(x[0])}</strong><span>${safe(x[1]||"PENDIENTE DE COMPLETAR")}</span></div>
 `).join("")}</div>`;
}
function datosPersonales(p){
 p=p||{};
 return tabla([
  ["Nombre",p.nombre],
  ["Nacionalidad",p.nacionalidad],
  ["Teléfono",p.telefono],
  ["Dirección",p.direccion],
  ["Estado",p.estado],
  ["ZIP",p.zip||p.codigo_postal],
  ["Correo",p.email||p.correo]
 ]);
}
function renderOpciones(a){
 const box=$("opciones");
 if(!box)return;
 box.innerHTML="";
 (a||[]).forEach(o=>{
  const id=typeof o==="string"?o:o.id;
  const text=typeof o==="string"?o:(o.nombre||o.titulo||o.texto||o.id);
  const b=document.createElement("button");
  b.type="button";b.className="opcion";b.textContent=text;
  b.onclick=()=>seleccionarOpcion(id,text);
  box.appendChild(b);
 });
}
function renderCatalogo(d){
 guardar(d);state.pregunta_id="tramite";
 if($("paso"))$("paso").textContent="ELIGE TU TRÁMITE";
 if($("preguntaTexto"))$("preguntaTexto").textContent=d.pregunta||"¿Qué trámite necesitas preparar?";
 renderOpciones(d.opciones||[]);
 if($("textoEntrada")){
  $("textoEntrada").style.display="block";
  $("textoUsuario").value="";
  $("textoUsuario").placeholder="Si no ves tu caso, explica aquí qué necesitas...";
 }
 mostrar("pregunta");
}
function renderPregunta(d){
 guardar(d);
 state.caso=d.caso||state.caso;
 state.pregunta_id=d.pregunta_id||"";
 if($("paso"))$("paso").textContent=d.titulo?"TRÁMITE: "+d.titulo:"";
 if($("preguntaTexto"))$("preguntaTexto").textContent=d.pregunta||"";
 renderOpciones(d.opciones||[]);
 if($("textoEntrada")){
  $("textoEntrada").style.display="block";
  $("textoUsuario").value="";
  $("textoUsuario").placeholder=d.opciones?.length?
   "También puedes escribir o hablar tu respuesta...":
   "Escribe aquí con tus propias palabras...";
 }
 mostrar("pregunta");
 setTimeout(()=>$("textoUsuario")?.focus(),100);
}
function renderResultado(d){
 guardar(d);state.resultado=d;
 const nivel=d.nivel||"amarillo";
 const clase=nivel==="verde"?"estado-verde":nivel==="rojo"?"estado-rojo":"estado-amarillo";
 const r=d.respuestas||state.respuestas||{};
 const k=d.checklist||{};
 const importantes=[...(d.importante||[]),...(d.especiales||[])];
 let h=`<div class="resultadoCabecera ${clase}">${safe(d.estado_texto||"TE FALTA ALGO")}</div>`;

 h+=bloque("1. DATOS PERSONALES",datosPersonales(d.perfil||state.perfil));
 h+=bloque("2. TRÁMITE",`<p>${safe(d.tramite||d.titulo||"PENDIENTE DE COMPLETAR")}</p>`);
 h+=bloque("3. PERSONAS QUE DEBEN PRESENTARSE",
  lista(d.personas_obligatorias||["PENDIENTE DE COMPLETAR"]));
 h+=bloque("4. REQUISITOS OBLIGATORIOS",
  lista(d.requisitos_obligatorios));

 if(d.caso==="pasaporte_menor"||d.caso==="matricula_menor"){
  h+=bloque("5. INFORMACIÓN DEL MENOR",tabla([
   ["Nombre del menor",r.menor_nombre||d.perfil?.nombre],
   ["Nacionalidad / documento",r.menor_nacionalidad],
   ["Identificación",r.menor_identidad]
  ]));
  h+=bloque("6. PADRE, MADRE O TUTOR",tabla([
   ["Nombre",r.padre1],
   ["Identificación",r.padre1_id],
   ["Otro padre/madre/tutor",r.padre2],
   ["Autorización",r.autorizacion||r.op7]
  ]));
  h+=bloque("7. LO QUE YA TIENES",lista(k.tiene));
  h+=bloque("8. LO QUE TE FALTA",lista(k.falta));
  h+=bloque("9. LO QUE DEBES CONFIRMAR",lista(k.revisar));
  h+=bloque("10. ¿QUÉ DEBES HACER?",`<p>${safe(d.prepara||"PENDIENTE DE COMPLETAR")}</p>`);
  h+=bloque("11. CITA",lista(d.cita));
  h+=bloque("12. DOCUMENTOS ORIGINALES",lista(d.originales));
  h+=bloque("13. COPIAS",lista(d.copias,false)||'<p class="vacio">No se identificaron copias obligatorias.</p>');
  h+=bloque("14. PAGO",`<p>${safe(d.pago||"Confirma la tarifa y forma de pago vigente.")}</p>`);
  h+=bloque("15. ANTES DE FIRMAR O IMPRIMIR",`<p>${safe(d.revision||"Revisa cuidadosamente todos los datos.")}</p>`);
  if(d.vigencia)h+=bloque("16. VIGENCIA",`<p>${safe(d.vigencia)}</p>`);
  if(d.entrega)h+=bloque("17. ENTREGA",`<p>${safe(d.entrega)}</p>`);
  h+=bloque("18. INFORMACIÓN IMPORTANTE",lista(importantes));
 }else{
  h+=bloque("5. LO QUE YA TIENES",lista(k.tiene));
  h+=bloque("6. LO QUE TE FALTA",lista(k.falta));
  h+=bloque("7. LO QUE DEBES CONFIRMAR",lista(k.revisar));
  h+=bloque("8. ¿QUÉ DEBES HACER?",`<p>${safe(d.prepara||"PENDIENTE DE COMPLETAR")}</p>`);
  h+=bloque("9. CITA",lista(d.cita));
  h+=bloque("10. DOCUMENTOS ORIGINALES",lista(d.originales));
  h+=bloque("11. COPIAS",lista(d.copias,false)||'<p class="vacio">No se identificaron copias obligatorias.</p>');
  h+=bloque("12. PAGO",`<p>${safe(d.pago||"Confirma la tarifa y forma de pago vigente.")}</p>`);
  h+=bloque("13. ANTES DE FIRMAR O IMPRIMIR",`<p>${safe(d.revision||"Revisa cuidadosamente todos los datos.")}</p>`);
  if(d.vigencia)h+=bloque("14. VIGENCIA",`<p>${safe(d.vigencia)}</p>`);
  if(d.entrega)h+=bloque("15. ENTREGA",`<p>${safe(d.entrega)}</p>`);
  h+=bloque("16. INFORMACIÓN IMPORTANTE",lista(importantes));
 }

 if(d.confirma)h+=bloque("CONFIRMACIÓN IMPORTANTE",`<p>${safe(d.confirma)}</p>`);

 if(d.fuente){
  h+=`<div class="bloque"><h3>INFORMACIÓN OFICIAL</h3>
  <a class="fuente" href="${safe(d.fuente)}" target="_blank" rel="noopener noreferrer">
  ABRIR INFORMACIÓN OFICIAL</a></div>`;
 }
 if($("respuesta"))$("respuesta").innerHTML=h;
 if($("fuenteOficial")){
  $("fuenteOficial").href=d.fuente||"#";
  $("fuenteOficial").style.display=d.fuente?"block":"none";
 }
 mostrar("resultado");
}
function procesar(d){
 if(!d)return;
 if(d.estado==="error"){toast(d.mensaje||"Ocurrió un error.");return}
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
async function iniciarServicio(s){
 try{
  state.servicio=s;state.caso="";state.pregunta_id="";
  state.respuestas={};state.perfil={};state.resultado=null;
  procesar(await api("/api/inicio/"+encodeURIComponent(s)));
 }catch(e){toast(e.message)}
}
async function iniciarCaso(c){
 try{
  const d=await api("/api/iniciar",{
   method:"POST",
   body:JSON.stringify({
    servicio:state.servicio,
    caso:c,
    respuestas:state.respuestas
   })
  });
  if(d.estado==="error"){toast(d.mensaje||"No se pudo iniciar.");return}
  state.caso=c;procesar(d);
 }catch(e){toast(e.message)}
}
async function seleccionarOpcion(id,texto){
 if(state.pregunta_id==="tramite"||!state.caso){
  await iniciarCaso(id);return;
 }
 await responder(texto||id);
}
async function responder(texto){
 texto=String(texto||"").trim();
 if(!texto){toast("Escribe o selecciona una respuesta.");return}
 if(!state.caso){toast("Primero selecciona el trámite.");return}
 if(!state.pregunta_id){toast("No hay una pregunta activa.");return}
 try{
  procesar(await api("/api/responder",{
   method:"POST",
   body:JSON.stringify({
    servicio:state.servicio,
    caso:state.caso,
    pregunta_id:state.pregunta_id,
    texto:texto,
    respuestas:state.respuestas
   })
  }));
 }catch(e){toast(e.message)}
}
async function usarTexto(){
 const x=$("textoUsuario");
 if(x)await responder(x.value);
}
async function descargarPDF(){
 const b=$("pdf");
 if(!state.resultado){toast("Primero termina la consulta.");return}
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
   throw Error(e.detail||"No se pudo generar el PDF.");
  }
  const blob=await r.blob();
  const u=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=u;
  a.download="Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(u),1000);
 }catch(e){toast(e.message)}
 finally{if(b)b.disabled=false}
}
function entrar(){mostrar("servicios")}
function nuevo(){limpiar();mostrar("inicio")}
function salir(){$("salida")?.classList.remove("oculto")}
function cancelarSalida(){$("salida")?.classList.add("oculto")}
function confirmarSalida(){
 $("salida")?.classList.add("oculto");
 limpiar();
 mostrar("inicio");
}
function abrirOficial(){$("infoOficial")?.classList.remove("oculto")}
function cerrarOficial(){$("infoOficial")?.classList.add("oculto")}

let reconocimiento=null;
function voz(){
 const b=$("voz"),x=$("textoUsuario");
 if(!x)return;
 if(!("webkitSpeechRecognition"in window||"SpeechRecognition"in window)){
  toast("Tu navegador no permite entrada por voz.");return;
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
 reconocimiento.onerror=()=>toast("No se pudo reconocer la voz.");
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
 try{await api("/api/estado")}catch(e){console.warn("Servidor:",e.message)}
});
