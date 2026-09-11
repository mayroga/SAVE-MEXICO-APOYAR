const $=id=>document.getElementById(id);
const state={servicio:"",caso:"",preguntaId:"",respuestas:{},escuchando:false,fuenteActual:"",resultado:null};

async function api(url,opt={}){
 try{
  const r=await fetch(url,{headers:{"Content-Type":"application/json"},...opt});
  const d=await r.json();
  if(!r.ok)throw Error(d.detail||"Error");
  return d;
 }catch(e){toast(e.message||"No se pudo completar la operación.");throw e}
}

function toast(t){
 let x=document.querySelector(".toast");
 if(!x){x=document.createElement("div");x.className="toast";document.body.appendChild(x)}
 x.textContent=t;x.classList.add("show");clearTimeout(x._t);x._t=setTimeout(()=>x.classList.remove("show"),3000);
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

async function despertar(){
 try{await api("/api/estado")}catch(e){}
}

function reset(){
 state.servicio="";state.caso="";state.preguntaId="";state.respuestas={};state.escuchando=false;state.fuenteActual="";state.resultado=null;
 $("textoUsuario").value="";
 mostrar("inicio",true);mostrar("servicios",false);mostrar("pregunta",false);mostrar("resultado",false);
 mostrar("infoOficial",false);mostrar("salida",false);
 limpiar("opciones");$("preguntaTexto").textContent="¿Qué necesitas?";
 if($("paso"))$("paso").textContent="";
}

function iniciar(){
 mostrar("inicio",false);mostrar("servicios",true);
 window.scrollTo({top:0,behavior:"smooth"});
}

async function seleccionarServicio(servicio){
 state.servicio=servicio;
 try{
  const d=await api("/api/inicio/"+encodeURIComponent(servicio));
  state.caso=d.caso||"";
  state.respuestas=d.respuestas||{};
  procesar(d);
 }catch(e){}
}

function procesar(d){
 if(d.respuestas)state.respuestas={...state.respuestas,...d.respuestas};
 if(d.caso)state.caso=d.caso;
 if(d.pregunta_id)state.preguntaId=d.pregunta_id;
 if(d.fuente)state.fuenteActual=d.fuente;
 if(d.tipo==="resuelto"||d.estado_texto||d.resultado){
  mostrarResultado(d.resultado||d);
  return;
 }
 mostrarPregunta(d);
}

function mostrarPregunta(d){
 mostrar("servicios",false);mostrar("resultado",false);mostrar("pregunta",true);
 limpiar("opciones");
 const q=d.pregunta||d;
 state.preguntaId=q.id||d.pregunta_id||"";
 const n=d.numero||d.paso||"";
 if($("paso"))$("paso").textContent=n?`PASO ${n}`:"";
 $("preguntaTexto").textContent=q.texto||d.texto||"¿Qué necesitas?";
 const ops=q.opciones||d.opciones||[];
 const entrada=$("textoEntrada");
 const area=$("textoUsuario");
 const btn=$("continuar");
 if(ops.length){
  entrada?.classList.add("oculto");
  ops.forEach((op,i)=>{
   const b=document.createElement("button");
   b.type="button";b.className="opcion";b.textContent=typeof op==="string"?op:(op.texto||op.label||"");
   b.dataset.valor=typeof op==="string"?op:(op.valor??op.value??op.texto??"");
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
 if(id)state.respuestas[id]=valor;
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
 if(!items||!items.length)return "<p class='vacio'>No se registró información en esta sección.</p>";
 return "<ul>"+items.map(x=>`<li>${escapar(typeof x==="string"?x:(x.nombre||x.texto||x.name||""))}</li>`).join("")+"</ul>";
}

function perfilHtml(p){
 if(!p)return"";
 const filas=[
  ["Nombre",p.nombre],["Nacionalidad",p.nacionalidad],["Teléfono",p.telefono],
  ["Dirección",p.direccion],["Estado",p.estado],["ZIP",p.zip],["Correo",p.email]
 ];
 return `<section class="bloque"><h3>DATOS DE LA PERSONA</h3><div class="datos">${filas.map(([a,b])=>`<div><strong>${a}</strong><span>${escapar(b||"PENDIENTE DE COMPLETAR")}</span></div>`).join("")}</div></section>`;
}

function documentosHtml(d){
 if(!d)return"";
 const normal=x=>typeof x==="string"?{name:x,status:"revisar"}:x;
 const arr=(d||[]).map(normal);
 const grupos={tiene:[],falta:[],revisar:[]};
 arr.forEach(x=>{
  const s=x.status||"revisar";
  (grupos[s]||grupos.revisar).push(x.name||x.nombre||x.texto||"");
 });
 return `<section class="bloque"><h3>DOCUMENTOS</h3>
 <h4>🟢 LO QUE YA TIENES</h4>${lista(grupos.tiene)}
 <h4>🟡 LO QUE TE FALTA</h4>${lista(grupos.falta)}
 <h4>🔎 LO QUE DEBES CONFIRMAR</h4>${lista(grupos.revisar)}</section>`;
}

function mostrarResultado(r){
 state.resultado=r;mostrar("pregunta",false);mostrar("servicios",false);mostrar("resultado",true);
 const nivel=(r.nivel||"amarillo").toLowerCase();
 const clase=nivel==="verde"?"estado-verde":nivel==="rojo"?"estado-rojo":"estado-amarillo";
 const estado=r.estado_texto||"TE FALTA ALGO";
 const docs=r.documentos||r.checklist||{};
 let html=`<div class="resultadoCabecera ${clase}"><strong>${escapar(estado)}</strong></div>`;
 html+=perfilHtml(r.perfil);
 html+=`<section class="bloque"><h3>TRÁMITE</h3><p>${escapar(r.tramite||r.caso_nombre||r.nombre_tramite||"Consulta consular")}</p></section>`;
 if(r.atencion)html+=`<section class="bloque"><h3>ATENCIÓN A TU CASO</h3>${lista(Array.isArray(r.atencion)?r.atencion:[r.atencion])}</section>`;
 if(docs&& !Array.isArray(docs))html+=documentosHtml([...(docs.tiene||[]).map(x=>({...x,status:"tiene"})),...(docs.falta||[]).map(x=>({...x,status:"falta"})),...(docs.revisar||[]).map(x=>({...x,status:"revisar"}))]);
 else if(Array.isArray(docs))html+=documentosHtml(docs);
 if(r.especiales?.length)html+=`<section class="bloque"><h3>INFORMACIÓN IMPORTANTE</h3>${lista(r.especiales)}</section>`;
 if(r.prepara?.length)html+=`<section class="bloque"><h3>¿QUÉ DEBES HACER?</h3>${lista(r.prepara)}</section>`;
 if(r.cita?.length)html+=`<section class="bloque"><h3>CITA</h3>${lista(r.cita)}</section>`;
 if(r.route?.length)html+=`<section class="bloque"><h3>RUTA</h3>${lista(r.route)}</section>`;
 if(r.originales?.length)html+=`<section class="bloque"><h3>DOCUMENTOS ORIGINALES</h3>${lista(r.originales)}</section>`;
 if(r.copias?.length)html+=`<section class="bloque"><h3>COPIAS</h3>${lista(r.copias)}</section>`;
 if(r.pago?.length)html+=`<section class="bloque"><h3>PAGO</h3>${lista(r.pago)}</section>`;
 if(r.vigencia?.length)html+=`<section class="bloque"><h3>VIGENCIA</h3>${lista(r.vigencia)}</section>`;
 if(r.entrega?.length)html+=`<section class="bloque"><h3>ENTREGA</h3>${lista(r.entrega)}</section>`;
 if(r.revision?.length)html+=`<section class="bloque"><h3>ANTES DE FIRMAR O IMPRIMIR</h3>${lista(r.revision)}</section>`;
 if(r.importante?.length)html+=`<section class="bloque"><h3>INFORMACIÓN IMPORTANTE</h3>${lista(r.importante)}</section>`;
 if(r.fuente)state.fuenteActual=r.fuente;
 $("respuesta").innerHTML=html;
 window.scrollTo({top:0,behavior:"smooth"});
}

async function descargarPDF(){
 if(!state.resultado){toast("Primero termina la consulta.");return}
 const btn=$("pdf");if(btn)btn.disabled=true;
 try{
  const r=await fetch("/api/pdf",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
   servicio:state.servicio,caso:state.caso,respuestas:state.respuestas,resultado:state.resultado
  })});
  if(!r.ok)throw Error("No se pudo generar el PDF.");
  const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf";
  document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){toast(e.message)}
 finally{if(btn)btn.disabled=false}
}

function abrirFuente(){
 const u=state.fuenteActual||state.resultado?.fuente;
 if(!u){toast("No hay una fuente oficial registrada.");return}
 $("fuenteOficial").href=u;mostrar("infoOficial",true);
}

function salir(){
 mostrar("salida",true);
}

function confirmarSalida(){
 reset();
}

function iniciarVoz(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){toast("Tu navegador no permite entrada por voz.");return}
 if(state.escuchando)return;
 const r=new SR();r.lang="es-MX";r.interimResults=false;r.continuous=false;state.escuchando=true;
 $("voz").textContent="🎤 ESCUCHANDO...";
 r.onresult=e=>{
  const v=[...e.results].map(x=>x[0].transcript).join(" ").trim();
  $("textoUsuario").value=v;
  state.escuchando=false;$("voz").textContent="🎤 HABLAR";
  if(v)enviarRespuesta(v);
 };
 r.onerror=()=>{state.escuchando=false;$("voz").textContent="🎤 HABLAR";toast("No se pudo usar el micrófono.")};
 r.onend=()=>{state.escuchando=false;$("voz").textContent="🎤 HABLAR"};
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
 if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){e.preventDefault();enviarRespuesta()}
});

mostrar("servicios",false);mostrar("pregunta",false);mostrar("resultado",false);mostrar("infoOficial",false);mostrar("salida",false);
despertar();
