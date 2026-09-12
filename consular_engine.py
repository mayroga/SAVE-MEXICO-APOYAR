# PARTE 1: INICIO
import re, unicodedata

APP = "MEXICANO APOYA MEXICANO"
VERSION = "7.0.0"

# Tarifas oficiales de derechos consulares para adultos (en USD)
TARIFAS_SRE = {
    "pasaporte_3": 101,
    "pasaporte_6": 137,
    "pasaporte_10": 209,
    "matricula": 41,
    "credencial_ine": 0  # Trámite gratuito por ley
}

# Directorio de consulados por estado de residencia
DIRECTORIO_SRE = {
    "California": {
        "consulado": "Consulado General de México en Los Ángeles",
        "direccion": "2401 W 6th St, Los Angeles, CA 90057",
        "telefono": "213-351-6800"
    },
    "Texas": {
        "consulado": "Consulado General de México en Houston",
        "direccion": "4507 San Jacinto St, Houston, TX 77004",
        "telefono": "713-271-6800"
    },
    "Florida": {
        "consulado": "Consulado General de México en Miami",
        "direccion": "2555 Ponce de Leon Blvd, 4th Floor, Coral Gables, FL 33134",
        "telefono": "786-268-4900"
    },
    "Illinois": {
        "consulado": "Consulado General de México en Chicago",
        "direccion": "204 S Ashland Ave, Chicago, IL 60607",
        "telefono": "312-738-2383"
    },
    "New York": {
        "consulado": "Consulado General de México en Nueva York",
        "direccion": "27 E 39th St, New York, NY 10016",
        "telefono": "212-217-6400"
    },
    "Arizona": {
        "consulado": "Consulado General de México en Phoenix",
        "direccion": "320 E McDowell Rd, Phoenix, AZ 85004",
        "telefono": "602-242-7398"
    },
    "Otro": {
        "consulado": "Sección Consular de la Embajada de México",
        "direccion": "1250 23rd St NW, Washington, DC 20037",
        "telefono": "202-736-1000"
    }
}
# PARTE 1: FIN
# PARTE 2: INICIO
def normalizar(v):
    v = str(v or "").strip().lower()
    v = unicodedata.normalize("NFD", v)
    return "".join(c for c in v if unicodedata.category(c) != "Mn")

def texto(v):
    return str(v or "").strip()

def si(v):
    return normalizar(v) in {"si", "s", "yes", "y", "verdadero", "true", "1"}

def no(v):
    return normalizar(v) in {"no", "n", "false", "0"}

def perfil_vacio():
    return {
        "nombre_completo": "",
        "estado": "Otro",
        "telefono": "",
        "nacionalidad": "mexicana"
    }

def fusionar(a, b):
    r = dict(a or {})
    r.update({k: v for k, v in (b or {}).items() if v not in ("", None, [])})
    return r

def unicos(xs):
    r = []
    for x in xs or []:
        x = texto(x)
        if x and x not in r: r.append(x)
    return r

def _perfil_desde(respuestas, perfil=None):
    p = fusionar(perfil_vacio(), perfil)
    for k in p:
        if texto(respuestas.get(k)): p[k] = respuestas[k]
    return p

def P(id, texto_, **kw):
    d = {"id": id, "pregunta": texto_}
    d.update(kw)
    return d

TRAMITES = {}

def registrar(caso, nombre, descripcion, questions, **info):
    TRAMITES[caso] = {
        "caso": caso, "nombre": nombre, "descripcion": descripcion,
        "preguntas": questions, **info
    }
# PARTE 2: FIN
# PARTE 3: INICIO
PASAPORTE_PREGUNTAS = [
    P("acta_nacimiento", "¿Tienes tu Acta de Nacimiento mexicana original?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("identificacion", "¿Tienes una identificación oficial con fotografía vigente (INE, Matrícula anterior, etc.)?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("vigencia_pasaporte", "¿Por cuántos años quieres tu pasaporte?", tipo="opciones", opciones=["3 años", "6 años", "10 años"], required=True),
    P("cita", "¿Ya agendaste tu cita en MiConsulado?", tipo="opciones", opciones=["Sí", "No"], required=True)
]

MATRICULA_PREGUNTAS = [
    P("acta_nacimiento", "¿Tienes tu Acta de Nacimiento mexicana original?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("identificacion", "¿Tienes una identificación oficial con fotografía vigente?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("domicilio", "¿Tienes un comprobante de domicilio original a tu nombre en EE. UU.?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("cita", "¿Ya agendaste tu cita en MiConsulado?", tipo="opciones", opciones=["Sí", "No"], required=True)
]

INE_PREGUNTAS = [
    P("acta_nacimiento", "¿Tienes tu Acta de Nacimiento mexicana original?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("identificacion", "¿Tienes una identificación oficial con fotografía vigente?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("domicilio", "¿Tienes un comprobante de domicilio original a tu nombre en el extranjero?", tipo="opciones", opciones=["Sí", "No"], required=True),
    P("cita", "¿Ya agendaste tu cita en el consulado para el trámite de INE?", tipo="opciones", opciones=["Sí", "No"], required=True)
]

registrar(
    "pasaporte", "Pasaporte Mexicano",
    "Preparación para solicitar o renovar tu pasaporte de adulto.",
    PASAPORTE_PREGUNTAS,
    documentos=["Acta de Nacimiento original", "Identificación oficial con foto vigente", "Pago de derechos"],
    pago="Según la vigencia elegida (3, 6 o 10 años)."
)

registrar(
    "matricula", "Matrícula Consular",
    "Preparación para obtener o renovar tu Matrícula Consular de alta seguridad.",
    MATRICULA_PREGUNTAS,
    documentos=["Acta de Nacimiento original", "Identificación oficial con foto", "Comprobante de domicilio en EE. UU."],
    pago=f"${TARIFAS_SRE['matricula']} USD exactos en efectivo o tarjeta."
)

registrar(
    "ine", "Credencial para Votar (INE)",
    "Preparación para tramitar tu credencial de elector desde el extranjero.",
    INE_PREGUNTAS,
    documentos=["Acta de Nacimiento original", "Identificación oficial con foto", "Comprobante de domicilio"],
    pago="El trámite del INE es 100% gratuito. No dejes que nadie te cobre."
)
# PARTE 3: FIN
# PARTE 4: INICIO
def identificar_caso(t):
    n = normalizar(t)
    if "pasaporte" in n: return "pasaporte"
    if "matricula" in n: return "matricula"
    if "ine" in n or "credencial" in n or "votar" in n: return "ine"
    return ""

def obtener_caso(caso):
    return TRAMITES.get(caso)

def pregunta_por_id(caso, pid):
    c = obtener_caso(caso)
    if not c: return None
    return next((q for q in c["preguntas"] if q["id"] == pid), None)

def preguntas_activas(caso, res):
    c = obtener_caso(caso)
    return list(c["preguntas"]) if c else []

def siguiente_pregunta(caso, respuestas):
    for q in preguntas_activas(caso, respuestas):
        if not texto(respuestas.get(q["id"])): return q
    return None

def pregunta_json(q, numero=0, total=0):
    if not q: return None
    return {
        "id": q["id"], "pregunta": q["pregunta"], "tipo": q.get("tipo", "texto"),
        "opciones": q.get("opciones", []), "paso": numero, "total": total,
        "progreso": round((numero - 1) / total * 100, 1) if total else 0
    }

def interpretar_respuesta(q, v):
    v = texto(v)
    if not v: return v
    n = normalizar(v)
    if q.get("tipo") == "opciones":
        for o in q.get("opciones", []):
            if n == normalizar(o): return o
        if n in {"si", "s", "yes", "y"}: return "Sí"
        if n in {"no", "n"}: return "No"
    return v

def evaluar_requisitos(caso, res):
    falt = []; c = obtener_caso(caso)
    if not c: return ["Trámite no disponible."]
    for q in c["preguntas"]:
        v = res.get(q["id"])
        if no(v) or not texto(v):
            if q["id"] == "acta_nacimiento": 
                falt.append("Llevar tu Acta de Nacimiento mexicana original (no copias, no rota, que se lean bien las letras).")
            elif q["id"] == "identificacion": 
                falt.append("Llevar UNA de estas identificaciones en original con foto: tu credencial del INE anterior, tu Matrícula anterior, tu Cartilla Militar o tu Cédula Profesional.")
            elif q["id"] == "domicilio": 
                falt.append("Llevar un recibo original que demuestre dónde vives (puede ser de luz, agua, un papel de tu banco o tu contrato de renta).")
            elif q["id"] == "cita": 
                falt.append("No tienes cita. Tienes que agendar una porque si vas sin cita no te van a dejar pasar.")
    return unicos(falt)

def calcular_pago(caso, res):
    if caso == "ine": return "¡GRATUITO! Este trámite no cuesta nada."
    if caso == "matricula": return f"${TARIFAS_SRE['matricula']} USD."
    if caso == "pasaporte":
        vig = normalizar(res.get("vigencia_pasaporte"))
        if "10" in vig: return f"${TARIFAS_SRE['pasaporte_10']} USD."
        if "6" in vig: return f"${TARIFAS_SRE['pasaporte_6']} USD."
        return f"${TARIFAS_SRE['pasaporte_3']} USD."
    return "A confirmar en ventanilla."

def pantalla_resultado(caso, res, p):
    c = obtener_caso(caso)
    faltantes = evaluar_requisitos(caso, res)
    estado = "INCOMPLETO" if faltantes else "LISTO PARA TU CITA"
    est_usuario = p.get("estado") or "Otro"
    consulado_asig = DIRECTORIO_SRE.get(est_usuario, DIRECTORIO_SRE["Otro"])
    
    # URL oficial directa para que el cliente no pase trabajo buscando
    url_oficial = "https://sre.gob.mx" if est_usuario == "Florida" else "https://www.gob.mx"

    acciones = ["Revisa muy bien tus papeles originales antes de salir de tu casa."]
    if faltantes: acciones.append("Consigue los documentos exactos que te marcamos en la lista de arriba.")
    if no(res.get("cita")): acciones.append("Llama por teléfono al número 1-424-309-0009 para que te den tu cita oficial.")
    acciones.append("Lleva esta Hoja de Ruta impresa el día de tu cita para que te sirva de guía.")

    return {
        "caso": caso, "nombre_tramite": c["nombre"], "estado": estado,
        "mensaje_estado": "Te hacen falta documentos importantes para que te atiendan." if faltantes else "¡Felicidades! Tienes todo listo para tramitar tu documento.",
        "nombre_ciudadano": p.get("nombre_completo") or "Ciudadano Mexicano",
        "telefono_ciudadano": p.get("telefono") or "No indicado",
        "requisitos_oficiales": c["documentos"], "faltantes": faltantes,
        "pago_estimado": calcular_pago(caso, res), "cita_estatus": "Cita agendada." if si(res.get("cita")) else "PENDIENTE: Debes agendar una cita obligatoriamente.",
        "consulado_nombre": consulado_asig["consulado"], "consulado_direccion": consulado_asig["direccion"], "consulado_telefono": consulado_asig["telefono"],
        "acciones_recomendadas": acciones, "url_consulado": url_oficial
    }

def iniciar(texto_inicial="", perfil=None):
    p = _perfil_desde({}, perfil)
    caso = identificar_caso(texto_inicial)
    if not caso:
        return {"ok": True, "pantalla": "inicio", "perfil": p, "tramites": catalogo()}
    return seleccionar_caso(caso, p)

def seleccionar_caso(caso, perfil=None, respuestas=None):
    res = dict(respuestas or {})
    p = _perfil_desde(res, perfil)
    q = siguiente_pregunta(caso, res)
    if q:
        activos = preguntas_activas(caso, res)
        return {
            "ok": True, "caso": caso, "servicio": TRAMITES[caso]["nombre"], 
            "perfil": p, "respuestas": res, 
            "pregunta": pregunta_json(q, activos.index(q) + 1, len(activos))
        }
    return {"ok": True, "caso": caso, "perfil": p, "respuestas": res, "resultado": pantalla_resultado(caso, res, p)}

def continuar(caso, respuestas=None, perfil=None, pregunta_id="", respuesta=""):
    res = dict(respuestas or {})
    if pregunta_id:
        q = pregunta_por_id(caso, pregunta_id)
        if q: res[pregunta_id] = interpretar_respuesta(q, respuesta)
    p = _perfil_desde(res, perfil)
    q = Broad_q = siguiente_pregunta(caso, res)
    if q:
        activos = preguntas_activas(caso, res)
        return {
            "ok": True, "caso": caso, "servicio": TRAMITES[caso]["nombre"], 
            "perfil": p, "respuestas": res, 
            "pregunta": pregunta_json(q, activos.index(q) + 1, len(activos))
        }
    return {"ok": True, "caso": caso, "perfil": p, "respuestas": res, "resultado": pantalla_resultado(caso, res, p)}

def catalogo():
    return [
        {"caso": "pasaporte", "nombre": "Pasaporte Mexicano", "descripcion": "Saca o renueva tu pasaporte oficial para viajar o identificarte."},
        {"caso": "matricula", "nombre": "Matrícula Consular", "descripcion": "Obtén tu certificado de nacionalidad y residencia en Estados Unidos."},
        {"caso": "ine", "nombre": "Credencial para Votar (INE)", "descripcion": "Tramita gratis tu credencial electoral desde el extranjero para votar en México."}
    ]

__all__ = ["APP", "VERSION", "TARIFAS_SRE", "DIRECTORIO_SRE", "TRAMITES", "catalogo", "iniciar", "seleccionar_caso", "continuar"]
# PARTE FINAL: FIN
