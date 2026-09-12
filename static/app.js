// static/app.js
let perfil = {};
let casoActual = "";
let respuestas = {};
let resultadoFinal = null;
let idTemporizador = null;
let contadorRevisiones = 0; // Control del árbol de triple clic obligatorio

// 1. RELEJO DE INACTIVIDAD DE 10 MINUTOS
function iniciarRelojInactividad() {
    clearTimeout(idTemporizador);
    idTemporizador = setTimeout(() => {
        alert("Por tu seguridad, tu sesión de 10 minutos ha terminado. Vamos a comenzar de nuevo.");
        comenzarDeNuevoLimpio();
    }, 600000);
}

document.addEventListener("click", iniciarRelojInactividad);
document.addEventListener("keydown", iniciarRelojInactividad);

function validarCheck() {
    const chk = document.getElementById('check-legal');
    document.getElementById('btn-comenzar').disabled = !chk.checked;
}

function comenzarDeNuevoLimpio() {
    casoActual = "";
    respuestas = {};
    resultadoFinal = null;
    contadorRevisiones = 0;
    document.getElementById('input-nombre').value = "";
    document.getElementById('input-tel').value = "";
    document.getElementById('input-fecha').value = "";
    document.getElementById('input-edad').value = "";
    document.getElementById('input-direccion').value = "";
    document.getElementById('input-estado').value = "California";
    document.getElementById('check-legal').checked = false;
    document.getElementById('btn-comenzar').disabled = true;
    irAPaso('paso-legal');
}

function irAPaso(id) {
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    window.scrollTo(0, 0);
}

// 2. MOTOR DE ACCESIBILIDAD AUDITIVA (SÍNTESIS Y DICTADO)
function leerEnVozAlta(textoAIngresar) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Cancelar cualquier audio previo activo
        let locucion = new SpeechSynthesisUtterance(textoAIngresar);
        locucion.lang = 'es-MX'; // Acento nativo mexicano para mayor claridad comunitaria
        locucion.rate = 0.95;    // Velocidad pausada y amigable para evitar confusión
        locucion.pitch = 1.0;
        window.speechSynthesis.speak(locucion);
    }
}

function activarMicrofono(idElementoInput) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("El dictado por voz no está soportado en este teléfono o navegador. Por favor escribe con el teclado.");
        return;
    }
    
    let reconocimiento = new SpeechRecognition();
    reconocimiento.lang = 'es-MX';
    reconocimiento.interimResults = false;
    reconocimiento.maxAlternatives = 1;
    
    const botonVoz = document.getElementById(`btn-voz-${idElementoInput.split('-')[1]}`);
    
    reconocimiento.onstart = () => {
        if (botonVoz) botonVoz.innerText = "🛑 Escuchando tu voz...";
    };
    
    reconocimiento.onresult = (event) => {
        let resultadoTexto = event.results[0][0].transcript;
        // Limpiar puntos finales molestos del dictado automático
        if (resultadoTexto.endsWith('.')) {
            resultadoTexto = resultadoTexto.slice(0, -1);
        }
        document.getElementById(idElementoInput).value = resultadoTexto;
    };
    
    reconocimiento.onerror = () => {
        alert("No se pudo entender bien el audio. Por favor intenta de nuevo o escribe con el teclado.");
    };
    
    reconocimiento.onend = () => {
        if (botonVoz) {
            if (idElementoInput === 'input-nombre') botonVoz.innerText = "🎙️ Dictar Nombre";
            if (idElementoInput === 'input-fecha') botonVoz.innerText = "🎙️ Dictar Fecha";
            if (idElementoInput === 'input-direccion') botonVoz.innerText = "🎙️ Dictar Dirección";
        }
    };
    
    reconocimiento.start();
}

// 3. MECANISMO INTERMEDIO OBLIGATORIO DE TRIPLE REVISIÓN VISUAL Y AUDITIVA
function iniciarMecanismoRevision() {
    const nombre = document.getElementById('input-nombre').value.trim();
    const fecha = document.getElementById('input-fecha').value.trim();
    const edad = document.getElementById('input-edad').value.trim();
    const origen = document.getElementById('input-origen').value;
    const direccion = document.getElementById('input-direccion').value.trim();
    const tel = document.getElementById('input-tel').value.trim();
    const edo = document.getElementById('input-estado').value;

    if (!nombre) { alert("Por favor escribe tu Nombre y Apellidos."); return; }
    if (!fecha) { alert("Por favor escribe tu Fecha de Nacimiento."); return; }
    if (!edad || isNaN(edad)) { alert("Por favor escribe tu Edad en números."); return; }
    if (!direccion) { alert("Por favor escribe tu Dirección en EE. UU."); return; }
    
    perfil = { 
        nombre_completo: nombre, 
        fecha_nacimiento: fecha,
        edad: edad,
        origen_mexico: origen,
        direccion_usa: direccion,
        telefono: tel, 
        estado: edo, 
        nacionalidad: "mexicana" 
    };

    // Renderizar resumen visual para que el ciudadano lo lea
    document.getElementById('resumen-visual-datos').innerHTML = `
        <p><strong>Tu Nombre:</strong> ${perfil.nombre_completo}</p>
        <p><strong>Tu Fecha de Nacimiento:</strong> ${perfil.fecha_nacimiento} (${perfil.edad} años)</p>
        <p><strong>Tu Dirección en USA:</strong> ${perfil.direccion_usa}</p>
        <p><strong>Tu Teléfono:</strong> ${perfil.telefono || 'No indicado'}</p>
        <p style="color:var(--primary); font-weight:bold;"><strong>Tu Estado Seleccionado por Clic:</strong> ${perfil.estado}</p>
    `;

    contadorRevisiones = 0;
    actualizarAlertaYVozRevision();
    irAPaso('paso-triple-revision');
}

function actualizarAlertaYVozRevision() {
    let textosPantallaLetrasRojas = [
        "🚨 REVISIÓN 1 DE 3: Mira bien tu nombre arriba en la pantalla. ¿Está escrito exactamente igualito que en tus papeles oficiales? Si tiene una sola letra mal, en el consulado no te van a atender y perderás tu cita.",
        "🚨 REVISIÓN 2 DE 3: Revisa el Estado de Estados Unidos que seleccionaste. Tuviste que haber tocado el estado donde vives ahorita. Tu número de teléfono no importa. Si pusiste otro estado, irás al consulado equivocado.",
        "🚨 REVISIÓN 3 DE 3: Última revisión de seguridad. ¿Tienes todos tus papeles guardados en tu mano ahorita mismo listos para llevar? Confirma que todo lo que pusiste es verdad para crear tu guía."
    ];
    
    let textosVozOir = [
        "Primera revisión obligatoria. Por favor, lee tu nombre en la pantalla. Debe estar escrito igualito que en tus papeles oficiales de nacimiento. Si una sola letra está mal, te van a regresar y perderás tu día. Da un clic para confirmar.",
        "Segunda revisión obligatoria. Mira el estado de residencia que seleccionaste. Tienes que tocar el estado donde estás viviendo ahorita. Tu número de celular no importa. Si dejas un estado que no es, te mandaremos al consulado equivocado. Da el segundo clic.",
        "Tercera revisión obligatoria. ¿Tienes todos tus papeles originales listos en tu mano ahorita mismo? Si es así, da el último clic en el botón verde para elegir qué documento quieres tramitar hoy."
    ];
    
    document.getElementById('texto-alerta-revision').innerText = textosPantallaLetrasRojas[contadorRevisiones];
    leerEnVozAlta(textosVozOir[contadorRevisiones]);
    
    document.getElementById('btn-confirmar-revision').innerText = `SÍ, YA REVISÉ (${contadorRevisiones + 1}/3)`;
}

function avanzarClicRevision() {
    contadorRevisiones++;
    if (contadorRevisiones >= 3) {
        window.speechSynthesis.cancel(); // Silenciar al entrar al catálogo
        cargarCatalogo();
    } else {
        actualizarAlertaYVozRevision();
    }
}

// 4. FLUJO DE ASISTENCIA Y COMUNICACIÓN CON EL SERVIDOR (FASTAPI)
async function cargarCatalogo() {
    try {
        let res = await fetch('/api/catalogo');
        let datos = await res.json();
        let lista = document.getElementById('lista-tramites');
        lista.innerHTML = "";
        
        datos.forEach(t => {
            let btn = document.createElement('button');
            btn.className = "option-btn";
            btn.onclick = () => iniciarTramite(t.caso);
            btn.innerHTML = `<strong>${t.nombre}</strong><span>${t.descripcion}</span>`;
            lista.appendChild(btn);
        });
        irAPaso('paso-tramites');
    } catch(e) {
        alert("Error de conexión al cargar los trámites del catálogo.");
    }
}

async function iniciarTramite(caso) {
    casoActual = caso;
    respuestas = {};
    try {
        let res = await fetch('/api/seleccionar-caso', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ caso: casoActual, perfil: perfil, respuestas: respuestas })
        });
        let data = await res.json();
        procesarPaso(data);
    } catch(e) { alert("Error al iniciar el cuestionario adaptativo."); }
}

async function enviarRespuesta(idPregunta, valor) {
    respuestas[idPregunta] = valor;
    try {
        let res = await fetch('/api/continuar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ caso: casoActual, pregunta_id: idPregunta, respuesta: valor, respuestas: respuestas, perfil: perfil })
        });
        let data = await res.json();
        procesarPaso(data);
    } catch(e) { alert("Error al registrar la respuesta en el servidor."); }
}

function procesarPaso(data) {
    if (data.pregunta) {
        irAPaso('paso-preguntas');
        document.getElementById('pregunta-titulo').innerText = data.servicio;
        document.getElementById('pregunta-texto').innerText = data.pregunta.pregunta;
        
        // El sistema le LEA en voz alta la pregunta actual de forma automatizada al usuario
        leerEnVozAlta(data.pregunta.pregunta);
  // El sistema le LEA en voz alta la pregunta actual de forma automatizada al usuario
        leerEnVozAlta(data.pregunta.pregunta);
        let opcionesCont = document.getElementById('contenedor-opciones');
        opcionesCont.innerHTML = "";
        data.pregunta.opciones.forEach(o => {
            let lbl = document.createElement('label');
            lbl.className = "radio-label";
            lbl.innerHTML = `<input type="radio" name="r_opt" value="${o}"> <span>${o}</span>`;
            lbl.onclick = () => {
                setTimeout(() => enviarRespuesta(data.pregunta.id, o), 150);
            };
            opcionesCont.appendChild(lbl);
        });
    } else if (data.resultado) {
        window.speechSynthesis.cancel();
        mostrarResultado(data.resultado);
    }
}

function mostrarResultado(r) {
    resultadoFinal = r;
    irAPaso('paso-resultado');
    let cajaEstado = document.getElementById('res-caja-estado');
    cajaEstado.className = "box-info " + (r.estado === "LISTO PARA TU CITA" ? "success" : "danger");
    cajaEstado.innerHTML = `<strong>ESTATUS: ${r.estado}</strong><br>${r.mensaje_estado}`;
    document.getElementById('res-consulado').innerText = r.consulado_nombre;
    document.getElementById('res-direccion').innerText = "📍 " + r.consulado_direccion;
    document.getElementById('res-telefono').innerText = "📞 Tel central: " + r.consulado_telefono;
    document.getElementById('res-pago').innerText = r.pago_estimado;
    document.getElementById('res-cita').innerText = r.cita_estatus;
    document.getElementById('res-cita').style.color = r.cita_estatus.includes("PENDIENTE") ? "var(--danger)" : "var(--accent)";
    inyectarLista('res-requisitos', r.requisitos_oficiales);
    let secFaltantes = document.getElementById('seccion-faltantes');
    if(r.faltantes.length > 0) {
        secFaltantes.style.display = "block";
        inyectarLista('res-faltantes', r.faltantes);
    } else {
        secFaltantes.style.display = "none";
    }
    inyectarLista('res-acciones', r.acciones_recomendadas);
    let btnWeb = document.getElementById('lnk-consulado-oficial');
    if (r.url_consulado) {
        btnWeb.href = r.url_consulado;
        btnWeb.style.display = "block";
    } else {
        btnWeb.style.display = "none";
    }
}

function inyectarLista(id, arreglo) {
    let el = document.getElementById(id);
    el.innerHTML = "";
    (arreglo || []).forEach(x => {
        let li = document.createElement('li');
        li.innerText = x;
        el.appendChild(li);
    });
}

// 5. MODAL DE VISUALIZACIÓN Y COMPILACIÓN DE GUÍAS DE EXPEDIENTES
async function verVistaPrevia() {
    if (!resultadoFinal) return;
    try {
        let res = await fetch('/api/pdf-preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(resultadoFinal)
        });
        if (res.ok) {
            let blob = await res.blob();
            let url = window.URL.createObjectURL(blob);
            document.getElementById('pdf-frame').src = url;
            document.getElementById('modal-pdf').classList.add('active');
        } else { 
            alert("No se pudo desplegar la hoja en pantalla."); 
        }
    } catch(e) { 
        alert("Error de red al intentar abrir la vista previa."); 
    }
}

function cerrarVistaPrevia() {
    document.getElementById('modal-pdf').classList.remove('active');
    document.getElementById('pdf-frame').src = "";
}

async function descargarPDF() {
    if (!resultadoFinal) return;
    try {
        let res = await fetch('/api/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(resultadoFinal)
        });
        if (res.ok) {
            let blob = await res.blob();
            let url = window.URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url;
            a.download = `Hoja_de_Ruta_${casoActual.toUpperCase()}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => window.URL.revokeObjectURL(url), 100);
        } else { 
            alert("No se pudo compilar tu archivo PDF editable."); 
        }
    } catch(e) { 
        alert("Error al conectar con el servidor para la descarga."); 
    }
}

function abortarCuestionario() { cargarCatalogo(); }
function reiniciarTodo() { comenzarDeNuevoLimpio(); }
iniciarRelojInactividad();
      
