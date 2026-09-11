let servicio="",caso="",preguntaId="",respuestas={},ultimaRespuesta="";

const $=id=>document.getElementById(id);

function mostrar(id){
 document.querySelectorAll(".pantalla").forEach(x=>x.classList.remove("activa"));
 $(id)?.classList.add("activa");
 window.scrollTo(0,0);
}

function entrar(){mostrar("info")}

async function despertar(){
 const e=$("servidor");
 try{
  const r=await fetch("/api/estado",{cache:"no-store"});
  e.textContent=r.ok?"Listo":"Preparando...";
 }catch{
  e.textContent="Preparando...";
 }
}

async function iniciarServicio(tipo){
 servicio=tipo;
 caso="";
 preguntaId="";
 respuestas={};
 ultimaRespuesta="";
 mostrar("pregunta");
 $("preguntaTexto").textContent="Un momento...";
 $("opciones").innerHTML="";
 $("respuestaTexto").value="";
 $("estadoPregunta").textContent="";

 try{
  const r=await fetch("/api/inicio/"+tipo,{cache:"no-store"});
  const d=await r.json();
  if(!r.ok||!d.ok)throw Error();
  procesar(d);
 }catch{
  mostrarError("No pudimos iniciar el servicio. Inténtalo nuevamente.");
 }
}

function procesar(d){
 if(d.caso)caso=d.caso;
 if(d.pregunta_id)preguntaId=d.pregunta_id;

 if(d.estado==="pregunta"||d.estado==="necesita_descripcion"){
  mostrar("pregunta");
  mostrarPregunta(d);
  return;
 }

 if(d.estado==="seleccionar"){
  mostrar("pregunta");
  mostrarSeleccion(d);
  return;
 }

 if(d.estado==="resuelto"){
  mostrarResultado(d);
  return;
 }

 if(d.estado==="no_identificado"){
  mostrar("pregunta");
  mostrarPregunta(d);
  return;
 }

 mostrarError(d.mensaje||"No pudimos entender tu caso.");
}

function mostrarPregunta(d){
 $("preguntaTexto").textContent=d.pregunta||"Cuéntame qué necesitas resolver.";
 $("opciones").innerHTML="";
 $("respuestaTexto").value="";
 $("estadoPregunta").textContent="";

 if(d.pregunta_id)preguntaId=d.pregunta_id;

 if(Array.isArray(d.opciones)&&d.opciones.length){
  d.opciones.forEach(op=>{
   const b=document.createElement("button");
   b.className="respuesta";
   b.textContent=op;
   b.onclick=()=>{
    document.querySelectorAll(".respuesta").forEach(x=>x.classList.remove("seleccionada"));
    b.classList.add("seleccionada");
    $("respuestaTexto").value=op;
   };
   $("opciones").appendChild(b);
  });
 }
}

function mostrarSeleccion(d){
 $("preguntaTexto").textContent=d.pregunta||"Elige la opción que más se parece a tu caso.";
 $("opciones").innerHTML="";
 $("respuestaTexto").value="";
 $("estadoPregunta").textContent="";

 (d.opciones||[]).forEach((op,i)=>{
  const b=document.createElement("button");
  b.className="respuesta";
  b.textContent=op;
  b.onclick=()=>{
   caso=(d.casos||[])[i]||"";
   respuestas._confirmado=[caso];
   document.querySelectorAll(".respuesta").forEach(x=>x.classList.remove("seleccionada"));
   b.classList.add("seleccionada");
   $("respuestaTexto").value=op;
  };
  $("opciones").appendChild(b);
 });
}

async function enviarRespuesta(){
 const campo=$("respuestaTexto");
 const texto=campo.value.trim();
 const estado=$("estadoPregunta");

 if(!texto){
  estado.textContent="Dime tu respuesta o elige una opción.";
  return;
 }

 estado.textContent="Un momento...";

 const datos={
  servicio,
  caso,
  texto,
  respuestas,
  pregunta_id:preguntaId
 };

 try{
  const r=await fetch("/api/responder",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify(datos)
  });

  const d=await r.json();

  if(!r.ok||!d.ok){
   estado.textContent=d.mensaje||"No pudimos continuar.";
   return;
  }

  respuestas=d.respuestas||respuestas;

  if(d.caso)caso=d.caso;
  if(d.pregunta_id)preguntaId=d.pregunta_id;

  procesar(d);

 }catch{
  estado.textContent="No pudimos conectar con el servicio. Inténtalo nuevamente.";
 }
}

function mostrarResultado(d){
 mostrar("resultado");

 $("resultadoTitulo").textContent=d.titulo||"TU RESULTADO";

 const caja=$("resultadoTexto");
 caja.innerHTML="";
 let partes=[];

 if(Array.isArray(d.prepara)&&d.prepara.length){
  agregarBloque(caja,"QUÉ DEBES PREPARAR",d.prepara);
  partes.push("Qué debes preparar. "+d.prepara.join(". "));
 }

 if(Array.isArray(d.confirma)&&d.confirma.length){
  agregarBloque(caja,"QUÉ DEBES CONFIRMAR",d.confirma);
  partes.push("Qué debes confirmar. "+d.confirma.join(". "));
 }

 if(d.fuente){
  const p=document.createElement("p");
  p.className="fuente";
  p.innerHTML="<strong>FUENTE OFICIAL</strong><br><a href='"+escapeAttr(d.fuente)+"' target='_blank' rel='noopener'>Consultar información oficial</a>";
  caja.appendChild(p);
  partes.push("Fuente oficial. Consulta la información oficial.");
 }

 if(!partes.length){
  caja.textContent=d.mensaje||"No tenemos información suficiente para darte un resultado.";
  partes.push(d.mensaje||"No tenemos información suficiente para darte un resultado.");
 }

 ultimaRespuesta=partes.join(" ");
 leerResultado();
}

function agregarBloque(caja,titulo,lista){
 const h=document.createElement("h3");
 h.textContent=titulo;
 caja.appendChild(h);

 lista.forEach((texto,i)=>{
  const p=document.createElement("p");
  p.textContent=(i+1)+". "+texto;
  caja.appendChild(p);
 });
}

function escuchar(){
 const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;

 if(!Recognition){
  $("estadoPregunta").textContent="Tu navegador no permite usar el micrófono. Puedes escribir.";
  return;
 }

 const r=new Recognition();
 r.lang="es-MX";
 r.continuous=false;
 r.interimResults=false;
 r.maxAlternatives=1;

 $("estadoPregunta").textContent="🎙️ TE ESTOY ESCUCHANDO...";

 r.onresult=e=>{
  const texto=e.results[0][0].transcript.trim();
  $("respuestaTexto").value=texto;
  $("estadoPregunta").textContent="Te escuché. Pulsa CONTINUAR.";
 };

 r.onerror=()=>{
  $("estadoPregunta").textContent="No pude escucharte. Inténtalo nuevamente.";
 };

 r.onend=()=>{
  if(!$("respuestaTexto").value)
   $("estadoPregunta").textContent="Puedes hablar nuevamente.";
 };

 try{r.start()}catch{
  $("estadoPregunta").textContent="No pude activar el micrófono.";
 }
}

function leerResultado(){
 if(!ultimaRespuesta||!("speechSynthesis" in window))return;

 speechSynthesis.cancel();

 const voz=new SpeechSynthesisUtterance(ultimaRespuesta);
 voz.lang="es-MX";
 voz.rate=.9;
 voz.pitch=1;

 speechSynthesis.speak(voz);
}

function mostrarError(texto){
 mostrar("resultado");
 $("resultadoTitulo").textContent="AVISO";
 $("resultadoTexto").textContent=texto;
 ultimaRespuesta=texto;
}

function escapeAttr(texto){
 return String(texto)
  .replace(/&/g,"&amp;")
  .replace(/"/g,"&quot;")
  .replace(/</g,"&lt;")
  .replace(/>/g,"&gt;");
}

despertar();
