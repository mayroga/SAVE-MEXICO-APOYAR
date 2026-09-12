# consular_engine.py
import re,unicodedata
from copy import deepcopy

APP="MEXICANO APOYA MEXICANO"
CONSULADO="Consulado de México en Miami"
FUENTES={
"pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/documentos-de-identidad/pasaporte",
"matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
"acta":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
"tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
"citas":"https://citas.sre.gob.mx"
}
CONTACTO={
"citas":"https://citas.sre.gob.mx",
"telefono":"1-424-309-0009",
"conmutador":"786-268-4900",
"direccion":"2555 Ponce de Leon Blvd., 4th Floor, Coral Gables, FL 33134",
"emergencia":"305-979-1534"
}
TARIFAS={
"pasaporte_1":"$44 USD",
"pasaporte_3":"$101 USD",
"pasaporte_6":"$137 USD",
"pasaporte_10":"$209 USD",
"matricula":"$41 USD",
"acta":"$20 USD"
}

def normalizar(v):
    v=unicodedata.normalize("NFD",str(v or ""))
    return "".join(c for c in v if unicodedata.category(c)!="Mn").lower().strip()

def texto(v):
    return str(v or "").strip()

def vacio(v):
    return not texto(v)

def si(v):
    return normalizar(v) in {"si","sí","yes","true","1","tengo","tiene","ya"}

def no(v):
    return normalizar(v) in {"no","false","0","ninguno","ninguna","no tengo"}

def unicos(a):
    r=[]
    for x in a or []:
        x=texto(x)
        if x and x not in r:r.append(x)
    return r

def fusionar(a,b):
    r=deepcopy(a or {})
    for k,v in (b or {}).items():
        if isinstance(v,dict) and isinstance(r.get(k),dict):
            r[k]=fusionar(r[k],v)
        elif not vacio(v):
            r[k]=v
    return r

def perfil_vacio():
    return {
        "nombre":"","apellido":"","nombre_completo":"",
        "nacionalidad":"","telefono":"","email":"",
        "direccion":"","ciudad":"","estado":"","zip":"",
        "fecha_nacimiento":""
    }

def extraer_email(s):
    m=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",s or "")
    return m.group(0) if m else ""

def extraer_telefono(s):
    m=re.search(r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}",s or "")
    return m.group(0) if m else ""

def extraer_zip(s):
    m=re.search(r"\b\d{5}(?:-\d{4})?\b",s or "")
    return m.group(0) if m else ""

ESTADOS_USA=[
"Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
"Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa",
"Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan",
"Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire",
"New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio",
"Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota",
"Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia",
"Wisconsin","Wyoming","District of Columbia"
]

def extraer_estado(s):
    n=normalizar(s)
    for e in ESTADOS_USA:
        if normalizar(e) in n:return e
    return ""

def extraer_nombre(s):
    s=texto(s)
    patrones=[
        r"(?:mi nombre es|me llamo)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{3,80})",
        r"(?:nombre completo)\s*[:\-]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{3,80})"
    ]
    for p in patrones:
        m=re.search(p,s,re.I)
        if m:
            x=m.group(1).strip(" .,-")
            return x
    return ""

def extraer_direccion(s):
    patrones=[
        r"(?:vivo en|mi direccion es|mi dirección es|direccion|dirección)\s*[:\-]?\s*([^.;\n]{5,120})"
    ]
    for p in patrones:
        m=re.search(p,s,re.I)
        if m:return m.group(1).strip()
    return ""

def extraer_nacionalidad(s):
    n=normalizar(s)
    if "naturalizado" in n:return "mexicano naturalizado"
    if "mexicano" in n:return "mexicano"
    if "mexicana" in n:return "mexicana"
    return ""

def extraer_perfil(s,perfil=None):
    p=fusionar(perfil_vacio(),perfil or {})
    s=texto(s)
    if not s:return p
    nom=extraer_nombre(s)
    if nom:
        p["nombre_completo"]=nom
    em=extraer_email(s)
    if em:p["email"]=em
    tel=extraer_telefono(s)
    if tel:p["telefono"]=tel
    z=extraer_zip(s)
    if z:p["zip"]=z
    e=extraer_estado(s)
    if e:p["estado"]=e
    d=extraer_direccion(s)
    if d:p["direccion"]=d
    n=extraer_nacionalidad(s)
    if n:p["nacionalidad"]=n
    return p

def P(id,texto,tipo="texto",**kw):
    d={"id":id,"texto":texto,"tipo":tipo}
    d.update(kw)
    return d

TRAMITES={}

def registrar(id,nombre,descripcion,fuente,categoria,preguntas,
              requisitos=None,personas=None,originales=None,copias=None,
              pago="",cita=True,vigencia="",entrega="",acciones=None,
              especiales=None):
    TRAMITES[id]={
        "id":id,"nombre":nombre,"descripcion":descripcion,
        "fuente":fuente,"categoria":categoria,
        "preguntas":preguntas or [],
        "requisitos":requisitos or [],
        "personas":personas or [],
        "originales":originales or [],
        "copias":copias or [],
        "pago":pago,"cita":cita,"vigencia":vigencia,
        "entrega":entrega,"acciones":acciones or [],
        "especiales":especiales or []
    }

# ============================================================
# 1. PASAPORTE - PRIMERA VEZ
# ============================================================

registrar(
"pasaporte_primera_vez",
"Pasaporte mexicano — primera vez",
"Preparación para solicitar por primera vez un pasaporte mexicano en el Consulado de México en Miami.",
FUENTES["pasaporte"],"Pasaporte",
[
 P("nacionalidad","¿Puedes demostrar que eres mexicano o mexicana con un documento original?","opciones",
   opciones=["Sí","No"]),
 P("identidad","¿Tienes un documento original con fotografía que permita comprobar tu identidad?","opciones",
   opciones=["Sí","No"]),
 P("documento_nacionalidad","¿Qué documento mexicano tienes para demostrar tu nacionalidad?","opciones",
   opciones=[
       "Acta de nacimiento mexicana",
       "Certificado de nacionalidad mexicana",
       "Declaración de nacionalidad mexicana",
       "Carta de naturalización",
       "Matrícula consular de alta seguridad",
       "Otro"
   ]),
 P("documento_identidad","¿Qué identificación con fotografía tienes?","opciones",
   opciones=[
       "INE",
       "Matrícula consular",
       "Licencia de conducir mexicana",
       "Licencia de conducir de Estados Unidos",
       "Identificación del gobierno de Estados Unidos",
       "Tarjeta de residente permanente",
       "Pasaporte",
       "Otra"
   ]),
 P("nombre","¿Cuál es tu nombre completo?"),
 P("telefono","¿Cuál es tu número de teléfono?"),
 P("direccion","¿Cuál es tu dirección actual?"),
 P("estado","¿En qué estado de Estados Unidos vives?"),
 P("zip","¿Cuál es tu ZIP Code?"),
 P("email","¿Cuál es tu correo electrónico? Puedes dejarlo vacío si no tienes."),
 P("cita","¿Ya tienes una cita para el trámite?","opciones",
   opciones=["Sí","No"]),
 P("vigencia","¿Qué vigencia de pasaporte deseas?","opciones",
   opciones=["1 año","3 años","6 años","10 años","No sé cuál me corresponde"])
],
requisitos=[
"Comparecer personalmente.",
"Contar con una cita.",
"Presentar un documento original que acredite la nacionalidad mexicana.",
"Presentar un documento original de identidad con fotografía.",
"Realizar el pago de la tarifa correspondiente."
],
personas=["La persona que solicita el pasaporte debe presentarse personalmente."],
originales=[
"Documento original que acredite la nacionalidad mexicana.",
"Documento original de identidad con fotografía."
],
copias=[],
pago="La tarifa depende de la vigencia elegida. Tarifas oficiales 2026: 1 año $44, 3 años $101, 6 años $137 y 10 años $209 USD.",
cita=True,
vigencia="Menores de 3 años: 1 o 3 años. De 3 a menos de 18 años: 3 o 6 años. Adultos: 3, 6 o 10 años.",
entrega="El Consulado de México en Estados Unidos informa que el pasaporte puede entregarse el mismo día después de cumplir los requisitos; el tiempo puede variar y puede haber demoras por fallas del sistema.",
acciones=[
"Verifica que tu nombre y datos estén correctos antes de finalizar el trámite.",
"Confirma la cita antes de acudir.",
"Confirma la tarifa vigente antes de pagar.",
"Lleva los documentos originales indicados."
]
)

# ============================================================
# 2. PASAPORTE - RENOVACIÓN
# ============================================================

registrar(
"pasaporte_renovacion",
"Pasaporte mexicano — renovación",
"Preparación para renovar un pasaporte mexicano.",
FUENTES["pasaporte"],"Pasaporte",
[
 P("pasaporte_actual","¿Tienes el pasaporte mexicano que vas a renovar?","opciones",
   opciones=["Sí","No"]),
 P("estado_pasaporte","¿El pasaporte está en condiciones de presentarse?","opciones",
   opciones=["Sí","No","Está dañado"]),
 P("naturalizado","¿Eres mexicano o mexicana por naturalización?","opciones",
   opciones=["Sí","No"]),
 P("fecha_pasaporte","¿Tu pasaporte fue expedido hace muchos años, antes de los periodos normales de renovación?","opciones",
   opciones=["Sí","No","No sé"]),
 P("nombre","¿Cuál es tu nombre completo?"),
 P("telefono","¿Cuál es tu número de teléfono?"),
 P("direccion","¿Cuál es tu dirección actual?"),
 P("estado","¿En qué estado de Estados Unidos vives?"),
 P("zip","¿Cuál es tu ZIP Code?"),
 P("email","¿Cuál es tu correo electrónico? Puedes dejarlo vacío si no tienes."),
 P("cita","¿Ya tienes una cita?","opciones",opciones=["Sí","No"])
],
requisitos=[
"Comparecer personalmente.",
"Contar con una cita.",
"Presentar el pasaporte que se desea renovar.",
"Realizar el pago correspondiente."
],
personas=["La persona titular del pasaporte debe presentarse personalmente."],
originales=["Pasaporte mexicano que se desea renovar."],
copias=[],
pago="Tarifa oficial 2026: 3 años $101 USD, 6 años $137 USD y 10 años $209 USD, según la vigencia que corresponda.",
cita=True,
vigencia="Adultos pueden solicitar 3, 6 o 10 años. Menores tienen reglas distintas.",
entrega="La entrega puede realizarse el mismo día después de cumplir los requisitos; el tiempo puede variar.",
acciones=[
"Revisa el pasaporte que vas a renovar.",
"Si eres naturalizado, prepara el documento original correspondiente.",
"Confirma que tu cita y tarifa estén vigentes.",
"Revisa tus datos antes de recibir/imprimir el documento."
],
especiales=[
"Un pasaporte de un año no puede renovarse como renovación ordinaria.",
"Pasaportes de emergencia, protección, restringidos o no canjeables pueden requerir un procedimiento especial.",
"Pasaportes antiguos pueden requerir documentación adicional según la fecha y lugar de expedición."
]
)

# ============================================================
# 3. PASAPORTE - PERDIDO / ROBADO / DAÑADO
# ============================================================

registrar(
"pasaporte_perdido_robo_mutilado",
"Pasaporte mexicano — perdido, robado o dañado",
"Preparación para solicitar un nuevo pasaporte cuando el anterior fue perdido, robado, destruido o está mutilado.",
FUENTES["pasaporte"],"Pasaporte",
[
 P("situacion","¿Qué ocurrió con tu pasaporte?","opciones",
   opciones=["Lo perdí","Me lo robaron","Está destruido","Está mutilado o muy dañado"]),
 P("reporte","¿Ya tienes un reporte o constancia de la autoridad competente sobre la pérdida o robo?","opciones",
   opciones=["Sí","No"]),
 P("nacionalidad","¿Tienes un documento original para demostrar tu nacionalidad mexicana?","opciones",
   opciones=["Sí","No"]),
 P("identidad","¿Tienes una identificación original con fotografía?","opciones",
   opciones=["Sí","No"]),
 P("nombre","¿Cuál es tu nombre completo?"),
 P("telefono","¿Cuál es tu teléfono?"),
 P("direccion","¿Cuál es tu dirección actual?"),
 P("estado","¿En qué estado vives?"),
 P("zip","¿Cuál es tu ZIP Code?"),
 P("email","¿Cuál es tu correo electrónico?"),
 P("cita","¿Ya tienes cita?","opciones",opciones=["Sí","No"])
],
requisitos=[
"Comparecer personalmente.",
"Presentar el reporte o constancia correspondiente cuando se trate de pérdida o robo.",
"Presentar documentación de nacionalidad mexicana.",
"Presentar identificación con fotografía.",
"Realizar el pago correspondiente.",
"Seguir el procedimiento de primera expedición cuando corresponda."
],
personas=["La persona titular debe presentarse personalmente."],
originales=[
"Reporte o constancia de la autoridad competente cuando corresponda.",
"Documento original de nacionalidad mexicana.",
"Identificación original con fotografía."
],
copias=[],
pago="La tarifa depende de la vigencia solicitada y de la situación concreta.",
cita=True,
vigencia="La vigencia dependerá del tipo de pasaporte que corresponda.",
entrega="La entrega está sujeta a que el expediente quede completo y el sistema consular funcione normalmente.",
acciones=[
"Primero reúne el reporte o constancia cuando corresponda.",
"No acudas pensando que el pasaporte perdido puede simplemente renovarse.",
"Prepara los documentos de nacionalidad e identidad.",
"Confirma con el Consulado cualquier situación especial antes de acudir."
],
especiales=[
"Cuando un pasaporte fue perdido, robado, destruido o mutilado, el procedimiento puede requerir documentación equivalente a una primera expedición.",
"Si el documento presenta una situación especial, el Consulado puede determinar requisitos adicionales."
]
)

# ============================================================
# 4. MATRÍCULA CONSULAR - PRIMERA VEZ
# ============================================================

registrar(
"matricula_primera_vez",
"Matrícula consular — primera vez",
"Preparación para solicitar por primera vez la matrícula consular de alta seguridad.",
FUENTES["matricula"],"Matrícula consular",
[
 P("nacionalidad","¿Tienes un documento original que demuestre tu nacionalidad mexicana?","opciones",
   opciones=["Sí","No"]),
 P("identidad","¿Tienes una identificación original con fotografía?","opciones",
   opciones=["Sí","No"]),
 P("domicilio","¿Tienes un comprobante original de domicilio a tu nombre con tu dirección completa?","opciones",
   opciones=["Sí","No","El comprobante está a nombre de otra persona"]),
 P("nombre","¿Cuál es tu nombre completo?"),
 P("telefono","¿Cuál es tu teléfono?"),
 P("direccion","¿Cuál es tu dirección actual?"),
 P("estado","¿En qué estado de Estados Unidos vives?"),
 P("zip","¿Cuál es tu ZIP Code?"),
 P("email","¿Cuál es tu correo electrónico?"),
 P("cita","¿Ya tienes una cita?","opciones",opciones=["Sí","No"])
],
requisitos=[
"Comparecer personalmente.",
"Contar con cita.",
"Presentar documento original de nacionalidad mexicana.",
"Presentar identificación original con fotografía.",
"Presentar comprobante de domicilio con dirección completa.",
"Realizar el pago correspondiente."
],
personas=["La persona que solicita la matrícula debe presentarse personalmente."],
originales=[
"Documento original de nacionalidad mexicana.",
"Identificación original con fotografía.",
"Comprobante de domicilio con dirección completa."
],
copias=[],
pago="La tarifa oficial 2026 para matrícula consular es $41 USD.",
cita=True,
vigencia="La matrícula consular tiene una vigencia de 5 años.",
entrega="El Consulado informa entrega el mismo día después de cumplir los requisitos; el tiempo puede variar.",
acciones=[
"Comprueba que el comprobante de domicilio tenga la dirección completa.",
"Si el comprobante no está a tu nombre, revisa con el Consulado qué documento alternativo corresponde a tu situación.",
"Revisa los datos antes de que se imprima la matrícula."
],
especiales=[
"Si el comprobante de domicilio está a nombre de un familiar o conocido, existen alternativas específicas que deben corresponder a la relación y situación del solicitante."
]
)

# ============================================================
# 5. MATRÍCULA CONSULAR - RENOVACIÓN
# ============================================================

registrar(
"matricula_renovacion",
"Matrícula consular — renovación",
"Preparación para renovar una matrícula consular.",
FUENTES["matricula"],"Matrícula consular",
[
 P("matricula_actual","¿Tienes tu matrícula consular actual?","opciones",
   opciones=["Sí","No"]),
 P("domicilio_cambio","¿Cambió tu domicilio desde que obtuviste la matrícula actual?","opciones",
   opciones=["Sí","No"]),
 P("domicilio","¿Tienes comprobante de domicilio a tu nombre?","opciones",
   opciones=["Sí","No","Está a nombre de otra persona"]),
 P("nombre","¿Cuál es tu nombre completo?"),
 P("telefono","¿Cuál es tu teléfono?"),
 P("direccion","¿Cuál es tu dirección actual?"),
 P("estado","¿En qué estado vives?"),
 P("zip","¿Cuál es tu ZIP Code?"),
 P("email","¿Cuál es tu correo electrónico?"),
 P("cita","¿Ya tienes una cita?","opciones",opciones=["Sí","No"])
],
requisitos=[
"Comparecer personalmente.",
"Contar con cita.",
"Presentar la matrícula consular actual.",
"Presentar comprobante de domicilio si cambió la residencia.",
"Realizar el pago correspondiente."
],
personas=["La persona titular debe presentarse personalmente."],
originales=["Matrícula consular actual."],
copias=[],
pago="La tarifa oficial 2026 para matrícula consular es $41 USD.",
cita=True,
vigencia="La matrícula consular tiene una vigencia de 5 años.",
entrega="El Consulado informa entrega el mismo día después de cumplir los requisitos; el tiempo puede variar.",
acciones=[
"Si tu domicilio no cambió, prepara tu matrícula actual.",
"Si cambió tu domicilio, prepara también el comprobante correspondiente.",
"Revisa los datos antes de que se imprima la nueva matrícula."
],
especiales=[
"El comprobante de domicilio se solicita cuando la residencia cambió."
]
)

# ============================================================
# 6. ACTA DE NACIMIENTO MEXICANA - COPIA CERTIFICADA
# ============================================================

registrar(
"acta_nacimiento_certificada",
"Acta de nacimiento mexicana — copia certificada",
"Preparación para obtener una copia certificada de un acta de nacimiento mexicana.",
FUENTES["acta"],"Acta de nacimiento",
[
 P("forma","¿Cómo quieres obtener el acta?","opciones",
   opciones=["En línea","En el Consulado"]),
 P("datos_acta","¿Tienes los datos necesarios para localizar tu acta de nacimiento?","opciones",
   opciones=["Sí","No"]),
 P("identidad","Si acudirás al Consulado, ¿tienes una identificación oficial que demuestre que eres el titular?","opciones",
   opciones=["Sí","No","No aplica"]),
 P("curp","¿Tienes tu CURP?","opciones",
   opciones=["Sí","No","No sé"]),
 P("nombre","¿Cuál es tu nombre completo?"),
 P("telefono","¿Cuál es tu teléfono?"),
 P("email","¿Cuál es tu correo electrónico?"),
 P("estado_nacimiento","¿En qué estado de México está registrada tu acta?"),
 P("cita","Si vas al Consulado, ¿ya tienes cita?","opciones",
   opciones=["Sí","No","No aplica"])
],
requisitos=[
"Para obtenerla en el Consulado: comparecer y presentar identificación oficial del titular.",
"Proporcionar los datos necesarios para localizar el acta.",
"Presentar CURP si se dispone de ella.",
"Completar la solicitud correspondiente.",
"Realizar el pago aplicable."
],
personas=["La persona interesada o titular debe realizar el trámite conforme al procedimiento correspondiente."],
originales=["Identificación oficial del titular cuando se solicite en el Consulado."],
copias=[],
pago="La tarifa oficial 2026 para copia certificada de acta de nacimiento es $20 USD en el Consulado.",
cita=True,
vigencia="No aplica como documento con vigencia fija; la validez del documento depende del uso que se le vaya a dar.",
entrega="La modalidad y entrega dependen de si se obtiene en línea o mediante el Consulado.",
acciones=[
"Si eliges la opción en línea, utiliza únicamente el portal oficial.",
"Si vas al Consulado, lleva los datos del acta y la identificación correspondiente.",
"Confirma la tarifa antes de realizar el pago."
],
especiales=[
"El Consulado de Miami informa que las copias certificadas también pueden obtenerse en línea mediante el portal oficial de actas.",
"El portal oficial para obtener el acta en línea es https://www.gob.mx/ActaNacimiento/"
]
)

# ============================================================
# DETECCIÓN DE TRÁMITES
# ============================================================

PALABRAS={
"pasaporte_primera_vez":[
"pasaporte","sacar pasaporte","primer pasaporte","primera vez pasaporte",
"nuevo pasaporte","quiero pasaporte"
],
"pasaporte_renovacion":[
"renovar pasaporte","renovacion pasaporte","renovación pasaporte",
"pasaporte vencido","se vencio","se venció","renovar"
],
"pasaporte_perdido_robo_mutilado":[
"pasaporte perdido","perdi mi pasaporte","perdí mi pasaporte",
"pasaporte robado","me robaron el pasaporte","pasaporte roto",
"pasaporte dañado","pasaporte mutilado","pasaporte destruido"
],
"matricula_primera_vez":[
"matricula consular","matrícula consular","primera matricula",
"primera matrícula","sacar matricula","sacar matrícula",
"quiero matricula"
],
"matricula_renovacion":[
"renovar matricula","renovar matrícula","matricula vencida",
"matrícula vencida","renovacion matricula","renovación matrícula"
],
"acta_nacimiento_certificada":[
"acta de nacimiento","copia certificada","acta certificada",
"certificacion de acta","certificación de acta","sacar acta"
]
}

def puntuar_caso(caso,s):
    n=normalizar(s)
    score=0
    for p in PALABRAS.get(caso,[]):
        if normalizar(p) in n:
            score+=2 if " " in p else 1
    return score

def identificar_caso(s):
    s=texto(s)
    n=normalizar(s)
    # Casos específicos primero
    if any(x in n for x in [
        "pasaporte perdido","perdi mi pasaporte","pasaporte robado",
        "me robaron el pasaporte","pasaporte dañado","pasaporte mutilado",
        "pasaporte destruido"
    ]):
        return "pasaporte_perdido_robo_mutilado"
    if any(x in n for x in [
        "renovar pasaporte","renovacion pasaporte","pasaporte vencido"
    ]):
        return "pasaporte_renovacion"
    if any(x in n for x in [
        "renovar matricula","renovacion matricula","matricula vencida"
    ]):
        return "matricula_renovacion"
    if "matricula" in n or "matrícula" in s.lower():
        return "matricula_primera_vez"
    if "acta de nacimiento" in n or "copia certificada" in n:
        return "acta_nacimiento_certificada"
    if "pasaporte" in n:
        return "pasaporte_primera_vez"
    return ""

def normalizar_servicio(servicio):
    n=normalizar(servicio)
    if "pasaporte" in n:return "pasaporte"
    if "matricula" in n:return "matricula"
    if "acta" in n:return "acta"
    return ""

# ============================================================
# REGLAS DE PREGUNTAS
# ============================================================

def obtener_caso(caso):
    return TRAMITES.get(caso or {})

def pregunta_por_id(caso,pid):
    c=obtener_caso(caso)
    if not c:return None
    for q in c["preguntas"]:
        if q["id"]==pid:return q
    return None

def _pregunta_aplica(q,r):
    pid=q.get("id","")
    if pid=="fecha_pasaporte":
        return True
    return True

def siguiente_pregunta(caso,respuestas,pregunta_id=""):
    c=obtener_caso(caso)
    if not c:return None
    r=respuestas or {}
    for q in c["preguntas"]:
        if not _pregunta_aplica(q,r):continue
        if vacio(r.get(q["id"])):return q
    return None

def pregunta_json(caso,q,respuestas=None):
    c=obtener_caso(caso)
    preguntas=c["preguntas"] if c else []
    r=respuestas or {}
    pendientes=[
        x for x in preguntas
        if _pregunta_aplica(x,r) and vacio(r.get(x["id"]))
    ]
    return {
        "id":q.get("id",""),
        "texto":q.get("texto",""),
        "tipo":q.get("tipo","texto"),
        "opciones":q.get("opciones",[]),
        "permite_otro":q.get("permite_otro",True),
        "obligatorio":q.get("obligatorio",True),
        "paso":len(preguntas)-len(pendientes)+1,
        "total":len(preguntas)
    }

def interpretar_respuesta(caso,pregunta_id,valor,respuestas=None):
    q=pregunta_por_id(caso,pregunta_id)
    if not q:return valor
    v=texto(valor)
    if q.get("tipo")=="opciones":
        for x in q.get("opciones",[]):
            if normalizar(x)==normalizar(v):
                return x
    return v

def _perfil_desde(respuestas,perfil=None):
    p=fusionar(perfil_vacio(),perfil or {})
    mapa={
        "nombre":"nombre_completo",
        "telefono":"telefono",
        "email":"email",
        "direccion":"direccion",
        "estado":"estado",
        "zip":"zip"
    }
    for k,d in mapa.items():
        if vacio(p.get(d)) and not vacio((respuestas or {}).get(k)):
            p[d]=texto(respuestas[k])
    return p

# ============================================================
# INFORMACIÓN DEL RESULTADO
# ============================================================

def datos_personales(perfil,respuestas):
    p=fusionar(perfil_vacio(),perfil or {})
    for k,d in {
        "nombre":"nombre_completo","telefono":"telefono",
        "email":"email","direccion":"direccion",
        "estado":"estado","zip":"zip"
    }.items():
        if vacio(p.get(d)) and not vacio((respuestas or {}).get(k)):
            p[d]=respuestas[k]
    return p

def personas_del_caso(caso):
    return obtener_caso(caso).get("personas",[]) if obtener_caso(caso) else []

def documentos_del_caso(caso):
    return obtener_caso(caso).get("requisitos",[]) if obtener_caso(caso) else []

def originales_del_caso(caso):
    return obtener_caso(caso).get("originales",[]) if obtener_caso(caso) else []

def copias_del_caso(caso):
    return obtener_caso(caso).get("copias",[]) if obtener_caso(caso) else []

def evaluar_requisitos(caso,respuestas):
    c=obtener_caso(caso)
    if not c:return {"faltan":[],"confirmar":[]}
    faltan=[]
    confirmar=[]
    for q in c["preguntas"]:
        v=respuestas.get(q["id"])
        if vacio(v):
            faltan.append(q["texto"])
    if caso=="pasaporte_perdido_robo_mutilado":
        if vacio(respuestas.get("reporte")) or no(respuestas.get("reporte")):
            faltan.append("Reporte o constancia de la autoridad competente.")
    if caso=="matricula_primera_vez":
        if normalizar(respuestas.get("domicilio"))=="no":
            faltan.append("Comprobante de domicilio.")
    if caso=="pasaporte_primera_vez":
        if no(respuestas.get("nacionalidad")):
            faltan.append("Documento original de nacionalidad mexicana.")
        if no(respuestas.get("identidad")):
            faltan.append("Identificación original con fotografía.")
    if caso=="pasaporte_renovacion":
        if no(respuestas.get("pasaporte_actual")):
            faltan.append("Pasaporte que se desea renovar.")
    if caso=="matricula_renovacion":
        if no(respuestas.get("matricula_actual")):
            faltan.append("Matrícula consular actual.")
    return {"faltan":unicos(faltan),"confirmar":unicos(confirmar)}

def calcular_estado(caso,respuestas,perfil):
    ev=evaluar_requisitos(caso,respuestas)
    if ev["faltan"]:
        return "rojo" if len(ev["faltan"])>=2 else "amarillo"
    return "verde"

def informacion_cita(caso,respuestas):
    c=obtener_caso(caso)
    if not c or not c["cita"]:return ""
    return (
        "La atención requiere cita. Consulta y confirma la cita en "
        f"{FUENTES['citas']} o mediante el teléfono {CONTACTO['telefono']}."
    )

def informacion_pago(caso,respuestas):
    c=obtener_caso(caso)
    return c.get("pago","") if c else ""

def vigencia_del_caso(caso,respuestas):
    c=obtener_caso(caso)
    return c.get("vigencia","") if c else ""

def entrega_del_caso(caso,respuestas):
    c=obtener_caso(caso)
    return c.get("entrega","") if c else ""

def situaciones_especiales(caso,respuestas):
    c=obtener_caso(caso)
    return c.get("especiales",[]) if c else []

def acciones_del_caso(caso,respuestas):
    c=obtener_caso(caso)
    return c.get("acciones",[]) if c else []

def _texto_estado(estado):
    if estado=="verde":
        return "🟢 PARECES LISTO"
    if estado=="amarillo":
        return "🟡 TE FALTA ALGO"
    return "🔴 ATENCIÓN / NO VAYAS TODAVÍA"

def pantalla_resultado(servicio,caso,respuestas=None,perfil=None):
    respuestas=deepcopy(respuestas or {})
    perfil=datos_personales(perfil or {},respuestas)
    c=obtener_caso(caso)
    if not c:
        return {
            "tipo":"error",
            "mensaje":"No pude identificar un trámite válido."
        }

    estado=calcular_estado(caso,respuestas,perfil)
    ev=evaluar_requisitos(caso,respuestas)

    if estado=="verde":
        mensaje="Con la información proporcionada, tienes los elementos principales preparados. Confirma la información oficial antes de acudir."
    elif estado=="amarillo":
        mensaje="Hay información que todavía debes completar o confirmar antes de acudir."
    else:
        mensaje="Todavía falta información o documentación importante. Es mejor no acudir hasta resolver lo indicado."

    return {
        "tipo":"resultado",
        "estado":estado,
        "titulo":_texto_estado(estado),
        "mensaje":mensaje,
        "servicio":servicio,
        "caso":caso,
        "nombre_tramite":c["nombre"],
        "descripcion":c["descripcion"],
        "perfil":perfil,
        "datos_personales":perfil,
        "respuestas":respuestas,
        "personas":personas_del_caso(caso),
        "requisitos":documentos_del_caso(caso),
        "originales":originales_del_caso(caso),
        "copias":copias_del_caso(caso),
        "faltan":ev["faltan"],
        "confirmar":ev["confirmar"],
        "pago":informacion_pago(caso,respuestas),
        "cita":informacion_cita(caso,respuestas),
        "vigencia":vigencia_del_caso(caso,respuestas),
        "entrega":entrega_del_caso(caso,respuestas),
        "especiales":situaciones_especiales(caso,respuestas),
        "acciones":acciones_del_caso(caso,respuestas),
        "fuente":c["fuente"],
        "fuente_oficial":c["fuente"],
        "boton_oficial":"VER INFORMACIÓN OFICIAL",
        "contacto":CONTACTO
    }

def resultado(servicio,caso,respuestas=None,perfil=None):
    return pantalla_resultado(servicio,caso,respuestas,perfil)

# ============================================================
# FLUJO PRINCIPAL
# ============================================================

def iniciar(texto_inicial="",servicio=""):
    s=texto(texto_inicial)
    perfil=extraer_perfil(s)
    caso=identificar_caso(s)

    if not caso:
        return {
            "tipo":"seleccion",
            "servicio":normalizar_servicio(servicio),
            "perfil":perfil,
            "catalogo":obtener_catalogo()
        }

    c=obtener_caso(caso)
    respuestas={}

    # La frase inicial solamente alimenta los datos que realmente
    # pueden identificarse. No se usa como respuesta automática
    # para todas las preguntas.
    if perfil.get("nombre_completo"):
        respuestas["nombre"]=perfil["nombre_completo"]
    if perfil.get("telefono"):
        respuestas["telefono"]=perfil["telefono"]
    if perfil.get("email"):
        respuestas["email"]=perfil["email"]
    if perfil.get("direccion"):
        respuestas["direccion"]=perfil["direccion"]
    if perfil.get("estado"):
        respuestas["estado"]=perfil["estado"]
    if perfil.get("zip"):
        respuestas["zip"]=perfil["zip"]

    q=siguiente_pregunta(caso,respuestas)

    if q:
        return {
            "tipo":"pregunta",
            "servicio":normalizar_servicio(servicio) or c["categoria"],
            "caso":caso,
            "pregunta":pregunta_json(caso,q,respuestas),
            "pregunta_id":q["id"],
            "respuestas":respuestas,
            "perfil":perfil
        }

    return pantalla_resultado(
        normalizar_servicio(servicio) or c["categoria"],
        caso,respuestas,perfil
    )

def seleccionar_caso(servicio,caso,perfil=None,respuestas=None):
    if caso not in TRAMITES:
        return {"tipo":"error","mensaje":"Trámite no disponible."}
    r=deepcopy(respuestas or {})
    p=fusionar(perfil_vacio(),perfil or {})
    for k,v in {
        "nombre":"nombre_completo","telefono":"telefono",
        "email":"email","direccion":"direccion",
        "estado":"estado","zip":"zip"
    }.items():
        if p.get(v) and not r.get(k):
            r[k]=p[v]

    q=siguiente_pregunta(caso,r)
    if q:
        return {
            "tipo":"pregunta",
            "servicio":servicio or obtener_caso(caso)["categoria"],
            "caso":caso,
            "pregunta":pregunta_json(caso,q,r),
            "pregunta_id":q["id"],
            "respuestas":r,
            "perfil":p
        }
    return pantalla_resultado(servicio,caso,r,p)

def continuar(servicio,caso,pregunta_id="",texto="",respuestas=None,perfil=None):
    r=deepcopy(respuestas or {})
    p=fusionar(perfil_vacio(),perfil or {})
    valor=texto if isinstance(texto,str) else str(texto or "")

    # IMPORTANTE:
    # app.js puede mandar la respuesta mediante "respuestas" y
    # dejar texto vacío. Por eso primero conservamos ese diccionario.
    if pregunta_id and valor.strip():
        r[pregunta_id]=interpretar_respuesta(caso,pregunta_id,valor,r)
        p=extraer_perfil(valor,p)

    # Si el texto contiene datos personales, se incorporan sin
    # convertir toda la frase en respuesta de la pregunta actual.
    p=extraer_perfil(valor,p)

    for k,d in {
        "nombre":"nombre_completo","telefono":"telefono",
        "email":"email","direccion":"direccion",
        "estado":"estado","zip":"zip"
    }.items():
        if vacio(r.get(k)) and not vacio(p.get(d)):
            r[k]=p[d]

    q=siguiente_pregunta(caso,r,pregunta_id)

    if q:
        return {
            "tipo":"pregunta",
            "servicio":servicio,
            "caso":caso,
            "pregunta":pregunta_json(caso,q,r),
            "pregunta_id":q["id"],
            "respuestas":r,
            "perfil":p
        }

    return pantalla_resultado(servicio,caso,r,p)

def interpretar(servicio,texto_usuario="",caso="",respuestas=None,perfil=None):
    s=texto(texto_usuario)
    r=deepcopy(respuestas or {})
    p=extraer_perfil(s,perfil or {})
    caso=caso or identificar_caso(s)

    if not caso:
        return {
            "tipo":"seleccion",
            "servicio":normalizar_servicio(servicio),
            "perfil":p,
            "catalogo":obtener_catalogo()
        }

    # Solo intenta responder la pregunta actual cuando el servidor
    # conoce cuál es. Los demás datos de la frase se guardan en perfil.
    pid=""
    q=siguiente_pregunta(caso,r)
    if q:
        pid=q["id"]

    if pid:
        r[pid]=interpretar_respuesta(caso,pid,s,r)

    for k,d in {
        "nombre":"nombre_completo","telefono":"telefono",
        "email":"email","direccion":"direccion",
        "estado":"estado","zip":"zip"
    }.items():
        if p.get(d):r[k]=p[d]

    return continuar(servicio,caso,pid,"",r,p)

# ============================================================
# CATÁLOGO / FUENTES / MANUAL
# ============================================================

def catalogo():
    return [
        {
            "id":"pasaporte_primera_vez",
            "nombre":"Pasaporte mexicano — primera vez",
            "descripcion":"Preparación para solicitar tu pasaporte por primera vez."
        },
        {
            "id":"pasaporte_renovacion",
            "nombre":"Pasaporte mexicano — renovación",
            "descripcion":"Preparación para renovar tu pasaporte."
        },
        {
            "id":"pasaporte_perdido_robo_mutilado",
            "nombre":"Pasaporte — perdido, robado o dañado",
            "descripcion":"Qué preparar cuando tu pasaporte se perdió, fue robado o está dañado."
        },
        {
            "id":"matricula_primera_vez",
            "nombre":"Matrícula consular — primera vez",
            "descripcion":"Preparación para obtener tu matrícula consular."
        },
        {
            "id":"matricula_renovacion",
            "nombre":"Matrícula consular — renovación",
            "descripcion":"Preparación para renovar tu matrícula consular."
        },
        {
            "id":"acta_nacimiento_certificada",
            "nombre":"Acta de nacimiento mexicana — copia certificada",
            "descripcion":"Preparación para obtener una copia certificada."
        }
    ]

def obtener_catalogo():
    return catalogo()

def obtener_fuentes():
    return {
        "pasaporte":FUENTES["pasaporte"],
        "matricula":FUENTES["matricula"],
        "acta":FUENTES["acta"],
        "tarifas":FUENTES["tarifas"],
        "citas":FUENTES["citas"]
    }

def obtener_contacto():
    return CONTACTO

def obtener_tarifas():
    return TARIFAS

def obtener_manual():
    return {
        "nombre":APP,
        "version":"4.0.0",
        "funciona_sin_ia":True,
        "tramites":catalogo(),
        "regla":"Nunca inventar requisitos. Si falta información, indicarlo como PENDIENTE DE COMPLETAR y dirigir a la fuente oficial.",
        "fuentes":obtener_fuentes(),
        "contacto":CONTACTO,
        "tarifas":TARIFAS
    }

# ============================================================
# COMPATIBILIDAD CON VERSIONES ANTERIORES
# ============================================================

def caso_info(caso):
    c=obtener_caso(caso)
    if not c:return {}
    return {
        "id":c["id"],
        "nombre":c["nombre"],
        "descripcion":c["descripcion"],
        "fuente":c["fuente"],
        "requisitos":c["requisitos"],
        "preguntas":c["preguntas"]
    }

def tramite_oficial(caso):
    c=obtener_caso(caso)
    return c["fuente"] if c else ""

def procesar(texto_usuario="",servicio="",caso="",respuestas=None,perfil=None):
    if caso:
        return continuar(
            servicio,caso,
            "",
            texto_usuario,
            respuestas or {},
            perfil or {}
        )
    return iniciar(texto_usuario,servicio)

# ============================================================
# VALIDACIÓN INTERNA
# ============================================================

MANUAL_VALIDACION={
    "pasaporte_primera_vez":True,
    "pasaporte_renovacion":True,
    "pasaporte_perdido_robo_mutilado":True,
    "matricula_primera_vez":True,
    "matricula_renovacion":True,
    "acta_nacimiento_certificada":True
}

def validar_manual():
    errores=[]
    for cid,c in TRAMITES.items():
        if not c["preguntas"]:
            errores.append(cid+": sin preguntas")
        if not c["requisitos"]:
            errores.append(cid+": sin requisitos")
        if not c["originales"]:
            errores.append(cid+": sin originales")
        if not c["fuente"]:
            errores.append(cid+": sin fuente oficial")
    return {"ok":not errores,"errores":errores}

def resumen_manual():
    v=validar_manual()
    return {
        "tramites":len(TRAMITES),
        "preguntas":sum(len(x["preguntas"]) for x in TRAMITES.values()),
        "ok":v["ok"],
        "errores":v["errores"]
    }

MANUAL_RESUMEN=resumen_manual()
