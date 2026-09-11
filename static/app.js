const $=id=>document.getElementById(id);
let servicio="",caso="",preguntaId="",respuestas={},escuchando=false;

const texto=(v="")=>String(v??"").trim();

function mostrar(id,visible=true){
  const e=$(id);
  if(e)e.style.display=visible?"block":"none";
}

function limpiar(){
  const q=$("preguntaTexto"),o=$("opciones"),r=$("respuesta"),t=$("textoUsuario");
  if(q)q.textContent="";
  if(o)o.innerHTML="";
  if(r)r.innerHTML="";
  if(t)t.value="";
}

function hablar(msg){
  if(!msg||!("speechSynthesis" in window))return;
  try{
    speechSynthesis.cancel();
    const u=new SpeechSynthesisUtterance(msg);
    u.lang=(document.documentElement.lang||"es-MX").toLowerCase().startsWith("en")?"en-US":"es-MX";
    u.rate=.92;
    speechSynthesis.speak(u);
  }catch(e){}
}

async function despertar(){
  try{await fetch("/api/estado",{cache:"no-store"});}catch(e){}
}

function pantallaBase(){
  mostrar("inicio",false);
  mostrar("servicios",true);
  mostrar("resultado",false);
  mostrar("pregunta",true);
}

function mostrarTitulo(t){
  const e=$("preguntaTexto");
  if(e)e.textContent=t||"¿Qué necesitas?";
}

function boton(texto,fn,clase="opcion"){
  const b=document.createElement("button");
  b.type="button";
  b.className=clase;
  b.textContent=texto;
  b.onclick=fn;
  return b;
}

function mostrarOpciones(opciones,fn){
  const box=$("opciones");
  if(!box)return;
  box.innerHTML="";
  (opciones||[]).forEach(x=>{
    const id=typeof x==="string"?x:x.id;
    const label=typeof x==="string"?x:(x.texto||x.titulo||x.id);
    box.appendChild(boton(label,()=>fn(id,label)));
  });
}

async function iniciarServicio(tipo){
  servicio=tipo;
  caso="";
  preguntaId="";
  respuestas={};
  limpiar();
  pantallaBase();

  try{
    const r=await fetch("/api/inicio/"+encodeURIComponent(tipo),{cache:"no-store"});
    const d=await r.json();
    procesar(d);
  }catch(e){
    error("No pudimos iniciar. Intenta nuevamente.");
  }
}

function procesar(d){
  if(!d)return error("No recibimos una respuesta.");

  if(d.estado==="necesita_descripcion"){
    caso="";
    preguntaId="";
    mostrarTitulo(d.pregunta||"¿Qué necesitas?");
    if(d.opciones?.length){
      mostrarOpciones(d.opciones,(id)=>{
        if(id==="no_se"){
          mostrarEntrada();
        }else{
          seleccionarCaso(id);
        }
      });
    }else{
      mostrarEntrada();
    }
    return;
  }

  if(d.estado==="seleccionar"){
    mostrarTitulo(d.pregunta||"¿Cuál necesitas?");
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
    mostrarResultado(d);
    return;
  }

  if(d.estado==="no_identificado"){
    mostrarTitulo(d.mensaje||"No encontramos la opción.");
    mostrarEntrada();
    return;
  }

  if(d.estado==="error"){
    error(d.mensaje||"Ocurrió un error.");
    return;
  }

  error("No entendimos la respuesta.");
}

function seleccionarCaso(id){
  if(!id)return;

  caso=id;
  preguntaId="";
  respuestas={_caso:id};

  limpiar();
  mostrarTitulo("Vamos a preparar lo que necesitas...");

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
  const q=$("preguntaTexto");
  const box=$("opciones");

  if(q)q.textContent=d.pregunta||"Responde esta pregunta";
  if(box)box.innerHTML="";

  if(d.titulo){
    const titulo=document.createElement("div");
    titulo.className="tituloCaso";
    titulo.textContent=d.titulo;
    if(box)box.appendChild(titulo);
  }

  if(d.opciones?.length){
    mostrarOpciones(d.opciones,(id,label)=>{
      enviarRespuesta(label||id);
    });
  }else{
    mostrarEntrada();
  }

  mostrar("textoEntrada",true);
  hablar(d.pregunta||"Responde esta pregunta");
}

function mostrarEntrada(){
  mostrar("textoEntrada",true);

  const t=$("textoUsuario");
  if(t){
    t.placeholder="Escribe aquí o usa tu voz";
    t.focus();
  }

  const box=$("opciones");
  if(box && !box.children.length){
    const b=boton("CONTINUAR",()=>enviarRespuesta(texto($("textoUsuario")?.value)),"continuar");
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

function mostrarResultado(d){
  mostrar("pregunta",false);
  mostrar("resultado",true);

  const box=$("respuesta");
  if(!box)return;

  box.innerHTML="";

  agregarResultado(box,"PREPARA",d.prepara);
  agregarResultado(box,"IMPORTANTE",d.confirma);

  if(d.fuente){
    const h=document.createElement("h3");
    h.textContent="FUENTE OFICIAL";
    box.appendChild(h);

    const a=document.createElement("a");
    a.className="fuente";
    a.href=d.fuente;
    a.target="_blank";
    a.rel="noopener noreferrer";
    a.textContent="Ver información oficial";
    box.appendChild(a);
  }

  const nuevo=boton("EMPEZAR DE NUEVO",reiniciar,"continuar");
  box.appendChild(nuevo);

  hablar(
    (d.prepara||"")+
    " "+
    (d.confirma||"")
  );
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

function mostrarEntradaSiHaceFalta(){
  const t=$("textoEntrada");
  if(t)t.style.display="block";
}

function error(msg){
  mostrar("resultado",true);
  mostrar("pregunta",false);

  const box=$("respuesta");
  if(box){
    box.innerHTML="";
    const p=document.createElement("p");
    p.textContent=msg;
    box.appendChild(p);
    box.appendChild(boton("INTENTAR DE NUEVO",reiniciar,"continuar"));
  }

  hablar(msg);
}

function reiniciar(){
  servicio="";
  caso="";
  preguntaId="";
  respuestas={};
  escuchando=false;
  limpiar();

  mostrar("resultado",false);
  mostrar("pregunta",false);
  mostrar("textoEntrada",false);
  mostrar("inicio",true);
  mostrar("servicios",true);

  if($("preguntaTexto"))
    $("preguntaTexto").textContent="¿Qué necesitas?";
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
    const value=texto(e.results?.[0]?.[0]?.transcript);
    if($("textoUsuario"))$("textoUsuario").value=value;
  };

  r.onerror=()=>{
    escuchando=false;
    if(b)b.textContent="🎤 HABLAR";
  };

  r.onend=()=>{
    escuchando=false;
    if(b)b.textContent="🎤 HABLAR";
  };

  try{r.start();}catch(e){}
}

document.addEventListener("DOMContentLoaded",()=>{
  despertar();

  const entrar=$("entrar");
  if(entrar)entrar.onclick=()=>{
    mostrar("inicio",false);
    mostrar("servicios",true);
  };

  const cita=$("servicioCita");
  if(cita)cita.onclick=()=>iniciarServicio("cita");

  const documento=$("servicioDocumento");
  if(documento)documento.onclick=()=>iniciarServicio("documento");

  const continuar=$("continuar");
  if(continuar)continuar.onclick=()=>enviarRespuesta();

  const voz=$("voz");
  if(voz)voz.onclick=iniciarVoz;

  const nuevo=$("nuevo");
  if(nuevo)nuevo.onclick=reiniciar;

  const entrada=$("textoUsuario");
  if(entrada){
    entrada.addEventListener("keydown",e=>{
      if(e.key==="Enter"&&!e.shiftKey){
        e.preventDefault();
        enviarRespuesta();
      }
    });
  }

  mostrar("resultado",false);
  mostrar("pregunta",false);
  mostrar("textoEntrada",false);
});
