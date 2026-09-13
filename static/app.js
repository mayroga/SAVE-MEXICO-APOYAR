let perfil={},casoActual="",respuestas={},resultadoFinal=null;
let idTemporizador=null,contadorRevisiones=0,peticionActiva=false;
let reconocimientoActual=null;
const $=id=>document.getElementById(id);

function iniciarRelojInactividad(){
 clearTimeout(idTemporizador);
 idTemporizador=setTimeout(()=>{
  alert("Por tu seguridad, tu sesión de 10 minutos ha terminado. Vamos a comenzar de nuevo.");
  comenzarDeNuevoLimpio();
 },600000);
}
document.addEventListener("click",iniciarRelojInactividad);
document.addEventListener("keydown",iniciarRelojInactividad);

async function api(url,opciones={},timeout=15000){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),timeout);
 try{
  const r=await fetch(url,{...opciones,signal:ctrl.signal,credentials:"same-origin"});
  const tipo=r.headers.get("content-type")||"";
  const data=tipo.includes("application/json")?await r.json():await r.text();
  if(!r.ok){
   let msg=data&&data.detail?data.detail:"El servidor rechazó la solicitud.";
   if(Array.isArray(msg))msg=msg.map(x=>x.msg||JSON.stringify(x)).join(", ");
   throw new Error(msg);
  }
  return data;
 }catch(e){
  if(e.name==="AbortError")throw new Error("La solicitud tardó demasiado. Intenta nuevamente.");
  throw e;
 }finally{
  clearTimeout(timer);
 }
}

function validarCheck(){
 const chk=$("check-legal");
 ["btn-plan-diario","btn-plan-mensual"].forEach(id=>{
  const b=$(id);
  if(b)b.disabled=!chk?.checked;
 });
}

function calcularEdadAutomaticamente(valor) {
    if (!valor) return;
    
    // Limpiar y estandarizar separadores (soporta / y -)
    let limpio = valor.trim().replace(/[-\/]/g, ' ');
    let partes = limpio.split(/\s+/);
    
    if (partes.length < 3) return;

    let p1 = parseInt(partes[0], 10);
    let p2 = parseInt(partes[1], 10);
    let p3 = parseInt(partes[2], 10);

    let y, mes, dia;

    // Detectar si el año viene al principio (YYYY-MM-DD) o al final (DD-MM-YYYY)
    if (p1 > 1900) {
        y = p1; mes = p2; dia = p3;
    } else {
        dia = p1; mes = p2; y = p3;
    }

    if (isNaN(y) || isNaN(mes) || isNaN(dia)) return;
    if (y < 1900 || y > new Date().getFullYear() || mes < 1 || mes > 12 || dia < 1 || dia > 31) return;

    const hoy = new Date();
    const nacimiento = new Date(y, mes - 1, dia);

    // Validar que la fecha sea real (ej. que no sea 31 de febrero)
    if (nacimiento.getFullYear() !== y || nacimiento.getMonth() !== mes - 1 || nacimiento.getDate() !== dia) return;

    let edad = hoy.getFullYear() - y;
    const m = hoy.getMonth() - (mes - 1);
    if (m < 0 || (m === 0 && hoy.getDate() < dia)) {
        edad--;
    }

    if (edad >= 0 && edad < 120) {
        const inp = $("input-edad");
        if (inp) inp.value = edad;
        perfil.edad = String(edad);
    }
}
function leerEnVozAlta(texto){
 if(!("speechSynthesis"in window))return;
 speechSynthesis.cancel();
 const u=new SpeechSynthesisUtterance(String(texto||""));
 u.lang="es-MX";u.rate=.95;speechSynthesis.speak(u);
}

function activarMicrofono(id){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){
  alert("El dictado por voz no está soportado en este dispositivo.");
  return;
 }
 if(reconocimientoActual)try{reconocimientoActual.stop()}catch(_){}
 const r=new SR();
 reconocimientoActual=r;
 r.lang="es-MX";r.interimResults=false;r.maxAlternatives=1;
 const boton=$("btn-voz-"+id.split("-")[1]);
 r.onstart=()=>{
  if(boton)boton.innerText="🛑 Escuchando...";
 };
 r.onresult=e=>{
  const t=e.results?.[0]?.[0]?.transcript||"";
  const el=$(id);
  if(el)el.value=t.replace(/\.$/,"");
  if(id==="input-fecha")calcularEdadAutomaticamente(t);
 };
 r.onerror=()=>{};
 r.onend=()=>{
  if(boton){
   boton.innerText=id==="input-nombre"?"🎙️ Dictar Nombre":
    id==="input-fecha"?"🎙️ Dictar Fecha":"🎙️ Dictar Dirección";
  }
  reconocimientoActual=null;
 };
 try{r.start()}catch(_){}
}

function iniciarMecanismoRevision(){
    const nombre = $("input-nombre").value.trim();
    const fecha = $("input-fecha").value.trim();
    const edad = $("input-edad").value.trim();
    const origen = $("input-origen").value;
    const direccion = $("input-direccion").value.trim();
    const tel = $("input-tel").value.trim();
    const edo = $("input-estado").value;

    if(!nombre || !fecha || !edad || !direccion){
        alert("Por favor rellena todos tus datos obligatorios.");
        return;
    }

    // Validación inteligente de dirección vs Estado seleccionado en USA
    const dirLower = direccion.toLowerCase();
    const edoLower = edo.toLowerCase();
    
    // Si el estado seleccionado es específico y la dirección no contiene indicios del estado o código postal válido
    if(edo !== "Otro" && !dirLower.includes(edoLower)) {
        const confirmarEstado = confirm(`⚠️ Nota de validación:\nSeleccionaste el estado de "${edo}", pero tu dirección escrita no parece incluirlo claramente.\n\n¿Deseas continuar de todas formas o corregirlo?`);
        if(!confirmarEstado) return;
    }

    perfil = {
        nombre_completo: nombre,
        fecha_nacimiento: fecha,
        edad,
        origen_mexico: origen,
        direccion_usa: direccion,
        telefono: tel,
        estado: edo,
        nacionalidad: "mexicana"
    };

    try{
        localStorage.setItem("perfil_retenido", JSON.stringify(perfil));
    }catch(_){}

    const resumen = $("resumen-visual-datos");
    if(resumen){
        resumen.innerHTML = "";
        [
            ["Tu Nombre", nombre],
            ["Tu Fecha de Nacimiento", `${fecha} (${edad} años)`],
            ["Tu Dirección en USA", direccion],
            ["Tu Teléfono", tel || "No indicado"],
            ["Tu Estado Seleccionado", edo]
        ].forEach(x => {
            const p = document.createElement("p"), b = document.createElement("strong");
            b.textContent = x[0] + ": ";
            p.append(b, document.createTextNode(x[1]));
            resumen.appendChild(p);
        });
    }

    contadorRevisiones = 0;
    actualizarAlertaYVozRevision();
    irAPaso("paso-triple-revision");
}

function actualizarAlertaYVozRevision(){
 const pantalla=[
  "🚨 REVISIÓN 1 DE 3: Mira bien tu nombre arriba en la pantalla. ¿Está escrito exactamente igualito que en tus papeles oficiales? Si tiene una sola letra mal, en el consulado puede haber problemas.",
  "🚨 REVISIÓN 2 DE 3: Revisa el Estado de Estados Unidos que seleccionaste. Debe ser el estado donde vives actualmente.",
  "🚨 REVISIÓN 3 DE 3: Última revisión. Confirma que la información que pusiste es verdadera y que llevarás tus papeles originales."
 ];
 const voz=[
  "Primera revisión obligatoria. Por favor, lee tu nombre en la pantalla. Debe estar escrito igualito que en tus papeles oficiales. Da un clic para confirmar.",
  "Segunda revisión obligatoria. Mira el estado de residencia que seleccionaste. Debe ser donde vives actualmente. Da el segundo clic.",
  "Tercera revisión obligatoria. Confirma que la información que pusiste es verdadera y que llevarás tus papeles originales. Da el último clic."
 ];
 $("texto-alerta-revision").innerText=pantalla[contadorRevisiones];
 leerEnVozAlta(voz[contadorRevisiones]);
 $("btn-confirmar-revision").innerText=`SÍ, YA REVISÉ (${contadorRevisiones+1}/3)`;
}

function avanzarClicRevision(){
 if(peticionActiva)return;
 contadorRevisiones++;
 if(contadorRevisiones>=3){
  if("speechSynthesis"in window)speechSynthesis.cancel();
  cargarCatalogo();
 }else actualizarAlertaYVozRevision();
}

async function cargarCatalogo(){
 if(peticionActiva)return;
 peticionActiva=true;
 try{
  const datos=await api("/api/catalogo");
  const lista=$("lista-tramites");
  if(!lista)throw Error("No existe el catálogo.");
  lista.innerHTML="";
  (datos||[]).forEach(t=>{
   const btn=document.createElement("button");
   btn.className="option-btn";
   const strong=document.createElement("strong"),span=document.createElement("span");
   strong.textContent=t.nombre;
   span.textContent=t.descripcion;
   btn.append(strong,span);
   btn.onclick=()=>iniciarTramite(t.caso);
   lista.appendChild(btn);
  });
  irAPaso("paso-tramites");
 }catch(e){
  alert("No se pudo cargar el catálogo. "+e.message);
 }finally{
  peticionActiva=false;
 }
}

async function iniciarTramite(caso){
 if(peticionActiva)return;
 casoActual=caso;
 respuestas={};
 peticionActiva=true;
 try{
  const data=await api("/api/seleccionar-caso",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({caso,perfil,respuestas})
  });

  /*
   * IMPORTANTE:
   * liberar el bloqueo ANTES de procesar el paso.
   * En PASAPORTE, procesarPaso puede necesitar enviar
   * automáticamente la respuesta de vigencia_pasaporte.
   */
  peticionActiva=false;
  procesarPaso(data);
 }catch(e){
  peticionActiva=false;
  alert("Error al iniciar el trámite. "+e.message);
 }
}

async function enviarRespuesta(idPregunta,valor){
 if(peticionActiva)return;

 peticionActiva=true;
 respuestas[idPregunta]=valor;

 try{
  const data=await api("/api/continuar",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({
    caso:casoActual,
    pregunta_id:idPregunta,
    respuesta:valor,
    respuestas,
    perfil
   })
  });

  /*
   * Liberamos antes de procesar el siguiente paso.
   * Esto evita el bloqueo de respuestas encadenadas.
   */
  peticionActiva=false;
  procesarPaso(data);
 }catch(e){
  delete respuestas[idPregunta];
  peticionActiva=false;
  alert("Error al procesar la respuesta. "+e.message);
 }
}

function procesarPaso(data){
 if(!data||typeof data!=="object"){
  alert("El servidor devolvió una respuesta inválida.");
  return;
 }

 if(data.pregunta){
  /*
   * PASAPORTE:
   * La versión anterior intentaba llamar enviarRespuesta()
   * mientras peticionActiva seguía en true.
   *
   * Ahora iniciarTramite/enviarRespuesta liberan el bloqueo
   * antes de llegar aquí, por lo que esta transición sí avanza.
   */
  if(data.pregunta.id==="vigencia_pasaporte"&&perfil.edad){
   const edad=parseInt(perfil.edad,10);
   let v="";
   if(edad<3)v="1 año";
   else if(edad<18)v="6 años";
   else v="10 años";

   if(!respuestas[data.pregunta.id]){
    enviarRespuesta(data.pregunta.id,v);
    return;
   }
  }

  irAPaso("paso-preguntas");
  $("pregunta-titulo").innerText=data.servicio||"Revisión de Papeles";
  $("pregunta-texto").innerText=data.pregunta.pregunta||"";
  leerEnVozAlta(data.pregunta.pregunta);

  const cont=$("contenedor-opciones");
  if(!cont)return;
  cont.innerHTML="";

  (data.pregunta.opciones||[]).forEach(o=>{
   const lbl=document.createElement("label");
   const radio=document.createElement("input");
   const span=document.createElement("span");

   lbl.className="radio-label";
   radio.type="radio";
   radio.name="r_opt";
   radio.value=o;
   span.textContent=o;

   lbl.append(radio,span);

   radio.addEventListener("change",()=>{
    if(!radio.checked||peticionActiva)return;
    cont.querySelectorAll("input").forEach(x=>x.disabled=true);
    enviarRespuesta(data.pregunta.id,o);
   });

   cont.appendChild(lbl);
  });

 }else if(data.resultado){
  if("speechSynthesis"in window)speechSynthesis.cancel();
  mostrarResultado(data.resultado);
 }else{
  alert("La respuesta del servidor está incompleta.");
 }
}

function mostrarResultado(r){
 resultadoFinal=r;
 irAPaso("paso-resultado");

 const caja=$("res-caja-estado");
 if(caja){
  caja.className="box-info "+(r.estado==="LISTO PARA TU CITA"?"success":"danger");
  caja.innerHTML="";
  const b=document.createElement("strong");
  b.textContent=`ESTATUS: ${r.estado}`;
  caja.append(
   b,
   document.createElement("br"),
   document.createTextNode(r.mensaje_estado||"")
  );
 }

 const set=(id,v)=>{
  const el=$(id);
  if(el)el.innerText=v||"";
 };

 set("res-consulado",r.consulado_nombre);
 set("res-direccion","📍 "+(r.consulado_direccion||""));
 set("res-telefono","📞 Tel central: "+(r.consulado_telefono||""));
 set("res-pago",r.pago_estimado);
 set("res-cita",r.cita_estatus);

 const cita=$("res-cita");
 if(cita)cita.style.color=(r.cita_estatus||"").includes("PENDIENTE")
  ?"var(--danger)":"var(--accent)";

 inyectarLista("res-requisitos",r.requisitos_oficiales);

 const sec=$("seccion-faltantes");
 if(sec)sec.style.display=(r.faltantes||[]).length?"block":"none";

 inyectarLista("res-faltantes",r.faltantes);
 inyectarLista("res-acciones",r.acciones_recomendadas);

 const btnWeb=document.querySelector(".btn-link");
 if(btnWeb&&r.url_consulado){
  btnWeb.onclick=()=>{
   window.open(r.url_consulado,"_blank","noopener,noreferrer");
  };
 }
}

function inyectarLista(id,arreglo){
 const el=$(id);
 if(!el)return;
 el.innerHTML="";
 (arreglo||[]).forEach(x=>{
  const li=document.createElement("li");
  li.textContent=x;
  el.appendChild(li);
 });
}

async function verVistaPrevia(){
 if(!resultadoFinal||peticionActiva)return;
 peticionActiva=true;
 try{
  const res=await fetch("/api/pdf-preview",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   credentials:"same-origin",
   body:JSON.stringify(resultadoFinal)
  });
  if(!res.ok)throw Error((await res.text())||"No se pudo generar la vista previa.");

  const blob=await res.blob();
  const url=URL.createObjectURL(blob);
  const iframe=$("pdf-frame"),modal=$("modal-pdf");

  if(iframe)iframe.src=url;
  if(modal)modal.classList.add("active");
 }catch(e){
  alert("No se pudo generar la vista previa. "+e.message);
 }finally{
  peticionActiva=false;
 }
}

function cerrarVistaPrevia(){
 const iframe=$("pdf-frame"),modal=$("modal-pdf");
 if(iframe){
  const u=iframe.src;
  iframe.src="";
  if(u.startsWith("blob:"))URL.revokeObjectURL(u);
 }
 if(modal)modal.classList.remove("active");
}

async function descargarPDF(){
 if(!resultadoFinal||peticionActiva)return;
 peticionActiva=true;
 try{
  const res=await fetch("/api/pdf",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   credentials:"same-origin",
   body:JSON.stringify(resultadoFinal)
  });
  if(!res.ok)throw Error((await res.text())||"No se pudo guardar el PDF.");

  const blob=await res.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");

  a.href=url;
  a.download=`Hoja_de_Ruta_${(casoActual||"consular").toUpperCase()}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){
  alert("No se pudo guardar tu Hoja de Ruta. "+e.message);
 }finally{
  peticionActiva=false;
 }
}

function comenzarDeNuevoLimpio(){
 casoActual="";
 respuestas={};
 resultadoFinal=null;
 contadorRevisiones=0;

 try{
  const d=JSON.parse(localStorage.getItem("perfil_retenido")||"null");
  if(d){
   perfil=d;
   const set=(id,v)=>{
    const el=$(id);
    if(el)el.value=v||"";
   };
   set("input-nombre",d.nombre_completo);
   set("input-fecha",d.fecha_nacimiento);
   set("input-edad",d.edad);
   set("input-direccion",d.direccion_usa);
   set("input-tel",d.telefono);
   set("input-origen",d.origen_mexico||"Michoacán");
   set("input-estado",d.estado||"Otro");
  }
 }catch(_){
  perfil={};
 }

 const chk=$("check-legal");
 if(chk)chk.checked=false;
 validarCheck();
 irAPaso("paso-legal");
}

function irAPaso(id){
 document.querySelectorAll(".step").forEach(s=>s.classList.remove("active"));
 const target=$(id);
 if(target)target.classList.add("active");
 window.scrollTo({top:0,behavior:"auto"});
}

async function bypassDesarrollador(user,pass){
 if(!user||!pass){
  alert("Por favor escribe tu usuario y contraseña.");
  return;
 }

 try{
  const data=await api("/api/login-developer",{
   method:"POST",
   headers:{"Content-Type":"application/json"},
   body:JSON.stringify({username:user,password:pass})
  });

  if(data.ok){
   try{localStorage.setItem("modo_desarrollador","activo")}catch(_){}
   const muro=$("muro-pago-stripe"),inicio=$("btn-comenzar");
   if(muro)muro.style.display="none";
   if(inicio)inicio.style.display="block";
   alert("¡Acceso de desarrollador aprobado!");
   irAPaso("paso-datos");
  }
 }catch(e){
  alert("No fue posible validar el acceso. "+e.message);
 }
}

async function solicitarAccesoStripe(plan){
 if(peticionActiva)return;

 peticionActiva=true;
 const btns=["btn-plan-diario","btn-plan-mensual"].map($).filter(Boolean);
 btns.forEach(b=>b.disabled=true);

 try{
  const data=await api(
   `/api/checkout?plan=${encodeURIComponent(plan)}`,
   {method:"POST"},
   20000
  );

  if(data.url)window.location.assign(data.url);
  else throw Error("Stripe no devolvió un enlace de pago.");
 }catch(e){
  alert("No se pudo abrir Stripe. "+e.message);
  validarCheck();
  peticionActiva=false;
 }
}

async function comprobarAcceso(){
 try{
  const data=await api("/api/access-status");
  const muro=$("muro-pago-stripe"),inicio=$("btn-comenzar");

  if(data.activo){
   if(muro)muro.style.display="none";
   if(inicio)inicio.style.display="block";
  }else{
   if(muro)muro.style.display="block";
   if(inicio)inicio.style.display="none";
  }
 }catch(_){}
}

function abortarCuestionario(){
 cargarCatalogo();
}

function reiniciarTodo(){
 comenzarDeNuevoLimpio();
}

document.addEventListener("DOMContentLoaded",()=>{
 const fecha=$("input-fecha");

 if(fecha){
  fecha.addEventListener("blur",()=>{
   calcularEdadAutomaticamente(fecha.value);
  });
 }

 validarCheck();
 comprobarAcceso();
 iniciarRelojInactividad();
});
