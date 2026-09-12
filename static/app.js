// static/app.js
let perfilGlobal = {};
let casoActual = "";
let respuestasAcumuladas = {};

function nextStep(stepId) {
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    const target = document.getElementById(stepId);
    if (target) target.classList.add('active');
    window.scrollTo(0, 0);
}

function prevStep(stepId) {
    nextStep(stepId);
}

function capturarPerfil() {
    perfilGlobal = {
        nombre_completo: (document.getElementById('p-nombre')?.value || "").trim(),
        fecha_nacimiento: (document.getElementById('p-fecha')?.value || "").trim(),
        edad: (document.getElementById('p-edad')?.value || "").trim(),
        estado: document.getElementById('p-estado')?.value || "Otro",
        direccion: (document.getElementById('p-direccion')?.value || "").trim(),
        codigo_postal: (document.getElementById('p-cp')?.value || "").trim(),
        telefono: (document.getElementById('p-tel')?.value || "").trim(),
        trabajo: (document.getElementById('p-trabajo')?.value || "").trim(),
        nacionalidad: "mexicana"
    };
    return perfilGlobal;
}

function reiniciarFlujo() {
    casoActual = "";
    respuestasAcumuladas = {};
    nextStep('step-datos');
}

function abortarCuestionario() {
    casoActual = "";
    respuestasAcumuladas = {};
    nextStep('step-catalogo');
}

async function cargarCatalogo() {
    capturarPerfil();
    try {
        let res = await fetch('/api/catalogo');
        if (!res.ok) throw new Error("No se pudo obtener el catálogo.");
        let tramites = await res.json();
        let contenedor = document.getElementById('lista-tramites');
        if (contenedor) {
            contenedor.innerHTML = "";
            tramites.forEach(t => {
                let card = document.createElement('div');
                card.className = "option-card";
                card.onclick = () => iniciarTramite(t.caso);
                card.innerHTML = `<h3>${t.nombre}</h3><p>${t.descripcion}</p>`;
                contenedor.appendChild(card);
            });
        }
        nextStep('step-catalogo');
    } catch (e) {
        alert("Error al conectar con el motor consular: " + e.message);
    }
}

async function iniciarTramite(caso) {
    casoActual = caso;
    respuestasAcumuladas = {};
    try {
        let res = await fetch('/api/seleccionar-caso', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ caso: casoActual, perfil: perfilGlobal, respuestas: respuestasAcumuladas })
        });
        if (!res.ok) throw new Error("Error en el inicio del trámite.");
        let data = await res.json();
        procesarPasoMotor(data);
    } catch (e) {
        alert("Error al iniciar el cuestionario: " + e.message);
    }
}

async function enviarRespuesta(preguntaId, valor) {
    respuestasAcumuladas[preguntaId] = valor;
    try {
        let res = await fetch('/api/continuar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                caso: casoActual,
                pregunta_id: preguntaId,
                respuesta: valor,
                respuestas: respuestasAcumuladas,
                perfil: perfilGlobal
            })
        });
        if (!res.ok) throw new Error("Error al enviar la respuesta.");
        let data = await res.json();
        procesarPasoMotor(data);
    } catch (e) {
        alert("Error al procesar la respuesta: " + e.message);
    }
}

function procesarPasoMotor(data) {
    if (data.pregunta) {
        nextStep('step-pregunta');
        const tit = document.getElementById('pregunta-servicio-titulo');
        const bar = document.getElementById('progreso-barra');
        const txtProg = document.getElementById('progreso-texto');
        const txtPreg = document.getElementById('pregunta-texto');
        const contResp = document.getElementById('contenedor-respuestas');

        if (tit) tit.innerText = data.servicio;
        if (bar) bar.style.width = `${data.pregunta.progreso}%`;
        if (txtProg) txtProg.innerText = `PASO ${data.pregunta.paso} DE ${data.pregunta.total} (${data.pregunta.progreso}%)`;
        if (txtPreg) txtPreg.innerText = data.pregunta.pregunta;
        
        if (contResp) {
            contResp.innerHTML = "";
            if (data.pregunta.tipo === "opciones") {
                data.pregunta.opciones.forEach(o => {
                    let b = document.createElement('button');
                    b.className = "btn btn-secondary";
                    b.style.width = "100%";
                    b.style.textAlign = "left";
                    b.style.margin = "4px 0";
                    b.innerText = o;
                    b.onclick = () => enviarRespuesta(data.pregunta.id, o);
                    contResp.appendChild(b);
                });
            } else {
                let inp = document.createElement('input');
                inp.type = "text";
                inp.id = "txt-resp-dinamica";
                inp.placeholder = data.pregunta.placeholder || "Escribe tu respuesta aquí...";
                
                let bSend = document.createElement('button');
                bSend.className = "btn";
                bSend.style.marginTop = "10px";
                bSend.innerText = "Continuar";
                bSend.onclick = () => enviarRespuesta(data.pregunta.id, inp.value);
                
                contResp.appendChild(inp);
                contResp.appendChild(bSend);
            }
        }
    } else if (data.resultado) {
        renderizarResultado(data.resultado);
    }
}

function renderizarResultado(r) {
    nextStep('step-resultado');
    
    let esMenor = parseInt(perfilGlobal.edad) < 18 || JSON.stringify(r).toUpperCase().includes("MENOR DE EDAD");
    const alertaMenor = document.getElementById('alerta-menor-op7');
    if (alertaMenor) alertaMenor.style.display = esMenor ? "block" : "none";

    const cNombre = document.getElementById('r-consulado-nombre');
    const cDir = document.getElementById('r-consulado-dir');
    const cTel = document.getElementById('r-consulado-tel');
    const cEmerg = document.getElementById('r-consulado-emergencia');
    const est = document.getElementById('r-estatus');
    const cit = document.getElementById('r-cita');
    const pag = document.getElementById('r-pago');

    if (cNombre) cNombre.innerText = r.contacto?.nombre || "Oficina Consular No Asignada";
    if (cDir) cDir.innerText = `📍 Dirección: ${r.contacto?.direccion || 'N/D'}`;
    if (cTel) cTel.innerText = `📞 Teléfono Central: ${r.contacto?.telefono || 'N/D'}`;
    if (cEmerg) cEmerg.innerText = `🚨 Emergencia Protección: ${r.contacto?.emergencia || 'N/D'}`;

    if (est) {
        est.innerText = `${r.estado} - ${r.mensaje_estado}`;
        est.style.color = r.estado === "INCOMPLETO" ? "var(--danger)" : "var(--accent)";
    }
    if (cit) cit.innerText = r.cita || "";
    if (pag) pag.innerText = r.pago || "";

    inyectarLista('r-personas', r.personas);
    inyectarLista('r-faltantes', r.faltantes, "Ninguno pendiente crítico.");
    inyectarLista('r-revisar', r.por_revisar, "Sin alertas de revisión adicionales.");
    inyectarLista('r-especial', r.especial, "Sin condiciones especiales identificadas.");
    inyectarLista('r-acciones', r.acciones);

    let btnOficial = document.getElementById('lnk-oficial');
    if (btnOficial) {
        if (r.fuente) {
            btnOficial.href = r.fuente;
            btnOficial.style.display = "block";
        } else {
            btnOficial.style.display = "none";
        }
    }
}

function inyectarLista(id, data, msgVacio = "") {
    let el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    let arr = [];
    if (typeof data === "string" && data.trim()) arr = [data];
    else if (Array.isArray(data)) arr = data;
    
    if (arr.length === 0 && msgVacio) {
        let li = document.createElement('li');
        li.innerText = msgVacio;
        li.style.color = "#888";
        el.appendChild(li);
    } else {
        arr.forEach(i => {
            let li = document.createElement('li');
            li.innerText = i;
            el.appendChild(li);
        });
    }
}

async function descargarPDF() {
    try {
        let res = await fetch('/api/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ caso: casoActual, respuestas: respuestasAcumuladas, perfil: perfilGlobal })
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
        } else {
            alert("Error al compilar el PDF de la Hoja de Ruta.");
        }
    } catch (e) {
        alert("Error de red al intentar descargar el documento.");
    }
}
