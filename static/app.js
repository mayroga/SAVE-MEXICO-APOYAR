let servicioActual="";
let ultimaRespuesta="";

function mostrar(id){
  document.querySelectorAll(".pantalla").forEach(x=>x.classList.remove("activa"));
  const p=document.getElementById(id);
  if(p)p.classList.add("activa");
  window.scrollTo(0,0);
}

function entrar(){
  mostrar("info");
}

async function despertarServidor(){
  const e=document.getElementById("servidor");
  try{
    const r=await fetch("/api/estado",{cache:"no-store"});
    e.textContent=r.ok?"Listo":"Preparando...";
  }catch{
    e.textContent="Preparando...";
  }
}

function elegirServicio(servicio){
  servicioActual=servicio;
  cargarServicio(servicio);
}

async function cargarServicio(servicio){
  mostrar("resultado");
  const titulo=document.getElementById("tituloResultado");
  const caja=document.getElementById("resultadoTexto");
  titulo.textContent="PREPARANDO...";
  caja.innerHTML="<p>Un momento, por favor.</p>";

  try{
    const r=await fetch("/api/servicio/"+encodeURIComponent(servicio),{cache:"no-store"});
    const d=await r.json();

    if(!r.ok||!d.ok)throw new Error();

    titulo.textContent=d.nombre;

    caja.innerHTML=
      "<p><strong>"+d.mensaje+"</strong></p>"+
      "<p>La aplicación hará lo siguiente:</p>"+
      "<ol>"+d.proceso.map(x=>"<li>"+x+"</li>").join("")+"</ol>";

    ultimaRespuesta=d.mensaje+" La aplicación hará lo siguiente: "+
      d.proceso.join(". ")+".";

  }catch{
    titulo.textContent="NO SE PUDO CONECTAR";
    caja.innerHTML="<p>Hubo un problema al conectar. Inténtalo nuevamente.</p>";
    ultimaRespuesta="Hubo un problema al conectar. Inténtalo nuevamente.";
  }
}

function mostrarEntrada(){
  mostrar("entrada");
  setTimeout(()=>{
    document.getElementById("texto")?.focus();
  },100);
}

function escuchar(){
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;

  if(!SpeechRecognition){
    mostrarEntrada();
    document.getElementById("escuchando").textContent=
      "Tu navegador no permite escuchar. Puedes escribir.";
    return;
  }

  const r=new SpeechRecognition();
  r.lang="es-MX";
  r.continuous=false;
  r.interimResults=false;
  r.maxAlternatives=1;

  mostrar("entrada");

  const estado=document.getElementById("escuchando");
  estado.textContent="🎙️ TE ESTOY ESCUCHANDO...";

  r.onresult=e=>{
    const texto=e.results[0][0].transcript;
    document.getElementById("texto").value=texto;
    estado.textContent="Esto fue lo que entendí. Pulsa CONTINUAR.";
  };

  r.onerror=()=>{
    estado.textContent="No pude escucharte. Puedes intentarlo otra vez o escribir.";
  };

  r.onend=()=>{
    if(!document.getElementById("texto").value)
      estado.textContent="Puedes hablar otra vez o escribir.";
  };

  r.start();
}

async function enviarTexto(){
  const campo=document.getElementById("texto");
  const texto=campo.value.trim();

  if(!texto){
    document.getElementById("escuchando").textContent=
      "Primero dime qué necesitas.";
    return;
  }

  mostrar("resultado");

  const titulo=document.getElementById("tituloResultado");
  const caja=document.getElementById("resultadoTexto");

  titulo.textContent="ESTOY ENTENDIENDO...";
  caja.innerHTML="<p>Un momento.</p>";

  try{
    const r=await fetch("/api/entender",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({texto})
    });

    const d=await r.json();

    if(!r.ok||!d.ok)throw new Error();

    titulo.textContent=d.encontrado?d.nombre:"VAMOS A INTENTARLO";

    if(d.encontrado){
      caja.innerHTML=
        "<p><strong>"+d.mensaje+"</strong></p>"+
        "<p>"+d.siguiente+"</p>";
      ultimaRespuesta=d.mensaje+" "+d.siguiente;
    }else{
      caja.innerHTML=
        "<p>"+d.mensaje+"</p>"+
        "<p>"+d.siguiente+"</p>";
      ultimaRespuesta=d.mensaje+" "+d.siguiente;
    }

    leerResultado();

  }catch{
    titulo.textContent="NO SE PUDO CONECTAR";
    caja.innerHTML=
      "<p>Hubo un problema. Inténtalo nuevamente.</p>";
    ultimaRespuesta="Hubo un problema. Inténtalo nuevamente.";
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

despertarServidor();
