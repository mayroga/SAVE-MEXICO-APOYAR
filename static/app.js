// static/app.js
let perfil = {};
let casoActual = "";
let respuestas = {};
let resultadoFinal = null;
let idTemporizador = null;
let contadorRevisiones = 0;

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
    const btnDiario = document.getElementById('btn-plan-diario');
    const btnMensual = document.getElementById('btn-plan-mensual');
    if (chk) {
        if (btnDiario) btnDiario.disabled = !chk.checked;
        if (btnMensual) btnMensual.disabled = !chk.checked;
    }
}

// 1. CÁLCULO DE EDAD AUTOMÁTICO EN SEGUNDOS
function calcularEdadAutomaticamente(valorFecha) {
    if (!valorFecha) return;
    const numeros = valorFecha.match(/\d{4}/); 
    if (numeros) {
        const anoNacimiento = parseInt(numeros[0], 10);
        const anoActual = new Date().getFullYear();
        const edadCalculada = anoActual - anoNacimiento;
        const inputEdad = document.getElementById('input-edad');
        if (inputEdad && edadCalculada > 0 && edadCalculada < 120) {
            inputEdad.value = edadCalculada;
            perfil.edad = edadCalculada.toString();
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const inputFecha = document.getElementById('input-fecha');
    if (inputFecha) {
        inputFecha.addEventListener("blur", () => {
            calcularEdadAutomaticamente(inputFecha.value);
        });
    }
});

function leerEnVozAlta(textoAIngresar) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        let locucion = new SpeechSynthesisUtterance(textoAIngresar);
        locucion.lang = 'es-MX';
        locucion.rate = 0.95;
        window.speechSynthesis.speak(locucion);
    }
}

function activarMicrofono(idElementoInput) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("El dictado por voz no está soportado en este dispositivo.");
        return;
    }
    let reconocimiento = new SpeechRecognition();
    reconocimiento.lang = 'es-MX';
    
    reconocimiento.onstart = () => {
        let btn = document.getElementById(`btn-voz-${idElementoInput.split('-')[1]}`);
        if (btn) btn.innerText = "🛑 Escuchando...";
    };
    
    reconocimiento.onresult = (event) => {
        let text = event.results[0][0].transcript;
        if (text.endsWith('.')) text = text.slice(0, -1);
        document.getElementById(idElementoInput).value = text;
        if (idElementoInput === 'input-fecha') calcularEdadAutomaticamente(text);
    };
    
    reconocimiento.onend = () => {
        let btn = document.getElementById(`btn-voz-${idElementoInput.split('-')[1]}`);
        if (btn) {
            if (idElementoInput === 'input-nombre') btn.innerText = "🎙️ Dictar Nombre";
            if (idElementoInput === 'input-fecha') btn.innerText = "🎙️ Dictar Fecha";
            if (idElementoInput === 'input-direccion') btn.innerText = "🎙️ Dictar Dirección";
        }
    };
    reconocimiento.start();
}

// 2. RETENCIÓN MOMENTÁNEA DE EXPEDIENTES EN DISPOSITIVO
function iniciarMecanismoRevision() {
    const nombre = document.getElementById('input-nombre').value.trim();
    const fecha = document.getElementById('input-fecha').value.trim();
    const edad = document.getElementById('input-edad').value.trim();
    const origen = document.getElementById('input-origen').value;
    const direccion = document.getElementById('input-direccion').value.trim();
    const tel = document.getElementById('input-tel').value.trim();
    const edo = document.getElementById('input-estado').value;

    if (!nombre || !fecha || !edad || !direccion) {
        alert("Por favor rellena todos tus datos obligatorios.");
        return;
    }

    perfil = { 
        nombre_completo: nombre, fecha_nacimiento: fecha, edad: edad,
        origen_mexico: origen, direccion_usa: direccion, telefono: tel, 
        estado: edo, nacionalidad: "mexicana" 
    };

    localStorage.setItem("perfil_retenido", JSON.stringify(perfil));

    document.getElementById('resumen-visual-datos').innerHTML = `
        <p><strong>Tu Nombre:</strong> ${perfil.nombre_completo}</p>
        <p><strong>Tu Fecha de Nacimiento:</strong> ${perfil.fecha_nacimiento} (${perfil.edad} años)</p>
        <p><strong>Tu Dirección en USA:</strong> ${perfil.direccion_usa}</p>
        <p><strong>Tu Teléfono:</strong> ${perfil.telefono || 'No indicado'}</p>
        <p style="color:var(--primary); font-weight:bold;"><strong>Tu Estado Seleccionado:</strong> ${perfil.estado}</p>
    `;

    contadorRevisiones = 0;
    actualizarAlertaYVozRevision();
    irAPaso('paso-triple-revision');
}

function actualizarAlertaYVozRevision() {
    let textosPantallaLetrasRojas = [
        "🚨 REVISIÓN 1 DE 3: Mira bien tu nombre arriba en la pantalla. ¿Está escrito exactamente igualito que en tus papeles oficiales? Si tiene una sola letra mal, en el consulado no te van a atender.",
        "🚨 REVISIÓN 2 DE 3: Revisa el Estado de Estados Unidos que seleccionaste. Tuviste que haber tocado el estado donde vives ahorita. Tu número de teléfono no importa.",
        "🚨 REVISIÓN 3 DE 3: Última revisión de seguridad. ¿Tienes todos tus papeles guardados en tu mano ahorita mismo listos para llevar? Confirma que todo lo que pusiste es verdad."
    ];
    let textosVozOir = [
        "Primera revisión obligatoria. Por favor, lee tu nombre en la pantalla. Debe estar escrito igualito que en tus papeles oficiales de nacimiento. Da un clic para confirmar.",
        "Segunda revisión obligatoria. Mira el estado de residencia que seleccionaste. Tienes que tocar el estado donde estás viviendo ahorita. Tu número de celular no importa. Da el segundo clic.",
        "Tercera revisión obligatoria. ¿Tienes todos tus papeles originales listos en tu mano ahorita mismo? Si es así, da el último clic en el botón verde."
    ];
    
    document.getElementById('texto-alerta-revision').innerText = textosPantallaLetrasRojas[contadorRevisiones];
    leerEnVozAlta(textosVozOir[contadorRevisiones]);
    document.getElementById('btn-confirmar-revision').innerText = `SÍ, YA REVISÉ (${contadorRevisiones + 1}/3)`;
}

function avanzarClicRevision() {
    contadorRevisiones++;
    if (contadorRevisiones >= 3) {
        window.speechSynthesis.cancel();
        if (localStorage.getItem("modo_desarrollador") === "activo") {
            document.cookie = "token=dev_token_permanente; path=/; max-age=86400; samesite=lax";
        }
        cargarCatalogo();
    } else {
        actualizarAlertaYVozRevision();
    }
}

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
    } catch(e) { alert("Error al cargar el catálogo."); }
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
    } catch(e) { alert("Error al iniciar el trámite."); }
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
    } catch(e) { alert("Error al procesar la respuesta."); }
}

// 3. ASIGNACIÓN ASISTIDA DE VIGENCIA DEL PASAPORTE POR EDAD
function procesarPaso(data) {
    if (data.pregunta) {
        if (data.pregunta.id === "vigencia_pasaporte" && perfil.edad) {
            let edadNum = parseInt(perfil.edad, 10);
            let vigenciaAutomatica = "3 años";
            if (edadNum < 3) vigenciaAutomatica = "1 año (Solo menores de 3 años)";
            else if (edadNum < 18) vigenciaAutomatica = "6 años";
            else if (edadNum >= 18) vigenciaAutomatica = "10 años (Solo adultos mayores de 18)";
            
            enviarRespuesta(data.pregunta.id, vigenciaAutomatica);
            return;
        }
        irAPaso('paso-preguntas');
        document.getElementById('pregunta-titulo').innerText = data.servicio;
        document.getElementById('pregunta-texto').innerText = data.pregunta.pregunta;
        leerEnVozAlta(data.pregunta.pregunta);
        let opcionesCont = document.getElementById('contenedor-opciones');
        if (opcionesCont) {
            opcionesCont.innerHTML = "";
            data.pregunta.opciones.forEach(o => {
                let lbl = document.createElement('label');
                lbl.className = "radio-label";
                // CORREGIDO: Se agregaron los acentos graves obligatorios para inyectar HTML dinámico
                lbl.innerHTML = `<input type="radio" name="r_opt" value="${o}"> <span>${o}</span>`;
                lbl.onclick = () => { setTimeout(() => enviarRespuesta(data.pregunta.id, o), 150); };
                opcionesCont.appendChild(lbl);
            });
        }
    } else if (data.resultado) {
        window.speechSynthesis.cancel();
        mostrarResultado(data.resultado);
    }
}

function mostrarResultado(r) {
    resultadoFinal = r;
    irAPaso('paso-resultado');
    let cajaEstado = document.getElementById('res-caja-estado');
    if (cajaEstado) {
        cajaEstado.className = "box-info " + (r.estado === "LISTO PARA TU CITA" ? "success" : "danger");
        // CORREGIDO: Se agregaron los acentos graves obligatorios
        cajaEstado.innerHTML = `<strong>ESTATUS: ${r.estado}</strong><br>${r.mensaje_estado}`;
    }
    document.getElementById('res-consulado').innerText = r.consulado_nombre;
    document.getElementById('res-direccion').innerText = "📍 " + r.consulado_direccion;
    document.getElementById('res-telefono').innerText = "📞 Tel central: " + r.consulado_telefono;
    document.getElementById('res-pago').innerText = r.pago_estimado;
    document.getElementById('res-cita').innerText = r.cita_estatus;
    
    let citaEl = document.getElementById('res-cita');
    if (citaEl) citaEl.style.color = r.cita_estatus.includes("PENDIENTE") ? "var(--danger)" : "var(--accent)";
    
    inyectarLista('res-requisitos', r.requisitos_oficiales);
    let secFaltantes = document.getElementById('seccion-faltantes');
    if (secFaltantes) secFaltantes.style.display = r.faltantes.length > 0 ? "block" : "none";
    
    inyectarLista('res-faltantes', r.faltantes);
    inyectarLista('res-acciones', r.acciones_recomendadas);
    
    let btnWeb = document.getElementById('lnk-consulado-oficial');
    if (btnWeb) {
        btnWeb.href = r.url_consulado || "#";
        btnWeb.style.display = r.url_consulado ? "block" : "none";
    }
}

function inyectarLista(id, arreglo) {
    let el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    (arreglo || []).forEach(x => {
        let li = document.createElement('li');
        li.innerText = x;
        el.appendChild(li);
    });
}

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
            const iframe = document.getElementById('pdf-frame');
            if (iframe) iframe.src = url;
            const modal = document.getElementById('modal-pdf');
            if (modal) modal.classList.add('active');
        } else { 
            alert("Error 422/400: El servidor rechazó la estructura de vista previa."); 
        }
    } catch(e) { 
        alert("Error de comunicación para generar vista previa."); 
    }
}

function cerrarVistaPrevia() {
    const modal = document.getElementById('modal-pdf');
    if (modal) modal.classList.remove('active');
    const iframe = document.getElementById('pdf-frame');
    if (iframe) iframe.src = "";
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
            // CORREGIDO: Se agregaron los acentos graves obligatorios
            a.download = `Hoja_de_Ruta_${casoActual.toUpperCase()}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => window.URL.revokeObjectURL(url), 100);
        } else { 
            alert("Error al guardar tu Hoja de Ruta Consular."); 
        }
    } catch(e) { 
        alert("Error de red al compilar tu PDF final."); 
    }
}

function comenzarDeNuevoLimpio() {
    casoActual = ""; respuestas = {}; resultadoFinal = null; contadorRevisiones = 0;
    const datosGuardados = localStorage.getItem("perfil_retenido");
    if (datosGuardados) {
        const pData = JSON.parse(datosGuardados);
        document.getElementById('input-nombre').value = pData.nombre_completo || "";
        document.getElementById('input-fecha').value = pData.fecha_nacimiento || "";
        document.getElementById('input-edad').value = pData.edad || "";
        document.getElementById('input-direccion').value = pData.direccion_usa || "";
        document.getElementById('input-tel').value = pData.telefono || "";
        document.getElementById('input-origen').value = pData.origen_mexico || "Michoacán";
        document.getElementById('input-estado').value = pData.estado || "California";
        perfil = pData;
    }
    document.getElementById('check-legal').checked = false;
    validarCheck();
    irAPaso('paso-legal');
}

async function bypassDesarrollador(user, pass) {
    if (!user || !pass) { alert("Ingresa tus credenciales."); return; }
    try {
        let res = await fetch('/api/login-developer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        let data = await res.json();
        if (res.ok && data.ok) {
            localStorage.setItem("modo_desarrollador", "activo");
            // CORREGIDO: Se agregaron acentos graves y comillas correspondientes al string de asignación de cookies
            document.cookie = `token=${data.token}; path=/; max-age=86400; samesite=lax`;
            alert("Bypass de pago activado.");
            window.location.href = "/";
        } else { 
            alert("Credenciales incorrectas."); 
        }
    } catch(e) { 
        alert("Error de autenticación."); 
    }
}

async function solicitarAccesoStripe(tipoPlan) {
    try {
        // CORREGIDO: Se agregaron acentos graves obligatorios para construir la URL del fetch comercial
        let res = await fetch(`/api/checkout?plan=${tipoPlan}`, { method: 'POST' });
        let data = await res.json();
        if (data.url) window.location.href = data.url;
    } catch(e) { 
        alert("Error al llamar a Stripe."); 
    }
}

function capturarRespuestaStripe() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('stripe_success') === "true") {
        // CORREGIDO: Se agregaron acentos graves obligatorios para concatenar la sesión de Stripe en la cookie
        document.cookie = `token=${urlParams.get('session_id')}; path=/; max-age=86400; samesite=lax`;
        localStorage.setItem("pago_stripe_activo", "activo");
        window.location.href = "/";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    capturarRespuestaStripe();
    if (document.cookie.includes("token=") || localStorage.getItem("modo_desarrollador") === "activo" || localStorage.getItem("pago_stripe_activo") === "activo") {
        const muro = document.getElementById('muro-pago-stripe');
        const btnComenzar = document.getElementById('btn-comenzar');
        if (muro) muro.style.display = 'none';
        if (btnComenzar) btnComenzar.style.display = 'block';
    }
});

function abortarCuestionario() { cargarCatalogo(); }
function reiniciarTodo() { comenzarDeNuevoLimpio(); }
iniciarRelojInactividad();
