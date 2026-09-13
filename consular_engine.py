import re,unicodedata
from copy import deepcopy
from datetime import date

APP="MEXICANO APOYA MEXICANO"
VERSION="10.1.0"

TARIFAS_SRE={
    "pasaporte_1":44,"pasaporte_3":101,"pasaporte_6":137,
    "pasaporte_10":209,"matricula":41,"credencial_ine":0
}

DIRECTORIO_SRE={
    "California":{"consulado":"Consulado General de México en Los Ángeles","direccion":"2401 W 6th St, Los Angeles, CA 90057","telefono":"213-351-6800","citas":"1-424-309-0009","emergencia":"213-219-0175","url_consulado":"https://sre.gob.mx"},
    "Texas":{"consulado":"Consulado General de México en Houston","direccion":"4507 San Jacinto St, Houston, TX 77004","telefono":"713-271-6800","citas":"1-424-309-0009","emergencia":"713-857-6504","url_consulado":"https://sre.gob.mx"},
    "Florida":{"consulado":"Consulado General de México en Miami","direccion":"2555 Ponce de Leon Blvd, 4th Floor, Coral Gables, FL 33134","telefono":"786-268-4900","citas":"1-424-309-0009","emergencia":"305-979-1534","url_consulado":"https://sre.gob.mx"},
    "Illinois":{"consulado":"Consulado General de México en Chicago","direccion":"204 S Ashland Ave, Chicago, IL 60607","telefono":"312-738-2383","citas":"1-424-309-0009","emergencia":"312-925-5022","url_consulado":"https://sre.gob.mx"},
    "New York":{"consulado":"Consulado General de México en Nueva York","direccion":"27 E 39th St, New York, NY 10016","telefono":"212-217-6400","citas":"1-424-309-0009","emergencia":"917-239-6699","url_consulado":"https://sre.gob.mx"},
    "Arizona":{"consulado":"Consulado General de México en Phoenix","direccion":"320 E McDowell Rd, Phoenix, AZ 85004","telefono":"602-242-7398","citas":"1-424-309-0009","emergencia":"602-616-5742","url_consulado":"https://sre.gob.mx"},
    "Otro":{"consulado":"Sección Consular de la Embajada de México","direccion":"1250 23rd St NW, Washington, DC 20037","telefono":"202-736-1000","citas":"1-424-309-0009","emergencia":"202-997-6265","url_consulado":"https://sre.gob.mx"}
}

def normalizar(v):
    s=str(v or "").strip().lower()
    s=unicodedata.normalize("NFD",s)
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

def texto(v): return str(v or "").strip()
def si(v): return normalizar(v) in {"si","s","yes","y","verdadero","true","1"}
def no(v): return normalizar(v) in {"no","n","false","0"}

def entero(v):
    m=re.search(r"\d{1,3}",texto(v))
    try:return int(m.group()) if m else None
    except:return None

def perfil_vacio():
    return {
        "nombre_completo":"","fecha_nacimiento":"","edad":"",
        "direccion_usa":"","telefono":"","origen_mexico":"Michoacán",
        "estado":"Otro","nacionalidad":"mexicana"
    }

def fusionar(a,b):
    r=dict(a or {})
    for k,v in (b or {}).items():
        if v not in ("",None,[]):r[k]=v
    return r

def unicos(xs):
    r=[]
    for x in xs or []:
        x=texto(x)
        if x and x not in r:r.append(x)
    return r

def _perfil_desde(respuestas=None,perfil=None):
    p=fusionar(perfil_vacio(),perfil)
    for k in p:
        if texto((respuestas or {}).get(k)):p[k]=respuestas[k]
    return p

def validar_edad_fecha(p):
    edad=entero(p.get("edad"))
    f=texto(p.get("fecha_nacimiento"))
    if edad is None or not f:return []
    nums=re.findall(r"\d{1,4}",f)
    if len(nums)!=3:return []
    try:
        a,b,c=map(int,nums)
        y,m,d=(a,b,c) if a>1900 else (c,b,a)
        if not(1900<=y<=date.today().year and 1<=m<=12 and 1<=d<=31):return []
        real=date.today().year-y-((date.today().month,date.today().day)<(m,d))
        if real!=edad:
            return [f"Aviso: Tu fecha de nacimiento ({f}) y la edad ingresada ({edad} años) no coinciden matemáticamente."]
    except Exception:pass
    return []

def P(id,texto_,**kw):
    d={"id":id,"pregunta":texto_}
    d.update(kw)
    return d

TRAMITES={}

def registrar(caso,nombre,descripcion,preguntas,**info):
    TRAMITES[caso]={
        "caso":caso,"nombre":nombre,"descripcion":descripcion,
        "preguntas":preguntas,**info
    }

PASAPORTE_PREGUNTAS=[
    P("clasificacion_origen","¿Cómo obtuviste tu nacionalidad mexicana?",tipo="opciones",
      opciones=["Nací en México","Nací en EE.UU. (Hijo de padres mexicanos)","Me naturalicé (Tengo Carta de Naturalización SRE)"],required=True),
    P("acta_origen","¿Tienes tu documento original de nacionalidad? (Acta mexicana, Inserción de Acta o Carta de Naturalización)",tipo="opciones",opciones=["Sí","No"],required=True),
    P("identificacion","¿Tienes una identificación oficial original con fotografía vigente (INE, Matrícula, pasaporte anterior o ID de EE.UU.)?",tipo="opciones",opciones=["Sí","No"],required=True),
    P("padres_presencia","[REQUISITO MENOR DE EDAD] ¿Ambos padres pueden asistir físicamente contigo al consulado a firmar el formato de autorización OP-7?",tipo="opciones",
      opciones=["Sí, ambos asistirán","No, uno está en México (Requiere OP-7 Remota)","No, uno está en otro estado de EE.UU.","No, tengo la patria potestad exclusiva / un padre falleció"],required=False),
    P("id_padres","[REQUISITO MENOR DE EDAD] ¿Cuentan ambos padres con identificaciones oficiales vigentes con fotografía en original?",tipo="opciones",opciones=["Sí","No"],required=False),
    P("vigencia_pasaporte","¿Por cuántos años requieres tu pasaporte?",tipo="opciones",
      opciones=["1 año (Solo menores de 3 años)","3 años","6 años","10 años (Solo adultos mayores de 18)"],required=True),
    P("cita","¿Ya agendaste tu cita oficial en MiConsulado?",tipo="opciones",opciones=["Sí","No"],required=True)
]

MATRICULA_PREGUNTAS=[
    P("acta_origen","¿Tienes tu Acta de Nacimiento mexicana original?",tipo="opciones",opciones=["Sí","No"],required=True),
    P("identificacion","¿Tienes una identificación oficial con fotografía vigente?",tipo="opciones",opciones=["Sí","No"],required=True),
    P("domicilio","¿Tienes un comprobante de domicilio original a tu nombre en EE. UU.?",tipo="opciones",opciones=["Sí","No","A nombre de un tercero"],required=True),
    P("cita","¿Ya agendaste tu cita en MiConsulado?",tipo="opciones",opciones=["Sí","No"],required=True)
]

INE_PREGUNTAS=[
    P("acta_origen","¿Tienes tu Acta de Nacimiento mexicana original?",tipo="opciones",opciones=["Sí","No"],required=True),
    P("identificacion","¿Tienes una identificación oficial con fotografía vigente?",tipo="opciones",opciones=["Sí","No"],required=True),
    P("domicilio","¿Tienes un comprobante de domicilio original a tu nombre en el extranjero?",tipo="opciones",opciones=["Sí","No, a nombre de un tercero"],required=True),
    P("cita","¿Ya agendaste tu cita en el consulado para el trámite de INE?",tipo="opciones",opciones=["Sí","No"],required=True)
]

registrar("pasaporte","Pasaporte Mexicano",
          "Preparación para solicitar o renovar tu pasaporte de adulto o menor (Formato OP-7).",
          PASAPORTE_PREGUNTAS,
          documentos=["Documento de Nacionalidad (Acta o Carta SRE)","Identificación oficial con foto vigente","Pago de derechos"],
          pago="Según la vigencia elegida. Beneficio del 50% de descuento automático por Ley Federal de Derechos a mayores de 60 años.")

registrar("matricula","Matrícula Consular",
          "Preparación para obtener o renovar tu Matrícula Consular de alta seguridad.",
          MATRICULA_PREGUNTAS,
          documentos=["Acta de Nacimiento original","Identificación oficial con foto","Comprobante de domicilio en EE. UU."],
          pago=f"${TARIFAS_SRE['matricula']} USD exactos.")

registrar("ine","Credencial para Votar (INE)",
          "Preparación para tramitar tu credencial de elector desde el extranjero de forma gratuita.",
          INE_PREGUNTAS,
          documentos=["Acta de Nacimiento original","Identificación oficial con foto","Comprobante de domicilio"],
          pago="El trámite del INE es 100% gratuito. No dejes que nadie te cobre.")

def identificar_caso(t):
    n=normalizar(t)
    if "pasaporte" in n:return "pasaporte"
    if "matricula" in n:return "matricula"
    if "ine" in n or "credencial" in n or "votar" in n:return "ine"
    return ""

def obtener_caso(caso):return TRAMITES.get(caso)

def pregunta_por_id(caso,pid):
    c=obtener_caso(caso)
    if not c:return None
    return next((q for q in c["preguntas"] if q["id"]==pid),None)

def preguntas_activas(caso,res=None,p=None):
    c=obtener_caso(caso)
    if not c:return []
    edad=entero((p or {}).get("edad"))
    out=[]
    for q in c["preguntas"]:
        if "[REQUISITO MENOR DE EDAD]" in q["pregunta"]:
            if edad is not None and edad<18:out.append(q)
            continue
        if q["id"]=="vigencia_pasaporte" and edad is not None:
            x=deepcopy(q)
            if edad<3:x["opciones"]=["1 año","3 años"]
            elif edad<18:x["opciones"]=["3 años","6 años"]
            else:x["opciones"]=["3 años","6 años","10 años"]
            out.append(x)
        else:out.append(q)
    return out

def siguiente_pregunta(caso,respuestas=None,p=None):
    res=respuestas or {}
    for q in preguntas_activas(caso,res,p):
        if not texto(res.get(q["id"])):return q
    return None

def pregunta_json(q,numero=0,total=0):
    if not q:return None
    return {
        "id":q["id"],"pregunta":q["pregunta"],
        "tipo":q.get("tipo","texto"),
        "options":q.get("opciones",[]),
        "opciones":q.get("opciones",[]),
        "required":q.get("required",False),
        "paso":numero,"total":total,
        "progreso":round((numero-1)/total*100,1) if total else 0
    }

def interpretar_respuesta(q,v):
    v=texto(v)
    if not v:return v
    n=normalizar(v)
    if q.get("tipo")=="opciones":
        for o in q.get("opciones",[]):
            if n==normalizar(o):return o
        if n in {"si","s","yes","y"}:return "Sí"
        if n in {"no","n"}:return "No"
    return v

def calcular_pago(caso,res,p):
    if caso=="ine":return "¡GRATUITO! Este trámite no cuesta nada por Ley Federal."
    if caso=="matricula":return f"${TARIFAS_SRE['matricula']} USD."
    if caso=="pasaporte":
        vig=normalizar(res.get("vigencia_pasaporte"))
        edad=entero((p or {}).get("edad"))
        mult=.5 if edad is not None and edad>=60 else 1
        base=TARIFAS_SRE["pasaporte_3"]
        if "10" in vig:base=TARIFAS_SRE["pasaporte_10"]
        elif "6" in vig:base=TARIFAS_SRE["pasaporte_6"]
        elif "1" in vig:base=TARIFAS_SRE["pasaporte_1"]
        final=round(base*mult,2)
        return f"${final} USD."+(" (Incluye 50% de descuento por beneficio de Adulto Mayor)." if mult<1 else " (Tarifa ordinaria).")
    return "A confirmar en ventanilla."

def evaluar_requisitos(caso,res,p):
    c=obtener_caso(caso)
    if not c:return ["Trámite no disponible."]
    falt=[]
    edad=entero((p or {}).get("edad"))

    for q in preguntas_activas(caso,res,p):
        v=res.get(q["id"])
        if no(v) or not texto(v):
            pid=q["id"]
            if pid=="acta_origen":
                origen=str(res.get("clasificacion_origen",""))
                if "EE.UU." in origen:
                    falt.append("Llevar Acta de Nacimiento estadounidense original Y tu Inserción de Acta mexicana (Doble Nacionalidad).")
                elif "naturalice" in normalizar(origen):
                    falt.append("Llevar tu Carta de Naturalización mexicana original expedida por la SRE.")
                else:
                    falt.append("Llevar tu Acta de Nacimiento mexicana original en buen estado (que se lean bien las letras).")
            elif pid=="identificacion":
                falt.append("Llevar una identificación oficial con foto vigente en original.")
            elif pid=="domicilio":
                falt.append("Llevar un comprobante de domicilio original a tu nombre en los Estados Unidos.")
            elif pid=="cita":
                falt.append("No tienes cita. Tienes que agendar una cita oficial llamando al 1-424-309-0009.")

    if edad is not None and edad<18 and caso=="pasaporte":
        padres=str(res.get("padres_presencia",""))
        if "México" in padres:
            falt.append("[ALERTA OP-7 REMOTA] El padre en México debe ir a una delegación de la SRE a firmar el permiso.")
        elif "otro estado" in normalizar(padres):
            falt.append("[ALERTA OP-7 INTERCONSULAR] El padre ausente debe firmar la autorización en el consulado más cercano a su residencia.")
        if no(res.get("id_padres")):
            falt.append("Presentar identificaciones oficiales vigentes con fotografía de ambos padres en original.")

    domicilio=normalizar(res.get("domicilio"))
    if "nombre de un tercero" in domicilio:
        falt.append("El comprobante de domicilio no está a tu nombre. Lleva documentación que permita acreditar el domicilio y consulta su aceptación en ventanilla.")

    falt.extend(validar_edad_fecha(p))
    return unicos(falt)

def pantalla_resultado(caso,res,p):
    c=obtener_caso(caso)
    if not c:return {"estado":"INCOMPLETO","faltantes":["Trámite no disponible."]}
    falt=evaluar_requisitos(caso,res,p)
    estado="INCOMPLETO" if falt else "LISTO PARA TU CITA"
    estado_res=p.get("estado") or "Otro"
    cons= DIRECTORIO_SRE.get(estado_res,DIRECTORIO_SRE["Otro"])

    acciones=["Revisa muy bien tus papeles originales antes de salir de tu casa."]
    if falt:acciones.append("Consigue los documentos exactos que te marcamos en la lista.")
    if no(res.get("cita")):acciones.append("Llama al 1-424-309-0009 para obtener tu cita oficial.")
    acciones.append("Lleva esta Hoja de Ruta impresa el día de tu cita.")

    return {
        "caso":caso,"nombre_tramite":c["nombre"],"estado":estado,
        "mensaje_estado":"Te hacen falta documentos importantes para que te atiendan." if falt else "¡Felicidades! Tienes todo listo para tramitar tu documento.",
        "nombre_ciudadano":p.get("nombre_completo") or "Ciudadano Mexicano",
        "fecha_nacimiento":p.get("fecha_nacimiento") or "No indicada",
        "direccion_usa":p.get("direccion_usa") or "No indicada",
        "telefono_ciudadano":p.get("telefono") or "No indicado",
        "origen_mexico":p.get("origen_mexico") or "No indicado",
        "estado_residencia":estado_res,
        "requisitos_oficiales":c["documentos"],
        "faltantes":falt,
        "pago_estimado":calcular_pago(caso,res,p),
        "cita_estatus":"Cita agendada." if si(res.get("cita")) else "PENDIENTE: Debes agendar una cita obligatoriamente.",
        "consulado_nombre":cons["consulado"],
        "consulado_direccion":cons["direccion"],
        "consulado_telefono":cons["telefono"],
        "acciones_recomendadas":acciones,
        "url_consulado":cons["url_consulado"]
    }

def resultado(caso,respuestas=None,perfil=None):
    res=dict(respuestas or {})
    p=_perfil_desde(res,perfil)
    return pantalla_resultado(caso,res,p)

def iniciar(texto_inicial="",perfil=None):
    p=_perfil_desde({},perfil)
    caso=identificar_caso(texto_inicial)
    if not caso:return {"ok":True,"pantalla":"inicio","perfil":p,"tramites":catalogo()}
    return seleccionar_caso(caso,p)

def seleccionar_caso(caso,perfil=None,respuestas=None):
    if caso not in TRAMITES:raise ValueError("Trámite no disponible.")
    res=dict(respuestas or {})
    p=_perfil_desde(res,perfil)
    q=siguiente_pregunta(caso,res,p)
    if q:
        activos=preguntas_activas(caso,res,p)
        numero=next((i+1 for i,x in enumerate(activos) if x["id"]==q["id"]),1)
        return {
            "ok":True,"caso":caso,"servicio":TRAMITES[caso]["nombre"],
            "perfil":p,"respuestas":res,
            "pregunta":pregunta_json(q,numero,len(activos))
        }
    return {"ok":True,"caso":caso,"perfil":p,"respuestas":res,"resultado":pantalla_resultado(caso,res,p)}

def continuar(caso,respuestas=None,perfil=None,pregunta_id="",respuesta=""):
    if caso not in TRAMITES:raise ValueError("Trámite no disponible.")
    res=dict(respuestas or {})
    if pregunta_id:
        q=pregunta_por_id(caso,pregunta_id)
        if not q:raise ValueError("Pregunta no válida para este trámite.")
        res[pregunta_id]=interpretar_respuesta(q,respuesta)

    p=_perfil_desde(res,perfil)
    q=siguiente_pregunta(caso,res,p)

    if q:
        activos=preguntas_activas(caso,res,p)
        numero=next((i+1 for i,x in enumerate(activos) if x["id"]==q["id"]),1)
        return {
            "ok":True,"caso":caso,"servicio":TRAMITES[caso]["nombre"],
            "perfil":p,"respuestas":res,
            "pregunta":pregunta_json(q,numero,len(activos))
        }

    return {
        "ok":True,"caso":caso,"perfil":p,"respuestas":res,
        "resultado":pantalla_resultado(caso,res,p)
    }

def catalogo():
    return [{"caso":k,"nombre":v["nombre"],"descripcion":v["descripcion"]} for k,v in TRAMITES.items()]

__all__=[
    "APP","VERSION","TARIFAS_SRE","DIRECTORIO_SRE","TRAMITES",
    "catalogo","iniciar","seleccionar_caso","continuar","resultado"
]
