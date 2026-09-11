const $=id=>document.getElementById(id);
let servicio="",caso="",preguntaId="",respuestas={},escuchando=false;

function mostrar(id,v=true){const e=$(id);if(e)e.style.display=v?"block":"none"}
function texto(v=""){return String(v??"").trim()}

function hablar(msg){
 if(!msg||!("speechSynthesis"in window))return;
 try{
  speechSynthesis.cancel();
  const u=new SpeechSynthesisUtterance(msg);
  u.lang="es-MX";u.rate=.92;speechSynthesis.speak(u);
 }catch(e){}
}

async function despertar(){try{await fetch("/api/estado",{cache:"no-store"})}catch(e){}}

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

/* FUNCIONES COMPATIBLES CON index.html */
window.entrar=()=>{
 mostrar("inicio",false);mostrar("servicios",true);
 mostrar("pregunta",false);mostrar("resultado",false);
};

window.iniciarCita=()=>iniciarServicioInterno("cita");
window.iniciarDocumento=()=>iniciarServicioInterno("documento");
window.iniciarServicio=tipo=>iniciarServicioInterno(tipo);
window.cita=()=>iniciarServicioInterno("cita");
window.documento=()=>iniciarServicioInterno("documento");
window.servicioCita=()=>iniciarServicioInterno("cita");
window.servicioDocumento=()=>iniciarServicioInterno("documento");
window.nuevo=()=>reiniciar();
window.reiniciar=()=>reiniciar();
window.iniciarVoz=()=>iniciarVoz();
window.enviar=()=>enviarRespuesta();
window.continuar=()=>enviarRespuesta();

/* INICIO DE SERVICIO */
function iniciarServicioInterno(tipo){
 servicio=tipo;caso="";preguntaId="";respuestas={};
 limpiar();
 mostrar("inicio",false);mostrar("servicios",false);
 mostrar("resultado",false);mostrar("pregunta",true);
 mostrarTitulo("Un momento...");

 fetch("/api/inicio/"+encodeURIComponent(tipo),{cache:"no-store"})
 .then(r=>r.json()).then(procesar)
 .catch(()=>error("No pudimos iniciar. Intenta nuevamente."));
}

/* PROCESAR SERVIDOR */
function procesar(d){
 if(!d)return error("No recibimos una respuesta.");
 if(d.respuestas)respuestas=d.respuestas;
 if(d.caso)caso=d.caso;
 if(d.pregunta_id)preguntaId=d.pregunta_id;

 if(d.estado==="necesita_descripcion"){
  mostrar("pregunta",true);mostrar("resultado",false);
  mostrarTitulo(d.pregunta||"¿Qué necesitas?");
  if(d.opciones?.length){
   mostrarOpciones(d.opciones,id=>id==="no_se"?mostrarEntrada():seleccionarCaso(id));
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
  caso=d.caso||caso;preguntaId=d.pregunta_id||"";
  mostrarPregunta(d);return;
 }

 if(d.estado==="resuelto"){
  caso=d.caso||caso;preguntaId="";
  mostrarResultado(d);return;
 }

 if(d.estado==="no_identificado"){
  mostrarTitulo(d.mensaje||"No encontramos la opción.");
  mostrarEntrada();return;
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

/* SELECCIÓN DIRECTA */
function seleccionarCaso(id){
 if(!id)return;
 caso=id;preguntaId="";respuestas={_caso:id};
 const box=$("opciones");if(box)box.innerHTML="";
 mostrarTitulo("Vamos a preparar lo que necesitas...");

 fetch("/api/responder",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({
   servicio,caso:id,texto:"",respuestas,pregunta_id:""
  })
 })
 .then(r=>r.json()).then(procesar)
 .catch(()=>error("No pudimos continuar."));
}

/* PREGUNTAS */
function mostrarPregunta(d){
 mostrar("pregunta",true);mostrar("resultado",false);
 const q=$("preguntaTexto"),box=$("opciones");
 if(q)q.textContent=d.pregunta||"Responde esta pregunta";
 if(box)box.innerHTML="";

 if(d.titulo){
  const t=document.createElement("div");
  t.className="tituloCaso";t.textContent=d.titulo;
  if(box)box.appendChild(t);
 }

 if(d.opciones?.length)
  mostrarOpciones(d.opciones,(id,label)=>enviarRespuesta(label||id));
 else mostrarEntrada();

 mostrar("textoEntrada",true);
 hablar(d.pregunta||"Responde esta pregunta");
}

function mostrarEntrada(){
 mostrar("textoEntrada",true);
 const t=$("textoUsuario");
 if(t){t.placeholder="Escribe aquí o usa tu voz";setTimeout(()=>t.focus(),50)}

 const box=$("opciones");
 if(box&&!box.querySelector(".continuar")){
  const b=boton("CONTINUAR",()=>enviarRespuesta(),"continuar");
  b.classList.add("continuar");box.appendChild(b);
 }
}

/* RESPUESTA */
async function enviarRespuesta(valor){
 valor=texto(valor||$("textoUsuario")?.value);

 if(!valor){
  hablar("Necesito tu respuesta para continuar.");
  if($("textoUsuario"))$("textoUsuario").focus();
  return;
 }

 if(preguntaId)respuestas[preguntaId]=valor;
 if(caso)respuestas._caso=caso;

 const box=$("opciones");if(box)box.innerHTML="";
 mostrarTitulo("Un momento...");

 try{
  const r=await fetch("/api/responder",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    servicio,caso,texto:valor,respuestas,pregunta_id:preguntaId
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

/* RESULTADO */
function mostrarResultado(d){
 mostrar("pregunta",false);mostrar("resultado",true);mostrar("textoEntrada",false);
 const box=$("respuesta");if(!box)return;
 box.innerHTML="";
 agregarResultado(box,"PREPARA",d.prepara);
 agregarResultado(box,"IMPORTANTE",d.confirma);

 if(d.fuente){
  const h=document.createElement("h3");
  h.textContent="FUENTE OFICIAL";box.appendChild(h);
  const a=document.createElement("a");
  a.className="fuente";a.href=d.fuente;a.target="_blank";
  a.rel="noopener noreferrer";a.textContent="Ver información oficial";
  box.appendChild(a);
 }

 box.appendChild(boton("EMPEZAR DE NUEVO",reiniciar,"continuar"));
 hablar((d.prepara||"")+" "+(d.confirma||""));
}

function agregarResultado(box,titulo,contenido){
 if(!contenido)return;
 const h=document.createElement("h3");
 h.textContent=titulo;box.appendChild(h);
 const p=document.createElement("p");
 p.textContent=contenido;box.appendChild(p);
}

/* ERROR */
function error(msg){
 mostrar("pregunta",false);mostrar("resultado",true);
 const box=$("respuesta");
 if(box){
  box.innerHTML="";
  const p=document.createElement("p");
  p.textContent=msg;box.appendChild(p);
  box.appendChild(boton("INTENTAR DE NUEVO",reiniciar,"continuar"));
 }
 hablar(msg);
}

/* REINICIAR */
function reiniciar(){
 servicio="";caso="";preguntaId="";respuestas={};escuchando=false;
 limpiar();
 mostrar("resultado",false);mostrar("pregunta",false);
 mostrar("textoEntrada",false);mostrar("inicio",true);mostrar("servicios",true);
 const q=$("preguntaTexto");if(q)q.textContent="¿Qué necesitas?";
}

/* VOZ */
function iniciarVoz(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR)return hablar("Tu navegador no tiene reconocimiento de voz.");
 if(escuchando)return;

 const r=new SR();
 r.lang="es-MX";r.interimResults=false;r.maxAlternatives=1;
 escuchando=true;

 const b=$("voz");if(b)b.textContent="ESCUCHANDO...";

 r.onresult=e=>{
  const v=texto(e.results?.[0]?.[0]?.transcript);
  const t=$("textoUsuario");if(t)t.value=v;
 };

 r.onerror=()=>{
  escuchando=false;if(b)b.textContent="🎤 HABLAR";
 };

 r.onend=()=>{
  escuchando=false;if(b)b.textContent="🎤 HABLAR";
 };

 try{r.start()}catch(e){}
}

/* DOM */
document.addEventListener("DOMContentLoaded",()=>{
 despertar();

 const e=$("entrar");if(e)e.onclick=window.entrar;
 const c=$("servicioCita");if(c)c.onclick=()=>iniciarServicioInterno("cita");
 const d=$("servicioDocumento");if(d)d.onclick=()=>iniciarServicioInterno("documento");
 const v=$("voz");if(v)v.onclick=iniciarVoz;
 const cont=$("continuar");if(cont)cont.onclick=enviarRespuesta;
 const n=$("nuevo");if(n)n.onclick=reiniciar;

 const t=$("textoUsuario");
 if(t)t.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){
   e.preventDefault();enviarRespuesta();
  }
 });

 mostrar("resultado",false);
 mostrar("pregunta",false);
});
