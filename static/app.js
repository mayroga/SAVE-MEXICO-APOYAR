// static/app.js
let perfil = {};
let casoActual = "";
let respuestas = {};
let resultadoFinal = null;
let idTemporizador = null;

// Reloj de Inactividad de 10 Minutos para obligar a comenzar de nuevo de forma limpia
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
    
    const nombre = document.getElementById('input-nombre');
    const fecha = document.getElementById('input-fecha');
    const origen = document.getElementById('input-origen');
    const direccion = document.getElementById('input-direccion');
    const tel = document.getElementById('input-tel');
    const edo = document.getElementById('input-estado');
    const chk = document.getElementById('check-legal');
    const btn = document.getElementById('btn-comenzar');
    
    if (nombre) nombre.value = "";
    if (fecha) fecha.value = "";
    if (origen) origen.value = "Michoacán";
    if (direccion) direccion.value = "";
    if (tel) tel.value = "";
    if (edo) edo.value = "California";
    if (chk) chk.checked = false;
    if (btn) btn.disabled = true;
    
    irAPaso('paso-legal');
}

function irAPaso(id) {
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(id);
    if (target) target.classList.add('active');
    window.scrollTo(0, 0);
}

function guardarDatos() {
    const nombre = document.getElementById('input-nombre').value.trim();
    const fecha = document.getElementById('input-fecha').value.trim();
    const origen = document.getElementById('input-origen').value;
    const direccion = document.getElementById('input-direccion').value.trim();
    const tel = document.getElementById('input-tel').value.trim();
    const edo = document.getElementById('input-estado').value;

    if (!nombre) { alert("Por favor escribe tu Nombre y Apellidos."); return; }
    if (!fecha) { alert("Por favor escribe tu Fecha de Nacimiento."); return; }
    if (!direccion) { alert("Por favor escribe tu Dirección en EE. UU."); return; }
    
    // Configuración idéntica a la clase ExpedientePerfil de Python
    perfil = { 
        nombre_completo: nombre, 
        fecha_nacimiento: fecha,
        origen_mexico: origen,
        direccion_usa: direccion,
        telefono: tel, 
        estado: edo, 
        nacionalidad: "mexicana" 
    };
    cargarCatalogo();
}

async function cargarCatalogo() {
    try {
        let res = await fetch('/api/catalogo');
        let datos = await res.json();
        let lista = document.getElementById('lista-tramites');
        if (lista) {
            lista.innerHTML = "";
            datos.forEach(t => {
                let btn = document.createElement('button');
                btn.className = "option-btn";
                btn.onclick = () => iniciarTramite(t.caso);
                btn.innerHTML = `<strong>${t.nombre}</strong><span>${t.descripcion}</span>`;
                lista.appendChild(btn);
            });
        }
        irAPaso('paso-tramites');
    } catch(e) {
        alert("Error de conexión al cargar trámites.");
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
        if (!res.ok) throw new Error("Error en respuesta del servidor");
        let data = await res.json();
        procesarPaso(data);
    } catch(e) { 
        alert("Error al iniciar el trámite. Reconectando con el servidor..."); 
    }
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
    } catch(e) { alert("Error al registrar respuesta."); }
}

function procesarPaso(data) {
    if (data.pregunta) {
        irAPaso('paso-preguntas');
        document.getElementById('pregunta-titulo').innerText = data.servicio;
        document.getElementById('pregunta-texto').innerText = data.pregunta.pregunta;
        
        let opcionesCont = document.getElementById('contenedor-opciones');
        if (opcionesCont) {
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
        }
    } else if (data.resultado) {
        mostrarResultado(data.resultado);
    }
}

function mostrarResultado(r) {
    resultadoFinal = r;
    irAPaso('paso-resultado');
    
    let cajaEstado = document.getElementById('res-caja-estado');
    if (cajaEstado) {
        cajaEstado.className = "box-info " + (r.estado === "LISTO PARA TU CITA" ? "success" : "danger");
        cajaEstado.innerHTML = `<strong>ESTATUS: ${r.estado}</strong><br>${r.mensaje_estado}`;
    }
    
    document.getElementById('res-consulado').innerText = r.consulado_nombre;
    document.getElementById('res-direccion').innerText = "📍 " + r.consulado_direccion;
    document.getElementById('res-telefono').innerText = "📞 Tel central: " + r.consulado_telefono;
    
    document.getElementById('res-pago').innerText = r.pago_estimado;
    document.getElementById('res-cita').innerText = r.cita_estatus;
    document.getElementById('res-cita').style.color = r.cita_estatus.includes("PENDIENTE") ? "var(--danger)" : "var(--accent)";

    inyectarLista('res-requisitos', r.requisitos_oficiales);
    
    let secFaltantes = document.getElementById('seccion-faltantes');
    if (secFaltantes) {
        if (r.faltantes.length > 0) {
            secFaltantes.style.display = "block";
            inyectarLista('res-faltantes', r.faltantes);
        } else {
            secFaltantes.style.display = "none";
        }
    }
    
    inyectarLista('res-acciones', r.acciones_recomendadas);

    let btnWeb = document.getElementById('lnk-consulado-oficial');
    if (btnWeb) {
        if (r.url_consulado) {
            btnWeb.href = r.url_consulado;
            btnWeb.style.display = "block";
        } else {
            btnWeb.style.display = "none";
        }
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
            document.getElementById('pdf-frame').src = url;
            document.getElementById('modal-pdf').classList.add('active');
        } else { alert("No se pudo abrir el cuadro de vista previa."); }
    } catch(e) { alert("Error de comunicación para generar vista previa."); }
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
            setTimeout(() => window.URL.revokeObjectURL(url), 2000);
        } else { 
            alert("No se pudo guardar tu Hoja de Ruta."); 
        }
    } catch(e) { 
        alert("Error de red al compilar tu PDF final."); 
    }
}

function abortarCuestionario() { 
    cargarCatalogo(); 
}

function reiniciarTodo() { 
    comenzarDeNuevoLimpio(); 
}

iniciarRelojInactividad();
