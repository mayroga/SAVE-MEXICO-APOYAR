const $=id=>document.getElementById(id);
const state={
 servicio:"",caso:"",pregunta_id:"",pregunta:null,respuestas:{},perfil:{},resultado:null
};

const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
const texto=v=>String(v??"").trim();

async function api(url,options={}){
 const r=await fetch(url,{headers:{"Content-Type":"application/json"},...options});
 const d=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(d.detail||"Error");
 return d;
}

function toast(msg){
 const e=$("toast");
 if(e){e.textContent=msg;e.classList.add("show");setTimeout(()=>e.classList.remove("show"),2500);}
}

function mostrar(id){
 document.querySelectorAll(".pantalla,.screen").forEach(e=>e.classList.remove("active","show"));
 const e=$(id);
 if(e)e.classList.add("active","show");
 window.scrollTo({top:0,behavior:"smooth"});
}

function limpiarEntrada(){
 if($("textoEntrada"))$("textoEntrada").value="";
 if($("textoUsuario"))$("textoUsuario").value="";
 document.querySelectorAll("input[name='q']").forEach(e=>e.checked=false);
 if($("otherInput"))$("otherInput").value="";
}

function perfilInicial(d){
 state.perfil=d?.perfil||{};
}

async function cargarEstado(){
 try{
  const d=await api("/api/estado");
  perfilInicial(d);
 }catch(e){}
}

async function cargarCatalogo(){
 try{
  const d=await api("/api/catalogo");
  const lista=d.casos||d.tramites||d.catalogo||[];
  renderCatalogo(lista);
 }catch(e){
  toast("No se pudo cargar la información.");
 }
}

function renderCatalogo(lista){
 const box=$("listaTramites");
 if(!box)return;
 box.innerHTML="";
 lista.forEach(x=>{
  const id=x.caso||x.id||x.codigo;
  const nombre=x.nombre||x.titulo||x.servicio||x.descripcion||id;
  if(!id)return;
  const b=document.createElement("button");
  b.type="button";b.className="tramite";
  b.textContent=nombre;
  b.onclick=()=>seleccionar(id,nombre);
  box.appendChild(b);
 });
}

async function seleccionar(caso,nombre=""){
 state.caso=caso;
 state.servicio=nombre;
 state.respuestas={};
 state.resultado=null;
 limpiarEntrada();
 try{
  const d=await api("/api/seleccionar-caso",{
   method:"POST",body:JSON.stringify({caso,servicio:nombre})
  });
  aplicarRespuesta(d);
 }catch(e){
  try{
   const d=await api("/api/seleccionar_caso",{
    method:"POST",body:JSON.stringify({caso,servicio:nombre})
   });
   aplicarRespuesta(d);
  }catch(err){toast(err.message||"No se pudo iniciar el trámite.");}
 }
}

function aplicarRespuesta(d){
 if(d.caso)state.caso=d.caso;
 if(d.servicio)state.servicio=d.servicio;
 if(d.perfil)state.perfil={...state.perfil,...d.perfil};
 if(d.respuestas)state.respuestas={...state.respuestas,...d.respuestas};
 if(d.resultado){state.resultado=d.resultado;renderResultado(d.resultado);return;}
 if(d.pregunta||d.pregunta_id){
  state.pregunta=d.pregunta||null;
  state.pregunta_id=d.pregunta_id||d.pregunta?.id||"";
  renderPregunta(d);
  mostrar("pantallaPreguntas");
  return;
 }
 if(d.pantalla==="resultado")renderResultado(d);
}

function renderPregunta(d){
 const q=d.pregunta||d;
 state.pregunta=q;
 state.pregunta_id=d.pregunta_id||q.id||"";
 const titulo=q.pregunta||q.texto||q.titulo||"";
 const paso=d.paso??q.paso??"";
 const total=d.total??q.total??"";
 if($("tramiteTitulo"))$("tramiteTitulo").textContent=state.servicio||"Tu trámite";
 if($("preguntaTexto"))$("preguntaTexto").textContent=titulo;
 if($("paso"))$("paso").textContent=total?`${paso} de ${total}`:paso;
 const bar=$("progresoBarra");
 if(bar){
  let p=d.progreso;
  if(p==null&&paso&&total)p=Number(paso)/Number(total)*100;
  bar.style.width=Math.max(0,Math.min(100,Number(p)||0))+"%";
 }
 const box=$("opciones");
 if(box){
  box.innerHTML="";
  const opciones=q.opciones||q.choices||[];
  opciones.forEach(o=>{
   const val=typeof o==="string"?o:(o.valor??o.value??o.texto??o.label??"");
   const lab=typeof o==="string"?o:(o.label??o.texto??o.nombre??val);
   if(!val)return;
   const wrap=document.createElement("label");
   wrap.className="opcion";
   wrap.innerHTML=`<input type="radio" name="q" value="${esc(val)}"><span>${esc(lab)}</span>`;
   const input=wrap.querySelector("input");
   input.addEventListener("change",()=>{
    const other=val==="__OTRO__"||val.toLowerCase()==="otro";
    if(other&&!$("otherInput")){
     const inp=document.createElement("input");
     inp.id="otherInput";inp.className="texto-otro";inp.placeholder="Escribe tu respuesta";
     box.appendChild(inp);
    }
   });
   box.appendChild(wrap);
  });
 }
 if($("textoEntrada")){
  $("textoEntrada").value="";
  $("textoEntrada").placeholder=q.placeholder||"Escribe tu respuesta aquí...";
 }
 limpiarEntrada();
}

function obtenerValor(){
 const q=state.pregunta||{};
 const sel=document.querySelector("input[name='q']:checked");
 let v=sel?sel.value:"";
 if((v==="__OTRO__"||v.toLowerCase()==="otro")&&$("otherInput"))v=texto($("otherInput").value);
 const txt=texto($("textoEntrada")?.value||$("textoUsuario")?.value);
 return txt||v;
}

async function continuar(){
 const q=state.pregunta||{};
 const valor=obtenerValor();
 if(q.required===true&&!valor){toast("Esta respuesta es necesaria.");return;}
 if((q.tipo==="opciones"||q.type==="opciones")&&q.permite_otro!==false){
  const sel=document.querySelector("input[name='q']:checked");
  if(sel&&(sel.value==="__OTRO__"||sel.value.toLowerCase()==="otro")&&!valor){
   toast("Escribe tu respuesta.");$("otherInput")?.focus();return;
  }
 }
 if(!state.pregunta_id){toast("No hay una pregunta activa.");return;}
 state.respuestas[state.pregunta_id]=valor;
 try{
  const d=await api("/api/continuar",{
   method:"POST",
   body:JSON.stringify({
    caso:state.caso,
    servicio:state.servicio,
    pregunta_id:state.pregunta_id,
    respuesta:valor,
    texto:valor,
    respuestas:state.respuestas,
    perfil:state.perfil
   })
  });
  if(d.perfil)state.perfil={...state.perfil,...d.perfil};
  if(d.respuestas)state.respuestas={...state.respuestas,...d.respuestas};
  aplicarRespuesta(d);
 }catch(e){toast(e.message||"No se pudo continuar.");}
}

async function interpretar(){
 const el=$("textoUsuario")||$("textoEntrada");
 const valor=texto(el?.value);
 if(!valor){toast("Escribe o habla primero.");return;}
 if(state.pregunta_id){await continuar();return;}
 try{
  const d=await api("/api/interpretar",{
   method:"POST",
   body:JSON.stringify({texto:valor,caso:state.caso,servicio:state.servicio,respuestas:state.respuestas,perfil:state.perfil})
  });
  aplicarRespuesta(d);
 }catch(e){toast(e.message||"No se pudo interpretar.");}
}

function renderResultado(r){
 state.resultado=r||{};
 mostrar("pantallaResultado");
 const map={
  datos:"resultadoDatos",personas:"resultadoPersonas",requisitos:"resultadoRequisitos",
  originales:"resultadoOriginales",copias:"resultadoCopias",faltantes:"resultadoFaltantes",
  confirmar:"resultadoConfirmar",pago:"resultadoPago",cita:"resultadoCita",
  vigencia:"resultadoVigencia",entrega:"resultadoEntrega",especial:"resultadoEspecial",
  acciones:"resultadoAcciones",fuentes:"resultadoFuentes",contacto:"resultadoContacto"
 };
 Object.entries(map).forEach(([k,id])=>{
  const e=$(id);if(!e)return;
  let v=r[k];
  if(v==null)v=r[k==="faltantes"?"missing":k];
  if(Array.isArray(v))e.innerHTML=v.length?`<ul>${v.map(x=>`<li>${esc(typeof x==="string"?x:x.texto||x.nombre||"")}</li>`).join("")}</ul>`:"<p>No hay información.</p>";
  else if(typeof v==="object"&&v)e.innerHTML=Object.entries(v).map(([a,b])=>`<p><strong>${esc(a)}:</strong> ${esc(b)}</p>`).join("");
  else e.innerHTML=esc(v||"");
 });
 const oficial=r.fuente||r.url_oficial||r.fuentes?.[0]?.url||"";
 const b=$("oficial");
 if(b&&oficial){b.href=oficial;b.target="_blank";b.rel="noopener";}
}

async function descargarPDF(){
 try{
  const r=await fetch("/api/pdf",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({caso:state.caso,respuestas:state.respuestas,perfil:state.perfil,resultado:state.resultado})
  });
  if(!r.ok)throw new Error("No se pudo generar el PDF.");
  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download="MEXICANO_APOYA_MEXICANO.pdf";
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){toast(e.message);}
}

function escuchar(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){toast("Tu navegador no permite entrada por voz.");return;}
 const rec=new SR();
 rec.lang="es-MX";rec.interimResults=false;rec.continuous=false;
 rec.onstart=()=>{$("voz")?.classList.add("activo");};
 rec.onend=()=>{$("voz")?.classList.remove("activo");};
 rec.onerror=()=>toast("No se pudo usar el micrófono.");
 rec.onresult=e=>{
  const t=e.results?.[0]?.[0]?.transcript||"";
  const el=$("textoEntrada")||$("textoUsuario");
  if(el){el.value=t;el.dispatchEvent(new Event("input"));}
 };
 rec.start();
}

function salir(){
 state.servicio="";state.caso="";state.pregunta_id="";state.pregunta=null;
 state.respuestas={};state.resultado=null;
 limpiarEntrada();
 mostrar("pantallaInicio");
}

function bind(){
 $("inicio")?.addEventListener("click",()=>mostrar("pantallaTramites"));
 $("comenzar")?.addEventListener("click",()=>mostrar("pantallaTramites"));
 $("continuar")?.addEventListener("click",continuar);
 $("interpretar")?.addEventListener("click",interpretar);
 $("voz")?.addEventListener("click",escuchar);
 $("pdf")?.addEventListener("click",descargarPDF);
 $("generarPDF")?.addEventListener("click",descargarPDF);
 $("salir")?.addEventListener("click",salir);
 $("nuevo")?.addEventListener("click",salir);
 $("volver")?.addEventListener("click",()=>mostrar("pantallaTramites"));
 $("cerrarModal")?.addEventListener("click",()=>$("modal")?.classList.remove("show"));
 $("oficial")?.addEventListener("click",()=>{});
 $("textoEntrada")?.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();continuar();}
 });
}

document.addEventListener("DOMContentLoaded",async()=>{
 bind();
 mostrar("pantallaInicio");
 await cargarEstado();
 await cargarCatalogo();
});
