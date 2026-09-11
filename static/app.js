const $=id=>document.getElementById(id);
let servicio="",caso="",preguntaId="",respuestas={},escuchando=false,fuenteActual="";

function mostrar(id,v=true){const e=$(id);if(e)e.style.display=v?"block":"none"}
function texto(v=""){return String(v??"").trim()}

function hablar(msg){
 if(!msg||!("speechSynthesis"in window))return;
 try{
  speechSynthesis.cancel();
  const u=new SpeechSynthesisUtterance(msg);
  u.lang="es-MX";u.rate=.92;
  speechSynthesis.speak(u);
 }catch(e){}
}

async function despertar(){
 try{await fetch("/api/estado",{cache:"no-store"})}catch(e){}
}

function limpiar(){
 const q=$("preguntaTexto"),o=$("opciones"),r=$("respuesta"),t=$("textoUsuario");
 if(q)q.textContent="";
 if(o)o.innerHTML="";
 if(r)r.innerHTML="";
 if(t)t.value="";
}

function boton(label,fn,clase="opcion"){
 const b=document.createElement("button");
 b.type="button";b.className=clase;b.textContent=label;b.onclick=fn;
 return b;
}

function entrar(){
 mostrar("inicio",false);
 mostrar("servicios",true);
 mostrar("pregunta",false);
 mostrar("resultado",false);
}

function iniciarCita(){iniciarServicioInterno("cita")}
function iniciarDocumento(){iniciarServicioInterno("documento")}
function cita(){iniciarServicioInterno("cita")}
function documento(){iniciarServicioInterno("documento")}
function servicioCita(){iniciarServicioInterno("cita")}
function servicioDocumento(){iniciarServicioInterno("documento")}

function iniciarServicioInterno(tipo){
 servicio=tipo;caso="";preguntaId="";respuestas={};fuenteActual="";
 limpiar();
 mostrar("inicio",false);
 mostrar("servicios",false);
 mostrar("resultado",false);
 mostrar("pregunta",true);
 mostrar("textoEntrada",false);
 mostrarTitulo("Un momento...");
 fetch("/api/inicio/"+encodeURIComponent(tipo),{cache:"no-store"})
 .then(r=>r.json()).then(procesar)
 .catch(()=>error("No pudimos iniciar. Intenta nuevamente."));
}

function procesar(d){
 if(!d)return error("No recibimos una respuesta.");
 if(d.respuestas)respuestas=d.respuestas;
 if(d.caso)caso=d.caso;
 if(d.pregunta_id)preguntaId=d.pregunta_id;

 if(d.estado==="necesita_descripcion"){
  mostrar("pregunta",true);mostrar("resultado",false);
  mostrarTitulo(d.pregunta||"¿Qué necesitas?");
  if(d.opciones?.length){
   mostrarOpciones(d.opciones,id=>{
    if(id==="no_se")mostrarEntrada();
    else seleccionarCaso(id);
   });
  }else mostrarEntrada();
  return;
 }

 if(d.estado==="seleccionar"){
  mostrar("pregunta",true);mostrar("resultado",false);
  mostrarTitulo(d.pregunta||"¿Cuál de estas opciones necesitas?");
  mostrarOpciones(d.opciones||[],id=>seleccionarCaso(id));
  return;
 }

 if(d.estado==="pregunta"){
  caso=d.caso||caso;
  preguntaId=d.pregunta_id||"";
  mostrarPregunta(d);
  return;
 }

 if(d.estado==="resuelto"){
  caso=d.caso||caso;
  preguntaId="";
  if(d.respuestas)respuestas=d.respuestas;
  mostrarResultado(d);
  return;
 }

 if(d.estado==="no_identificado"){
  mostrar("pregunta",true);mostrar("resultado",false);
  mostrarTitulo(d.mensaje||"No encontramos esa opción.");
  mostrarEntrada();
  return;
 }

 if(d.estado==="error")return error(d.mensaje||"Ocurrió un error.");
 error("No entendimos la respuesta.");
}

function mostrarTitulo(t){
 const e=$("preguntaTexto");
 if(e)e.textContent=t||"¿Qué necesitas?";
}

function mostrarOpciones(opciones,fn){
 const box=$("opciones");
 if(!box)return;
 box.innerHTML="";
 opciones.forEach(x=>{
  const id=typeof x==="string"?x:x.id;
  const label=typeof x==="string"?x:(x.texto||x.titulo||x.id);
  box.appendChild(boton(label,()=>fn(id,label)));
 });
}

function seleccionarCaso(id){
 if(!id)return;
 caso=id;
 preguntaId="";
 respuestas={_caso:id};
 const box=$("opciones");
 if(box)box.innerHTML="";
 mostrarTitulo("Un momento...");
 fetch("/api/responder",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({
   servicio,
   caso:id,
   texto:"",
   respuestas,
   pregunta_id:""
  })
 })
 .then(r=>r.json())
 .then(procesar)
 .catch(()=>error("No pudimos continuar."));
}

function mostrarPregunta(d){
 mostrar("pregunta",true);
 mostrar("resultado",false);
 const q=$("preguntaTexto"),box=$("opciones");
 if(q)q.textContent=d.pregunta||"Responde esta pregunta";
 if(box)box.innerHTML="";

 if(d.titulo){
  const t=document.createElement("div");
  t.className="tituloCaso";
  t.textContent=d.titulo;
  if(box)box.appendChild(t);
 }

 if(d.opciones?.length){
  mostrarOpciones(d.opciones,(id,label)=>enviarRespuesta(label||id));
 }else mostrarEntrada();

 mostrar("textoEntrada",true);
 hablar(d.pregunta||"Responde esta pregunta");
}

function mostrarEntrada(){
 mostrar("textoEntrada",true);
 const t=$("textoUsuario");
 if(t){
  t.placeholder="Escribe aquí con tus propias palabras...";
  setTimeout(()=>t.focus(),50);
 }

 const box=$("opciones");
 if(box&&!box.querySelector(".continuar")){
  const b=boton("CONTINUAR",()=>enviarRespuesta(),"continuar");
  b.classList.add("continuar");
  box.appendChild(b);
 }
}

async function enviarRespuesta(valor){
 valor=texto(valor||$("textoUsuario")?.value);

 if(!valor){
  hablar("Necesito tu respuesta para continuar.");
  if($("textoUsuario"))$("textoUsuario").focus();
  return;
 }

 if(preguntaId)respuestas[preguntaId]=valor;
 if(caso)respuestas._caso=caso;

 const box=$("opciones");
 if(box)box.innerHTML="";
 mostrarTitulo("Un momento...");

 try{
  const r=await fetch("/api/responder",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    servicio,
    caso,
    texto:valor,
    respuestas,
    pregunta_id:preguntaId
   })
  });

  const d=await r.json();

  if(d.respuestas)respuestas=d.respuestas;
  if(d.caso)caso=d.caso;

  procesar(d);
 }catch(e){
  error("No pudimos continuar. Intenta nuevamente.");
 }
}

function agregarResultado(box,titulo,contenido){
 if(!contenido)return;
 const h=document.createElement("h3");
 h.textContent=titulo;
 box.appendChild(h);

 const p=document.createElement("p");
 p.textContent=contenido;
 box.appendChild(p);
}

function agregarLista(box,titulo,items,simbolo){
 const h=document.createElement("h3");
 h.textContent=titulo;
 box.appendChild(h);

 if(!items||!items.length){
  const p=document.createElement("p");
  p.textContent="No hay elementos en esta categoría.";
  box.appendChild(p);
  return;
 }

 items.forEach(x=>{
  const p=document.createElement("p");
  p.textContent=(simbolo||"•")+" "+x;
  box.appendChild(p);
 });
}

function mostrarResultado(d){
 mostrar("pregunta",false);
 mostrar("resultado",true);
 mostrar("textoEntrada",false);

 caso=d.caso||caso;
 respuestas=d.respuestas||respuestas;
 fuenteActual=d.fuente||"";

 window.casoActual=caso;
 window.respuestasActuales=respuestas;

 const box=$("respuesta");
 if(!box)return;
 box.innerHTML="";

 const c=d.checklist||{};
 agregarLista(box,"LO QUE YA TIENES",c.tiene,"☑");
 agregarLista(box,"LO QUE TE FALTA",c.falta,"☐");
 agregarLista(box,"LO QUE NO ESTÁS SEGURO DE TENER",c.revisar,"□");

 agregarResultado(box,"PREPARA",d.prepara);
 agregarResultado(box,"PAGO",d.pago);
 agregarResultado(box,"IMPORTANTE",d.confirma);

 if(d.ruta){
  agregarResultado(box,"CITA",d.ruta.cita);
  agregarResultado(box,"ORIGINAL",d.ruta.llevar_original);
  agregarResultado(box,"COPIA",d.ruta.copias);
 }

 const oficial=$("oficial");
 if(oficial)oficial.style.display=fuenteActual?"block":"none";

 const pdf=$("pdf");
 if(pdf)pdf.style.display=caso?"block":"none";

 hablar(
  (d.prepara||"")+" "+
  (d.confirma||"")
 );
}

function abrirFuente(){
 if(!fuenteActual)return;
 const a=$("fuenteOficial");
 if(a)a.href=fuenteActual;
 const m=$("infoOficial");
 if(m)m.classList.remove("oculto");
}

function cerrarFuente(){
 const m=$("infoOficial");
 if(m)m.classList.add("oculto");
}

async function descargarPDF(){
 if(!caso){
  hablar("Primero completa la consulta.");
  return;
 }

 const b=$("pdf");
 if(b){
  b.disabled=true;
  b.textContent="PREPARANDO PDF...";
 }

 try{
  const r=await fetch("/api/pdf",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    caso,
    respuestas
   })
  });

  if(!r.ok)throw new Error("PDF");

  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");

  a.href=url;
  a.download="Hoja_Ruta_Mexicano_Apoya_Mexicano.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(()=>URL.revokeObjectURL(url),1500);
 }catch(e){
  alert("No pudimos generar el PDF. Intenta nuevamente.");
 }finally{
  if(b){
   b.disabled=false;
   b.textContent="DESCARGAR HOJA DE RUTA PDF";
  }
 }
}

function pedirSalir(){
 const m=$("salida");
 if(m)m.classList.remove("oculto");
}

function cancelarSalida(){
 const m=$("salida");
 if(m)m.classList.add("oculto");
}

function confirmarSalida(){
 cancelarSalida();
 reiniciar();
 window.scrollTo({top:0,behavior:"smooth"});
}

function error(msg){
 mostrar("pregunta",false);
 mostrar("resultado",true);
 mostrar("textoEntrada",false);

 const box=$("respuesta");
 if(box){
  box.innerHTML="";
  const h=document.createElement("h3");
  h.textContent="AVISO";
  box.appendChild(h);

  const p=document.createElement("p");
  p.textContent=msg;
  box.appendChild(p);

  box.appendChild(
   boton("INTENTAR DE NUEVO",reiniciar,"continuar")
  );
 }

 hablar(msg);
}

function reiniciar(){
 servicio="";
 caso="";
 preguntaId="";
 respuestas={};
 fuenteActual="";
 escuchando=false;

 if("speechSynthesis"in window){
  try{speechSynthesis.cancel()}catch(e){}
 }

 limpiar();

 mostrar("inicio",true);
 mostrar("servicios",false);
 mostrar("pregunta",false);
 mostrar("resultado",false);
 mostrar("textoEntrada",false);

 const m1=$("infoOficial");
 const m2=$("salida");
 if(m1)m1.classList.add("oculto");
 if(m2)m2.classList.add("oculto");

 const q=$("preguntaTexto");
 if(q)q.textContent="¿Qué necesitas?";

 window.casoActual="";
 window.respuestasActuales={};
}

function iniciarVoz(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;

 if(!SR){
  hablar("Tu navegador no tiene reconocimiento de voz.");
  return;
 }

 if(escuchando)return;

 const r=new SR();
 r.lang="es-MX";
 r.interimResults=false;
 r.maxAlternatives=1;
 escuchando=true;

 const b=$("voz");
 if(b)b.textContent="ESCUCHANDO...";

 r.onresult=e=>{
  const v=texto(e.results?.[0]?.[0]?.transcript);
  const t=$("textoUsuario");
  if(t)t.value=v;
 };

 r.onerror=()=>{
  escuchando=false;
  if(b)b.textContent="🎤 HABLAR";
 };

 r.onend=()=>{
  escuchando=false;
  if(b)b.textContent="🎤 HABLAR";
 };

 try{r.start()}catch(e){
  escuchando=false;
  if(b)b.textContent="🎤 HABLAR";
 }
}

window.entrar=entrar;
window.iniciarCita=iniciarCita;
window.iniciarDocumento=iniciarDocumento;
window.iniciarServicio=iniciarServicioInterno;
window.cita=cita;
window.documento=documento;
window.servicioCita=servicioCita;
window.servicioDocumento=servicioDocumento;
window.nuevo=reiniciar;
window.reiniciar=reiniciar;
window.iniciarVoz=iniciarVoz;
window.enviar=enviarRespuesta;
window.continuar=enviarRespuesta;
window.descargarPDF=descargarPDF;
window.abrirFuente=abrirFuente;
window.cerrarFuente=cerrarFuente;
window.pedirSalir=pedirSalir;
window.confirmarSalida=confirmarSalida;
window.cancelarSalida=cancelarSalida;

document.addEventListener("DOMContentLoaded",()=>{
 despertar();

 const entrarBtn=$("entrar");
 if(entrarBtn)entrarBtn.onclick=entrar;

 const citaBtn=$("servicioCita");
 if(citaBtn)citaBtn.onclick=iniciarCita;

 const docBtn=$("servicioDocumento");
 if(docBtn)docBtn.onclick=iniciarDocumento;

 const vozBtn=$("voz");
 if(vozBtn)vozBtn.onclick=iniciarVoz;

 const cont=$("continuar");
 if(cont)cont.onclick=enviarRespuesta;

 const nuevo=$("nuevo");
 if(nuevo)nuevo.onclick=reiniciar;

 const pdf=$("pdf");
 if(pdf)pdf.onclick=descargarPDF;

 const oficial=$("oficial");
 if(oficial)oficial.onclick=abrirFuente;

 const cerrar=$("cerrarOficial");
 if(cerrar)cerrar.onclick=cerrarFuente;

 const salir=$("salir");
 if(salir)salir.onclick=pedirSalir;

 const confirmar=$("confirmarSalida");
 if(confirmar)confirmar.onclick=confirmarSalida;

 const cancelar=$("cancelarSalida");
 if(cancelar)cancelar.onclick=cancelarSalida;

 const t=$("textoUsuario");
 if(t)t.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){
   e.preventDefault();
   enviarRespuesta();
  }
 });

 mostrar("resultado",false);
 mostrar("pregunta",false);
 mostrar("textoEntrada",false);
});
