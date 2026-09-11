let servicio="";
let paso=0;
let ultimaRespuesta="";

function mostrar(id){
  document.querySelectorAll(".pantalla").forEach(p=>p.classList.remove("activa"));
  document.getElementById(id)?.classList.add("activa");
  window.scrollTo(0,0);
}

function entrar(){
  mostrar("info");
}

async function despertar(){
  const e=document.getElementById("servidor");
  try{
    const r=await fetch("/api/estado",{cache:"no-store"});
    e.textContent=r.ok?"Listo":"Preparando...";
  }catch{
    e.textContent="Preparando...";
  }
}

async function iniciarServicio(tipo){
  servicio=tipo;
  paso=0;
  mostrar("pregunta");

  try{
    const r=await fetch("/api/inicio/"+tipo,{cache:"no-store"});
    const d=await r.json();

    if(!r.ok||!d.ok)throw Error();

    mostrarPregunta(d);
  }catch{
    mostrarError("No pudimos conectar con el servicio. Inténtalo nuevamente.");
  }
}

function mostrarPregunta(d){
  paso=d.paso;

  document.getElementById("paso").textContent=
    "PREGUNTA "+(paso+1)+" DE "+d.total;

  document.getElementById("preguntaTexto").textContent=d.pregunta;

  const opciones=document.getElementById("opciones");
  opciones.innerHTML="";

  if(d.opciones&&d.opciones.length){
    d.opciones.forEach(op=>{
      const b=document.createElement("button");
      b.className="respuesta";
      b.textContent=op;
      b.onclick=()=>{
        document.querySelectorAll(".respuesta")
          .forEach(x=>x.classList.remove("seleccionada"));
        b.classList.add("seleccionada");
        document.getElementById("respuestaTexto").value=op;
      };
      opciones.appendChild(b);
    });
  }

  document.getElementById("respuestaTexto").value="";
  document.getElementById("estadoPregunta").textContent="";
}

async function enviarRespuesta(){
  const campo=document.getElementById("respuestaTexto");
  const respuesta=campo.value.trim();

  if(!respuesta){
    document.getElementById("estadoPregunta").textContent=
      "Dime tu respuesta o elige una opción.";
    return;
  }

  const estado=document.getElementById("estadoPregunta");
  estado.textContent="Un momento...";

  try{
    const r=await fetch("/api/responder",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        servicio,
        paso,
        respuesta
      })
    });

    const d=await r.json();

    if(!r.ok||!d.ok)throw Error();

    if(d.terminado){
      mostrarResultado(d);
      return;
    }

    mostrarPregunta(d);

  }catch{
    estado.textContent=
      "No pudimos continuar. Inténtalo nuevamente.";
  }
}

function mostrarResultado(d){
  mostrar("resultado");

  document.getElementById("resultadoTitulo").textContent=
    d.titulo||"TU RESULTADO";

  const caja=document.getElementById("resultadoTexto");
  caja.innerHTML="";

  if(Array.isArray(d.resultado)){
    d.resultado.forEach((texto,i)=>{
      const p=document.createElement("p");
      p.textContent=(i+1)+". "+texto;
      caja.appendChild(p);
    });
    ultimaRespuesta=d.resultado.join(". ");
  }else{
    caja.textContent=d.resultado||"Tu preparación terminó.";
    ultimaRespuesta=d.resultado||"Tu preparación terminó.";
  }

  leerResultado();
}

function escuchar(){
  const Recognition=
    window.SpeechRecognition||
    window.webkitSpeechRecognition;

  if(!Recognition){
    document.getElementById("estadoPregunta").textContent=
      "Tu navegador no permite usar el micrófono. Puedes escribir.";
    return;
  }

  const r=new Recognition();
  r.lang="es-MX";
  r.continuous=false;
  r.interimResults=false;
  r.maxAlternatives=1;

  const estado=document.getElementById("estadoPregunta");
  estado.textContent="🎙️ TE ESTOY ESCUCHANDO...";

  r.onresult=e=>{
    const texto=e.results[0][0].transcript;
    document.getElementById("respuestaTexto").value=texto;
    estado.textContent="Te escuché. Pulsa CONTINUAR.";
  };

  r.onerror=()=>{
    estado.textContent=
      "No pude escucharte. Inténtalo nuevamente.";
  };

  r.onend=()=>{
    if(!document.getElementById("respuestaTexto").value)
      estado.textContent="Puedes hablar nuevamente.";
  };

  r.start();
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
  document.getElementById("resultadoTitulo").textContent="AVISO";
  document.getElementById("resultadoTexto").textContent=texto;
  ultimaRespuesta=texto;
}

despertar();

