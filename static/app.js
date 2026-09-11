const $=id=>document.getElementById(id);
const state={servicio:"",caso:"",preguntaId:"",respuestas:{},escuchando:false,fuenteActual:"",resultado:null,catalogo:false};

async function api(url,opt={}){
 try{
  const r=await fetch(url,{headers:{"Content-Type":"application/json",...(opt.headers||{})},...opt});
  let d={};try{d=await r.json()}catch(e){}
  if(!r.ok)throw Error(d.detail||d.error||"No se pudo completar la operación.");
  return d;
 }catch(e){toast(e.message||"No se pudo completar la operación.");throw e}
}

function toast(t){
 let x=document.querySelector(".toast");
 if(!x){x=document.createElement("div");x.className="toast";document.body.appendChild(x)}
 x.textContent=t;x.classList.add("show");clearTimeout(x._t);
 x._t=setTimeout(()=>x.classList.remove("show"),3200);
}
function mostrar(id,on=true){$(id)?.classList.toggle("oculto",!on)}
function limpiar(id){if($(id))$(id).innerHTML=""}
function texto(v){return String(v??"").trim()}

function hablar(t){
 if(!("speechSynthesis"in window)||!texto(t))return;
 speechSynthesis.cancel();
 const u=new SpeechSynthesisUtterance(texto(t));
 u.lang=document.documentElement.lang==="en"?"en-US":"es-MX";
 u.rate=.96;speechSynthesis.speak(u);
}

async function despertar(){try{await api("/api/estado")}catch(e){}}

function reset(){
 state.servicio="";state.caso="";state.preguntaId="";state.respuestas={};
 state.escuchando=false;state.fuenteActual="";state.resultado=null;state.catalogo=false;
 if($("textoUsuario"))$("textoUsuario").value="";
 mostrar("inicio",true);mostrar("servicios",false);mostrar("pregunta",false);
 mostrar("resultado",false);mostrar("infoOficial",false);mostrar("salida",false);
 limpiar("opciones");
 if($("preguntaTexto"))$("preguntaTexto").textContent="¿Qué necesitas?";
 if($("paso"))$("paso").textContent="";
 window.scrollTo({top:0,behavior:"smooth"});
}

function iniciar(){
 mostrar("inicio",false);mostrar("servicios",true);window.scrollTo({top:0,behavior:"smooth"});
}

async function seleccionarServicio(servicio){
 state.servicio=servicio;state.caso="";state.respuestas={};state.catalogo=true;
 try{
  const d=await api("/api/inicio/"+encodeURIComponent(servicio));
  procesar(d);
 }catch(e){}
}

function seleccionarCaso(valor,label){
 const v=texto(valor),nombre=texto(label)||v;
 if(!v)return;
 state.caso=v;
 state.catalogo=false;
 state.preguntaId="";
 limpiar("opciones");
 $("preguntaTexto").textContent="PREPARANDO TU TRÁMITE";
 if($("paso"))$("paso").textContent="TRÁMITE";
 mostrar("servicios",false);mostrar("pregunta",true);
 if($("textoEntrada"))$("textoEntrada").classList.add("oculto");
 try{
  iniciarCaso(v,nombre);
 }catch(e){}
}

async function iniciarCaso(caso,nombre){
 try{
  const d=await api("/api/responder",{method:"POST",body:JSON.stringify({
   servicio:state.servicio,
   caso:caso,
   pregunta_id:"",
   texto:nombre,
   respuestas:{}
  })});
  procesar(d);
 }catch(e){}
}

function procesar(d){
 if(!d)return;
 if(d.fuente)state.fuenteActual=d.fuente;
 if(d.resultado)state.resultado=d.resultado;
 if(d.respuestas&&typeof d.respuestas==="object")
  state.respuestas={...state.respuestas,...d.respuestas};
 if(d.caso&&typeof d.caso==="string"&&!d.catalogo&&!d.tipo==="catalogo")
  state.caso=d.caso;

 const tipo=String(d.tipo||"").toLowerCase();
 if(tipo==="catalogo"||d.catalogo||d.tramites||d.casos||d.opciones_tramite){
  mostrarCatalogo(d);
  return;
 }
 if(tipo==="resuelto"||d.estado_texto||d.resultado){
  mostrarResultado(d.resultado||d);
  return;
 }
 mostrarPregunta(d);
}

function extraerOpciones(d){
 return d.opciones_tramite||d.tramites||d.casos||d.catalogo||d.opciones||[];
}

function mostrarCatalogo(d){
 state.catalogo=true;
 mostrar("inicio",false);mostrar("servicios",false);mostrar("resultado",false);mostrar("pregunta",true);
 limpiar("opciones");
 if($("textoEntrada"))$("textoEntrada").classList.add("oculto");
 const titulo=d.texto||d.pregunta||"¿Qué trámite necesitas preparar?";
 $("preguntaTexto").textContent=titulo;
 if($("paso"))$("paso").textContent="ELIGE TU TRÁMITE";
 const ops=extraerOpciones(d);
 if(!ops.length){
  toast("No se encontraron trámites disponibles.");
  return;
 }
 ops.forEach(op=>{
  const b=document.createElement("button");
  b.type="button";b.className="opcion";
  const label=typeof op==="string"?op:(op.texto||op.nombre||op.label||op.titulo||"");
  const valor=typeof op==="string"?op:(op.valor??op.value??op.id??op.caso??label);
  b.textContent=label;b.dataset.valor=valor;
  b.addEventListener("click",()=>seleccionarCaso(b.dataset.valor,label));
  $("opciones").appendChild(b);
 });
 window.scrollTo({top:0,behavior:"smooth"});
}

function mostrarPregunta(d){
 state.catalogo=false;
 mostrar("inicio",false);mostrar("servicios",false);mostrar("resultado",false);mostrar("pregunta",true);
 limpiar("opciones");
 const q=d.pregunta||d;
 state.preguntaId=q.id||d.pregunta_id||"";
 if(d.caso)state.caso=d.caso;
 const n=d.numero||d.paso||d.orden||"";
 if($("paso"))$("paso").textContent=n?`PASO ${n}`:"";
 $("preguntaTexto").textContent=q.texto||d.texto||"¿Qué necesitas?";
 const ops=q.opciones||d.opciones||[];
 const entrada=$("textoEntrada"),area=$("textoUsuario"),btn=$("continuar");
 if(ops.length){
  entrada?.classList.add("oculto");
  ops.forEach(op=>{
   const b=document.createElement("button");
   b.type="button";b.className="opcion";
   const label=typeof op==="string"?op:(op.texto||op.label||op.nombre||"");
   const valor=typeof op==="string"?op:(op.valor??op.value??label);
   b.textContent=label;b.dataset.valor=valor;
   b.addEventListener("click",()=>enviarRespuesta(b.dataset.valor));
   $("opciones").appendChild(b);
  });
 }else{
  entrada?.classList.remove("oculto");
  if(area){area.value="";area.focus()}
  if(btn)btn.disabled=false;
 }
 window.scrollTo({top:0,behavior:"smooth"});
}

async function enviarRespuesta(valor){
 valor=texto(valor||$("textoUsuario")?.value);
 if(!valor){toast("Escribe o selecciona una respuesta.");return}
 const id=state.preguntaId;
 if(!id){toast("Primero selecciona el trámite.");return}
 state.respuestas[id]=valor;
 if($("continuar"))$("continuar").disabled=true;
 try{
  const d=await api("/api/responder",{method:"POST",body:JSON.stringify({
   servicio:state.servicio,
   caso:state.caso,
   pregunta_id:id,
   texto:valor,
   respuestas:state.respuestas
  })});
  procesar(d);
 }catch(e){
  if($("continuar"))$("continuar").disabled=false;
 }
}

function escapar(v){
 const d=document.createElement("div");d.textContent=texto(v);return d.innerHTML;
}

function lista(items){
 if(!items||!items.length)return"<p class='vacio'>No se registró información en esta sección.</p>";
 return"<ul>"+items.map(x=>`<li>${escapar(typeof x==="string"?x:(x.nombre||x.texto||x.name||x.descripcion||""))}</li>`).join("")+"</ul>";
}

function perfilHtml(p){
 if(!p)return"";
 const filas=[
  ["Nombre",p.nombre],["Nacionalidad",p.nacionalidad],["Teléfono",p.telefono],
  ["Dirección",p.direccion],["Estado",p.estado],["ZIP",p.zip],["Correo",p.email]
 ];
 return`<section class="bloque"><h3>DATOS PERSONALES</h3><div class="datos">${
  filas.map(([a,b])=>`<div><strong>${a}</strong><span>${escapar(b||"PENDIENTE DE COMPLETAR")}</span></div>`).join("")
 }</div></section>`;
}

function personasHtml(items){
 if(!items?.length)return"";
 return`<section class="bloque"><h3>PERSONAS QUE DEBEN PRESENTARSE</h3>${lista(items)}</section>`;
}

function documentosHtml(d){
 if(!d)return"";
 const normal=x=>typeof x==="string"?{name:x,status:"revisar"}:x;
 const arr=Array.isArray(d)?d.map(normal):[];
 const g={tiene:[],falta:[],revisar:[]};
 arr.forEach(x=>{
  const s=String(x.status||"revisar").toLowerCase();
  (g[s]||g.revisar).push(x.name||x.nombre||x.texto||x.descripcion||"");
 });
 return`<section class="bloque"><h3>DOCUMENTOS</h3>
 <h4>🟢 LO QUE YA TIENES</h4>${lista(g.tiene)}
 <h4>🟡 LO QUE TE FALTA</h4>${lista(g.falta)}
 <h4>🔎 LO QUE DEBES CONFIRMAR</h4>${lista(g.revisar)}</section>`;
}

function bloque(t,items){
 if(items==null)return"";
 if(!Array.isArray(items))items=[items];
 if(!items.length)return"";
 return`<section class="bloque"><h3>${t}</h3>${lista(items)}</section>`;
}

function mostrarResultado(r){
 state.resultado=r;state.catalogo=false;
 mostrar("inicio",false);mostrar("servicios",false);mostrar("pregunta",false);mostrar("resultado",true);
 const nivel=String(r.nivel||"amarillo").toLowerCase();
 const clase=nivel==="verde"?"estado-verde":nivel==="rojo"?"estado-rojo":"estado-amarillo";
 const estado=r.estado_texto||(nivel==="verde"?"PARECES LISTO":nivel==="rojo"?"ATENCIÓN / NO VAYAS TODAVÍA":"TE FALTA ALGO");
 let html=`<div class="resultadoCabecera ${clase}"><strong>${escapar(estado)}</strong></div>`;
 html+=perfilHtml(r.perfil);
 html+=personasHtml(r.personas_obligatorias||r.personas||r.deben_presentarse);
 html+=`<section class="bloque"><h3>TRÁMITE</h3><p>${escapar(r.tramite||r.caso_nombre||r.nombre_tramite||state.caso||"Consulta consular")}</p></section>`;
 html+=bloque("ATENCIÓN A TU CASO",r.atencion);
 const docs=r.documentos||r.checklist;
 if(docs&&!Array.isArray(docs)){
  const arr=[
   ...(docs.tiene||[]).map(x=>({...((typeof x==="object")?x:{name:x}),status:"tiene"})),
   ...(docs.falta||[]).map(x=>({...((typeof x==="object")?x:{name:x}),status:"falta"})),
   ...(docs.revisar||[]).map(x=>({...((typeof x==="object")?x:{name:x}),status:"revisar"}))
  ];
  html+=documentosHtml(arr);
 }else if(Array.isArray(docs))html+=documentosHtml(docs);
 html+=bloque("¿QUÉ DEBES HACER?",r.prepara||r.que_debes_hacer);
 html+=bloque("CITA",r.cita);
 html+=bloque("DOCUMENTOS ORIGINALES",r.originales);
 html+=bloque("COPIAS",r.copias);
 html+=bloque("PAGO",r.pago);
 html+=bloque("ANTES DE FIRMAR O IMPRIMIR",r.revision);
 html+=bloque("VIGENCIA",r.vigencia);
 html+=bloque("ENTREGA",r.entrega);
 html+=bloque("INFORMACIÓN IMPORTANTE",r.especiales||r.importante);
 if(r.fuente)state.fuenteActual=r.fuente;
 if(r.fuente_oficial&&!state.fuenteActual)state.fuenteActual=r.fuente_oficial;
 $("respuesta").innerHTML=html;
 window.scrollTo({top:0,behavior:"smooth"});
}

async function descargarPDF(){
 if(!state.resultado){toast("Primero termina la consulta.");return}
 const btn=$("pdf");if(btn)btn.disabled=true;
 try{
  const r=await fetch("/api/pdf",{method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({caso:state.caso,respuestas:state.respuestas,resultado:state.resultado})});
  if(!r.ok){
   let d={};try{d=await r.json()}catch(e){}
   throw Error(d.detail||"No se pudo generar el PDF.");
  }
  const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf";
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){toast(e.message||"No se pudo generar el PDF.")}
 finally{if(btn)btn.disabled=false}
}

function abrirFuente(){
 const u=state.fuenteActual||state.resultado?.fuente||state.resultado?.fuente_oficial;
 if(!u){toast("No hay una fuente oficial registrada.");return}
 $("fuenteOficial").href=u;mostrar("infoOficial",true);
}

function salir(){mostrar("salida",true)}
function confirmarSalida(){reset()}

function iniciarVoz(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){toast("Tu navegador no permite entrada por voz.");return}
 if(state.escuchando)return;
 const r=new SR();
 r.lang="es-MX";r.interimResults=false;r.continuous=false;
 state.escuchando=true;
 $("voz").textContent="🎤 ESCUCHANDO...";
 r.onresult=e=>{
  const v=[...e.results].map(x=>x[0].transcript).join(" ").trim();
  $("textoUsuario").value=v;
  state.escuchando=false;$("voz").textContent="🎤 HABLAR";
  if(v)enviarRespuesta(v);
 };
 r.onerror=()=>{
  state.escuchando=false;$("voz").textContent="🎤 HABLAR";
  toast("No se pudo usar el micrófono.");
 };
 r.onend=()=>{
  state.escuchando=false;$("voz").textContent="🎤 HABLAR";
 };
 try{r.start()}catch(e){state.escuchando=false}
}

$("entrar")?.addEventListener("click",iniciar);
$("servicioCita")?.addEventListener("click",()=>seleccionarServicio("cita"));
$("servicioDocumento")?.addEventListener("click",()=>seleccionarServicio("documento"));
$("continuar")?.addEventListener("click",()=>enviarRespuesta());
$("voz")?.addEventListener("click",iniciarVoz);
$("pdf")?.addEventListener("click",descargarPDF);
$("oficial")?.addEventListener("click",abrirFuente);
$("cerrarOficial")?.addEventListener("click",()=>mostrar("infoOficial",false));
$("nuevo")?.addEventListener("click",reset);
$("salir")?.addEventListener("click",salir);
$("confirmarSalida")?.addEventListener("click",confirmarSalida);
$("cancelarSalida")?.addEventListener("click",()=>mostrar("salida",false));

$("textoUsuario")?.addEventListener("keydown",e=>{
 if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){
  e.preventDefault();enviarRespuesta();
 }
});

mostrar("inicio",true);
mostrar("servicios",false);
mostrar("pregunta",false);
mostrar("resultado",false);
mostrar("infoOficial",false);
mostrar("salida",false);
despertar();
