const $=id=>document.getElementById(id);
let servicio="",caso="",preguntaId="",respuestas={},escuchando=false;

function mostrar(id,visible=true){
  const e=$(id);
  if(e)e.style.display=visible?"block":"none";
}

function texto(v=""){return String(v??"").trim();}

function hablar(msg){
  if(!msg||!("speechSynthesis" in window))return;
  try{
    speechSynthesis.cancel();
    const u=new SpeechSynthesisUtterance(msg);
    u.lang="es-MX";
    u.rate=.92;
    speechSynthesis.speak(u);
  }catch(e){}
}

async function despertar(){
  try{await fetch("/api/estado",{cache:"no-store"});}catch(e){}
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
  b.type="button";
  b.className=clase;
  b.textContent=label;
  b.onclick=fn;
  return b;
}

/* =====================================================
   FUNCIONES GLOBALES PARA LOS onclick DEL index.html
   ===================================================== */

window.entrar=function(){
  mostrar("inicio",false);
  mostrar("servicios",true);
  mostrar("pregunta",false);
  mostrar("resultado",false);
};

window.iniciarCita=function(){
  iniciarServicio("cita");
};

window.iniciarDocumento=function(){
  iniciarServicio("documento");
};

window.iniciarServicio=function(tipo){
  iniciarServicio(tipo);
};

window.nuevo=function(){
  reiniciar();
};

window.reiniciar=function(){
  reiniciar();
};

window.iniciarVoz=function(){
  iniciarVoz();
};

window.enviar=function(){
  enviarRespuesta();
};

window.continuar=function(){
  enviarRespuesta();
};

/* Compatibilidad con nombres que pueda tener el HTML */
window.cita=function(){
  iniciarServicio("cita");
};

window.documento=function(){
  iniciarServicio("documento");
};

window.servicioCita=function(){
  iniciarServicio("cita");
};

window.servicioDocumento=function(){
  iniciarServicio("documento");
};

/* =====================================================
   INICIO
   ===================================================== */

function iniciarServicio(tipo){
  servicio=tipo;
  caso="";
  preguntaId="";
  respuestas={};

  limpiar();
  mostrar("inicio",false);
  mostrar("servicios",false);
  mostrar("resultado",false);
  mostrar("pregunta",true);

  const q=$("preguntaTexto");
  if(q)q.textContent="Un momento...";

  fetch("/api/inicio/"+encodeURIComponent(tipo),{cache:"no-store"})
    .then(r=>r.json())
    .then(procesar)
    .catch(()=>error("No pudimos iniciar. Intenta nuevamente."));
}

/* =====================================================
   PROCESAR RESPUESTA DEL SERVIDOR
   ===================================================== */

function procesar(d){
  if(!d){
    error("No recibimos una respuesta.");
    return;
  }

  if(d.respuestas)respuestas=d.respuestas;
  if(d.caso)caso=d.caso;
  if(d.pregunta_id)preguntaId=d.pregunta_id;

  if(d.estado==="necesita_descripcion"){
    mostrarTitulo(d.pregunta||"¿Qué necesitas?");
    mostrar("pregunta",true);
    mostrar("resultado",false);

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
    mostrar("pregunta",true);
    mostrar("resultado",false);
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

/* =====================================================
   MOSTRAR OPCIONES
   ===================================================== */

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

/* =====================================================
   SELECCIÓN DIRECTA
   ===================================================== */

function seleccionarCaso(id){
  if(!id)return;

  caso=id;
  preguntaId="";
  respuestas={_caso:id};

  const box=$("opciones");
  if(box)box.innerHTML="";

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

/* =====================================================
   PREGUNTA
   ===================================================== */

function mostrarPregunta(d){
  mostrar("pregunta",true);
  mostrar("resultado",false);

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

/* =====================================================
   ESCRIBIR / VOZ
   ===================================================== */

function mostrarEntrada(){
  mostrar("textoEntrada",true);

  const t=$("textoUsuario");
  if(t){
    t.placeholder="Escribe aquí o usa tu voz";
    setTimeout(()=>t.focus(),50);
  }

  const box=$("opciones");
  if(box&&!box.querySelector(".continuar")){
    const b=boton(
      "CONTINUAR",
      ()=>enviarRespuesta(),
      "continuar"
    );
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

/* =====================================================
   RESULTADO
   ===================================================== */

function mostrarResultado(d){
  mostrar("pregunta",false);
  mostrar("resultado",true);
  mostrar("textoEntrada",false);

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

  box.appendChild(
    boton("EMPEZAR DE NUEVO",reiniciar,"continuar")
  );

  hablar((d.prepara||"")+" "+(d.confirma||""));
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

/* =====================================================
   ERROR
   ===================================================== */

function error(msg){
  mostrar("pregunta",false);
  mostrar("resultado",true);

  const box=$("respuesta");
  if(box){
    box.innerHTML="";

    const p=document.createElement("p");
    p.textContent=msg;
    box.appendChild(p);

    box.appendChild(
      boton("INTENTAR DE NUEVO",reiniciar,"continuar")
    );
  }

  hablar(msg);
}

/* =====================================================
   REINICIAR
   ===================================================== */

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

  const q=$("preguntaTexto");
  if(q)q.textContent="¿Qué necesitas?";
}

/* =====================================================
   RECONOCIMIENTO DE VOZ
   ===================================================== */

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
    const t=$("textoUsuario");
    if(t)t.value=value;

    /* Si estaba describiendo qué necesita,
       dejamos el texto listo para continuar. */
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

/* =====================================================
   INICIO DEL DOCUMENTO
   ===================================================== */

document.addEventListener("DOMContentLoaded",()=>{
  despertar();

  const e=$("entrar");
  if(e)e.onclick=window.entrar;

  const c=$("servicioCita");
  if(c)c.onclick=()=>iniciarServicio("cita");

  const d=$("servicioDocumento");
  if(d)d.onclick=()=>iniciarServicio("documento");

  const v=$("voz");
  if(v)v.onclick=iniciarVoz;

  const cont=$("continuar");
  if(cont)cont.onclick=enviarRespuesta;

  const nuevoBtn=$("nuevo");
  if(nuevoBtn)nuevoBtn.onclick=reiniciar;

  const t=$("textoUsuario");
  if(t){
    t.addEventListener("keydown",e=>{
      if(e.key==="Enter"&&!e.shiftKey){
        e.preventDefault();
        enviarRespuesta();
      }
    });
  }

  mostrar("resultado",false);
  mostrar("pregunta",false);
});
