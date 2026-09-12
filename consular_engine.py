# consular_engine.py
import re,unicodedata
from copy import deepcopy

APP="MEXICANO APOYA MEXICANO"
CONSULADO="Consulado de México en Miami"

FUENTES={
 "citas":"https://citas.sre.gob.mx/",
 "consulado":"https://consulmex.sre.gob.mx/miami/",
 "pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
 "acta":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
 "doble_nacionalidad":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/doble-nacionalidad",
 "poderes":"https://consulmex.sre.gob.mx/miami/index.php/poderes-notariales",
 "cartilla":"https://consulmex.sre.gob.mx/miami/index.php/cartilla-militar",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "voto":"https://www.votoextranjero.mx/",
 "acta_online":"https://www.gob.mx/ActaNacimiento/"
}

CONTACTO={
 "citas":"1-424-309-0009",
 "general":"786-268-4900",
 "registro_civil":"786-268-4900 ext. 4905/4917",
 "notarial":"786-268-4900 ext. 4908",
 "op7":"786-268-4900 ext. 4923/4924",
 "emergencia":"305-979-1534",
 "direccion":"2555 Ponce de Leon Blvd., 4th Floor, Coral Gables, FL 33134"
}

TARIFAS={
 "pasaporte_1":"$44 USD",
 "pasaporte_3":"$101 USD",
 "pasaporte_6":"$137 USD",
 "pasaporte_10":"$209 USD",
 "matricula":"$41 USD",
 "acta_certificada":"$20 USD",
 "acta_doble_nacionalidad":"Registro gratuito; las copias certificadas pueden tener costo.",
 "credencial_votar":"Gratis"
}

def normalizar(v):
    s=str(v or "").strip().lower()
    s=unicodedata.normalize("NFD",s)
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

def texto(v):
    return str(v or "").strip()

def vacio(v):
    return not texto(v)

def si(v):
    return normalizar(v) in {"si","sí","yes","true","1","claro","correcto"}

def no(v):
    return normalizar(v) in {"no","false","0"}

def lista(v):
    if not v:return []
    if isinstance(v,list):return [texto(x) for x in v if texto(x)]
    return [texto(v)]

def unicos(v):
    r=[]
    for x in lista(v):
        if x not in r:r.append(x)
    return r

def pendiente(v):
    return texto(v) or "PENDIENTE DE COMPLETAR"

def fusionar(a,b):
    r=deepcopy(a or {})
    for k,v in (b or {}).items():
        if isinstance(v,dict) and isinstance(r.get(k),dict):
            r[k]=fusionar(r[k],v)
        elif v not in ("",None,[],{}):
            r[k]=v
    return r

def buscar(s,*palabras):
    s=normalizar(s)
    return any(normalizar(p) in s for p in palabras)

# ============================================================
# PERFIL
# ============================================================

CAMPOS_PERSONALES=[
 "nombre","nacionalidad","telefono","direccion","estado","zip","email"
]

def perfil_vacio():
    return {
        "nombre":"",
        "nacionalidad":"",
        "telefono":"",
        "direccion":"",
        "estado":"",
        "zip":"",
        "email":"",
        "menor":{},
        "padre_madre_tutor":{}
    }

def extraer_email(s):
    m=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",s or "")
    return m.group(0) if m else ""

def extraer_telefono(s):
    m=re.search(r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]\d{4}",s or "")
    return m.group(0) if m else ""

def extraer_zip(s):
    m=re.search(r"\b\d{5}(?:-\d{4})?\b",s or "")
    return m.group(0) if m else ""

ESTADOS_USA=[
"Alabama","Alaska","Arizona","Arkansas","California","Colorado",
"Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho",
"Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana",
"Maine","Maryland","Massachusetts","Michigan","Minnesota",
"Mississippi","Missouri","Montana","Nebraska","Nevada",
"New Hampshire","New Jersey","New Mexico","New York",
"North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
"Pennsylvania","Rhode Island","South Carolina","South Dakota",
"Tennessee","Texas","Utah","Vermont","Virginia","Washington",
"West Virginia","Wisconsin","Wyoming"
]

def extraer_estado(s):
    n=normalizar(s)
    for x in ESTADOS_USA:
        if normalizar(x) in n:return x
    return ""

def extraer_nombre(s):
    s=texto(s)
    patrones=[
        r"(?:mi nombre es|me llamo|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{2,})",
        r"(?:nombre)\s*[:\-]\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{2,})"
    ]
    for p in patrones:
        m=re.search(p,s,re.I)
        if m:
            x=m.group(1).strip(" .,;")
            x=re.split(r"\b(?:soy|vivo|resido|tengo|quiero|necesito|mi)\b",x,flags=re.I)[0]
            return x.strip(" .,;")
    return ""

def extraer_direccion(s):
    patrones=[
        r"(?:vivo en|resido en|mi direccion es|mi dirección es|direccion|dirección)\s*[:\-]?\s*(.+?)(?=(?:\b(?:mi nombre|me llamo|mi telefono|mi teléfono|mi correo|email|zip)\b)|$)"
    ]
    for p in patrones:
        m=re.search(p,s,re.I)
        if m:
            x=m.group(1).strip(" .,;")
            return x
    return ""

def extraer_nacionalidad(s):
    n=normalizar(s)
    if "naturalizado mexicano" in n or "mexicano naturalizado" in n:
        return "Mexicano naturalizado"
    if "mexicana naturalizada" in n:
        return "Mexicana naturalizada"
    if "mexicano" in n or "mexicana" in n:
        return "Mexicano"
    return ""

def extraer_fecha(s):
    m=re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",s or "")
    return m.group(1) if m else ""

def extraer_perfil(s,base=None):
    p=fusionar(perfil_vacio(),base or {})
    s=texto(s)
    if not s:return p

    nombre=extraer_nombre(s)
    email=extraer_email(s)
    telefono=extraer_telefono(s)
    zipc=extraer_zip(s)
    estado=extraer_estado(s)
    direccion=extraer_direccion(s)
    nacionalidad=extraer_nacionalidad(s)

    if nombre and not p["nombre"]:p["nombre"]=nombre
    if email:p["email"]=email
    if telefono:p["telefono"]=telefono
    if zipc:p["zip"]=zipc
    if estado:p["estado"]=estado
    if direccion and not p["direccion"]:p["direccion"]=direccion
    if nacionalidad:p["nacionalidad"]=nacionalidad

    return p

# ============================================================
# CASOS
# ============================================================

CASOS={}

def registrar(cid,**data):
    data["id"]=cid
    CASOS[cid]=data

def P(i,tipo,texto_,required=False,opciones=None,ayuda=""):
    d={"id":i,"tipo":tipo,"texto":texto_,"required":required}
    if opciones:d["opciones"]=opciones
    if ayuda:d["ayuda"]=ayuda
    return d

SI_NO=["Sí","No"]

registrar(
 "pasaporte_primera_vez",
 nombre="Pasaporte mexicano por primera vez",
 categoria="pasaportes",
 descripcion="Preparación para solicitar el pasaporte mexicano por primera vez.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("nacionalidad","opciones","¿Tienes un documento original que pruebe tu nacionalidad mexicana?",True,SI_NO),
  P("identidad","opciones","¿Tienes una identificación con fotografía que corresponda a tu identidad?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita para el trámite?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste la tarifa vigente del pasaporte?",True,SI_NO)
 ],
 requisitos_generales=[
  "Presentación personal.",
  "Cita previa.",
  "Documento original que acredite la nacionalidad mexicana.",
  "Documento original de identidad con fotografía.",
  "Pago de la tarifa vigente."
 ],
 requisitos_mapeados={
  "nacionalidad":"Documento original que acredite la nacionalidad mexicana.",
  "identidad":"Identificación original con fotografía.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación de la tarifa vigente."
 },
 documentos_nacionalidad=[
  "Acta de nacimiento mexicana.",
  "Certificado de nacionalidad mexicana.",
  "Declaración de nacionalidad mexicana.",
  "Carta de naturalización.",
  "Matrícula consular de alta seguridad expedida después de 2005."
 ],
 documentos_identidad=[
  "Identificación oficial con fotografía aceptada por el Consulado."
 ],
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 pdf={"titulo":"Pasaporte mexicano por primera vez"},
 acciones=[
  {"titulo":"AGENDAR CITA","texto":"Agenda o consulta tu cita oficial.","url":FUENTES["citas"]},
  {"titulo":"CONSULTAR REQUISITOS","texto":"Revisa los requisitos oficiales.","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "pasaporte_renovacion",
 nombre="Renovación de pasaporte mexicano",
 categoria="pasaportes",
 descripcion="Preparación para renovar un pasaporte mexicano.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("pasaporte_actual","opciones","¿Tienes el pasaporte que quieres renovar?",True,SI_NO),
  P("naturalizado","opciones","¿Eres mexicano naturalizado?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste la tarifa vigente?",True,SI_NO),
  P("pasaporte_especial","opciones","¿Tu pasaporte anterior fue de emergencia, protección, restringido, no canjeable o de un año?",False,SI_NO)
 ],
 requisitos_generales=[
  "Presentación personal.",
  "Cita previa.",
  "Pasaporte que se desea renovar.",
  "Pago de la tarifa vigente."
 ],
 requisitos_mapeados={
  "pasaporte_actual":"Pasaporte que se desea renovar.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación de la tarifa vigente."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 pdf={"titulo":"Renovación de pasaporte mexicano"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "pasaporte_perdido_robo_mutilado",
 nombre="Pasaporte perdido, robado, destruido o mutilado",
 categoria="pasaportes",
 descripcion="Preparación para reportar y tramitar nuevamente un pasaporte en estos casos.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("reporte","opciones","¿Ya tienes el reporte de la autoridad competente sobre la pérdida, robo, destrucción o mutilación?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste la tarifa vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "Reporte de la autoridad competente.",
  "La solicitud se atiende con requisitos de primera vez.",
  "Presentación personal.",
  "Cita previa.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "reporte":"Reporte de la autoridad competente.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación de la tarifa vigente."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=["Después del reporte, el trámite puede requerir documentación de primera expedición."],
 pdf={"titulo":"Pasaporte perdido, robado, destruido o mutilado"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "pasaporte_menor",
 nombre="Pasaporte mexicano para menor de edad",
 categoria="pasaportes",
 descripcion="Preparación del pasaporte de una persona menor de 18 años.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("nacionalidad_menor","opciones","¿Tienes el documento original que acredita la nacionalidad mexicana del menor?",True,SI_NO),
  P("identidad_menor","opciones","¿Tienes la identificación requerida del menor?",True,SI_NO),
  P("padres","opciones","¿Pueden presentarse los padres o quienes ejercen la patria potestad?",True,SI_NO),
  P("op7","opciones","¿Necesitas la autorización OP-7 de alguno de los padres?",True,SI_NO),
  P("identidades_padres","opciones","¿Tienes las identificaciones de los padres o tutores?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste la tarifa vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "El menor debe presentarse.",
  "Documento original de nacionalidad del menor.",
  "Documento de identidad del menor.",
  "Presentación de padres o tutores cuando corresponda.",
  "Autorización OP-7 cuando corresponda.",
  "Identificaciones de padres o tutores.",
  "Cita previa.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "nacionalidad_menor":"Documento original de nacionalidad del menor.",
  "identidad_menor":"Identificación del menor.",
  "padres":"Presentación de padres o tutores.",
  "op7":"Autorización OP-7 cuando corresponda.",
  "identidades_padres":"Identificaciones de padres o tutores.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación de la tarifa vigente."
 },
 personas=["menor","padre","madre"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=[
  "Si un padre no puede presentarse, puede ser necesaria la OP-7 mediante el procedimiento correspondiente.",
  "El divorcio o la separación por sí solos no eliminan la patria potestad."
 ],
 pdf={"titulo":"Pasaporte mexicano para menor"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "pasaporte_naturalizado",
 nombre="Pasaporte para mexicano naturalizado",
 categoria="pasaportes",
 descripcion="Preparación para una persona mexicana por naturalización.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("naturalizacion","opciones","¿Tienes el original de tu carta de naturalización o una copia certificada válida?",True,SI_NO),
  P("identidad","opciones","¿Tienes una identificación con fotografía?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste la tarifa vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "Carta de naturalización original o copia certificada válida.",
  "Identificación con fotografía.",
  "Presentación personal.",
  "Cita previa.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "naturalizacion":"Carta de naturalización original o copia certificada válida.",
  "identidad":"Identificación con fotografía.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación de la tarifa vigente."
 },
 documentos_nacionalidad=["Carta de naturalización original o copia certificada válida."],
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 pdf={"titulo":"Pasaporte para mexicano naturalizado"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "pasaporte_apellido_matrimonio",
 nombre="Pasaporte y apellido por matrimonio",
 categoria="pasaportes",
 descripcion="Información para acreditar el apellido del cónyuge cuando corresponda.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("acta_matrimonio","opciones","¿Tienes el acta de matrimonio que acredita el apellido de tu cónyuge?",True,SI_NO),
  P("pasaporte","opciones","¿Tienes tu pasaporte o documentación de identidad?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO)
 ],
 requisitos_generales=[
  "Documento que acredite el matrimonio cuando corresponda.",
  "Presentación personal.",
  "Cita previa."
 ],
 requisitos_mapeados={
  "acta_matrimonio":"Acta de matrimonio.",
  "pasaporte":"Documento de identidad o pasaporte.",
  "cita":"Cita para el trámite."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=["Revisa los datos antes de firmar o imprimir el documento."],
 pdf={"titulo":"Pasaporte y apellido por matrimonio"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "pasaporte_acta_extemporanea",
 nombre="Pasaporte con acta de nacimiento extemporánea",
 categoria="pasaportes",
 descripcion="Preparación para casos en los que el registro de nacimiento fue realizado fuera del periodo ordinario.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("fecha_nacimiento","texto","¿Cuál es la fecha de nacimiento?",True),
  P("fecha_registro","texto","¿Cuál es la fecha aproximada en que se registró el nacimiento?",True),
  P("acta","opciones","¿Tienes el acta de nacimiento original?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO)
 ],
 requisitos_generales=[
  "Acta de nacimiento.",
  "El Consulado puede requerir documentación complementaria según la antigüedad del registro.",
  "Puede existir una verificación adicional antes de expedir el pasaporte.",
  "Cita previa."
 ],
 requisitos_mapeados={
  "acta":"Acta de nacimiento.",
  "cita":"Cita para el trámite."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=[
  "En Miami existen periodos de referencia para registros extemporáneos según el año de nacimiento.",
  "Si el registro supera el periodo correspondiente, pueden solicitarse pruebas complementarias.",
  "La verificación puede retrasar la expedición del pasaporte."
 ],
 pdf={"titulo":"Pasaporte con acta de nacimiento extemporánea"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "matricula_primera_vez",
 nombre="Matrícula consular por primera vez",
 categoria="matricula",
 descripcion="Preparación para obtener la matrícula consular mexicana por primera vez.",
 fuente=FUENTES["matricula"],
 preguntas=[
  P("nacionalidad","opciones","¿Tienes un documento original que pruebe tu nacionalidad mexicana?",True,SI_NO),
  P("identidad","opciones","¿Tienes una identificación original con fotografía?",True,SI_NO),
  P("domicilio","opciones","¿Tienes un comprobante de domicilio con tu nombre y dirección completa?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste el costo vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "Presentación personal.",
  "Cita previa.",
  "Documento original de nacionalidad mexicana.",
  "Identificación original con fotografía.",
  "Comprobante de domicilio.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "nacionalidad":"Documento original de nacionalidad mexicana.",
  "identidad":"Identificación original con fotografía.",
  "domicilio":"Comprobante de domicilio con nombre y dirección completa.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación del costo vigente."
 },
 documentos_nacionalidad=[
  "Acta de nacimiento mexicana.",
  "Carta de naturalización.",
  "Certificado de nacionalidad mexicana.",
  "Declaración de nacionalidad mexicana."
 ],
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 pdf={"titulo":"Matrícula consular por primera vez"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["matricula"]}
 ]
)

registrar(
 "matricula_renovacion",
 nombre="Renovación de matrícula consular",
 categoria="matricula",
 descripcion="Preparación para renovar una matrícula consular.",
 fuente=FUENTES["matricula"],
 preguntas=[
  P("matricula_actual","opciones","¿Tienes tu matrícula consular actual?",True,SI_NO),
  P("cambio_domicilio","opciones","¿Cambió tu domicilio desde que obtuviste la matrícula?",True,SI_NO),
  P("domicilio","opciones","¿Tienes comprobante de tu nuevo domicilio?",False,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste el costo vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "Presentación personal.",
  "Matrícula consular actual.",
  "Si cambió el domicilio, comprobante del nuevo domicilio.",
  "Cita previa.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "matricula_actual":"Matrícula consular actual.",
  "cambio_domicilio":"Confirmación sobre cambio de domicilio.",
  "domicilio":"Comprobante del nuevo domicilio.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación del costo vigente."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 pdf={"titulo":"Renovación de matrícula consular"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["matricula"]}
 ]
)

registrar(
 "matricula_perdida_robo",
 nombre="Matrícula consular perdida o robada",
 categoria="matricula",
 descripcion="Preparación para reportar una matrícula consular perdida o robada.",
 fuente=FUENTES["matricula"],
 preguntas=[
  P("reporte","opciones","¿Ya informaste al Consulado sobre la pérdida o robo?",True,SI_NO),
  P("formulario","opciones","¿Ya completaste la explicación o formulario requerido por el Consulado?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO)
 ],
 requisitos_generales=[
  "Informar la pérdida o robo.",
  "Completar el formulario correspondiente.",
  "Presentación personal.",
  "Cita cuando corresponda.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "reporte":"Reporte de pérdida o robo.",
  "formulario":"Formulario o explicación de las circunstancias.",
  "cita":"Cita para el trámite."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=["El sistema puede requerir el formulario correspondiente antes de emitir una nueva matrícula."],
 pdf={"titulo":"Matrícula consular perdida o robada"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["matricula"]}
 ]
)

registrar(
 "matricula_menor",
 nombre="Matrícula consular para menor de edad",
 categoria="matricula",
 descripcion="Preparación de matrícula consular para una persona menor de 18 años.",
 fuente=FUENTES["matricula"],
 preguntas=[
  P("nacionalidad_menor","opciones","¿Tienes el documento original que acredita la nacionalidad mexicana del menor?",True,SI_NO),
  P("identidad_menor","opciones","¿Tienes la identificación requerida del menor?",True,SI_NO),
  P("domicilio","opciones","¿Tienes comprobante del domicilio?",True,SI_NO),
  P("padres","opciones","¿Pueden presentarse los padres o tutores?",True,SI_NO),
  P("op7","opciones","¿Necesitas autorización del padre o madre que no estará presente?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO),
  P("pago","opciones","¿Ya revisaste el costo vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "El menor debe presentarse.",
  "Documento original de nacionalidad.",
  "Identificación del menor.",
  "Comprobante de domicilio.",
  "Padres o tutores y autorizaciones cuando corresponda.",
  "Cita previa.",
  "Pago vigente."
 ],
 requisitos_mapeados={
  "nacionalidad_menor":"Documento original de nacionalidad del menor.",
  "identidad_menor":"Identificación del menor.",
  "domicilio":"Comprobante de domicilio.",
  "padres":"Presentación de padres o tutores.",
  "op7":"Autorización correspondiente cuando proceda.",
  "cita":"Cita para el trámite.",
  "pago":"Confirmación del costo vigente."
 },
 personas=["menor","padre","madre"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=["La matrícula consular tiene una vigencia de 5 años."],
 pdf={"titulo":"Matrícula consular para menor"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["matricula"]}
 ]
)

registrar(
 "acta_nacimiento_certificada",
 nombre="Copia certificada de acta de nacimiento mexicana",
 categoria="actas",
 descripcion="Preparación para obtener una copia certificada del acta de nacimiento mexicana.",
 fuente=FUENTES["acta"],
 preguntas=[
  P("modalidad","opciones","¿Quieres obtenerla en línea o en el Consulado?",True,["En línea","En el Consulado"]),
  P("identidad","opciones","¿Tienes una identificación oficial que pruebe que eres el titular?",True,SI_NO),
  P("curp","opciones","¿Tienes tu CURP disponible?",False,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",False,SI_NO),
  P("pago","opciones","¿Ya revisaste el costo vigente?",True,SI_NO)
 ],
 requisitos_generales=[
  "Identificación oficial del titular.",
  "Datos del acta.",
  "CURP si está disponible.",
  "Solicitud correspondiente.",
  "Pago aplicable."
 ],
 requisitos_mapeados={
  "identidad":"Identificación oficial del titular.",
  "curp":"CURP, si está disponible.",
  "pago":"Confirmación del costo vigente."
 },
 personas=["adulto"],
 cita={"necesaria":False,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=[
  "La copia certificada también puede consultarse, descargarse e imprimirse en línea mediante el portal oficial.",
  "La tarifa consular de referencia para copia certificada es $20 USD."
 ],
 pdf={"titulo":"Copia certificada de acta de nacimiento mexicana"},
 acciones=[
  {"titulo":"ACTA EN LÍNEA","url":FUENTES["acta_online"]},
  {"titulo":"INFORMACIÓN DEL CONSULADO","url":FUENTES["acta"]}
 ]
)

registrar(
 "doble_nacionalidad",
 nombre="Registro de doble nacionalidad",
 categoria="registro_civil",
 descripcion="Preparación para registrar en México el nacimiento de una persona nacida en el extranjero que puede tener nacionalidad mexicana.",
 fuente=FUENTES["doble_nacionalidad"],
 preguntas=[
  P("persona","opciones","¿La persona que se va a registrar nació fuera de México?",True,SI_NO),
  P("padre_madre_mexicano","opciones","¿Puedes acreditar que uno o ambos padres son mexicanos?",True,SI_NO),
  P("acta_extranjera","opciones","¿Tienes el acta de nacimiento extranjera?",True,SI_NO),
  P("identidades","opciones","¿Tienes las identificaciones requeridas de los padres y de la persona que se registra?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita?",True,SI_NO)
 ],
 requisitos_generales=[
  "Presentación de la persona que se registra.",
  "Presentación de padres cuando corresponda.",
  "Prueba de nacionalidad mexicana del padre o madre mexicano.",
  "Acta de nacimiento extranjera.",
  "Identificaciones requeridas.",
  "Cita previa."
 ],
 requisitos_mapeados={
  "persona":"Presentación de la persona que se registra.",
  "padre_madre_mexicano":"Prueba de nacionalidad mexicana del padre o madre.",
  "acta_extranjera":"Acta de nacimiento extranjera.",
  "identidades":"Identificaciones requeridas.",
  "cita":"Cita para el trámite."
 },
 personas=["menor","padre","madre"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=[
  "El registro de nacimiento puede ser gratuito.",
  "Las copias certificadas pueden tener costo.",
  "Confirma con el Consulado si tu caso requiere documentos adicionales."
 ],
 pdf={"titulo":"Registro de doble nacionalidad"},
 acciones=[
  {"titulo":"AGENDAR CITA","url":FUENTES["citas"]},
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["doble_nacionalidad"]}
 ]
)

registrar(
 "op7",
 nombre="Autorización OP-7",
 categoria="menores",
 descripcion="Preparación relacionada con la autorización de padre o madre para un trámite de un menor.",
 fuente=FUENTES["pasaporte"],
 preguntas=[
  P("menor","opciones","¿La autorización corresponde a un menor de edad?",True,SI_NO),
  P("padre_ausente","opciones","¿El padre o madre que debe autorizar no estará presente?",True,SI_NO),
  P("identidad_padre","opciones","¿Tienes la identificación requerida del padre o madre que autoriza?",True,SI_NO),
  P("cita","opciones","¿Ya confirmaste con el Consulado cómo se realizará la OP-7?",True,SI_NO)
 ],
 requisitos_generales=[
  "Identificación del padre o madre que autoriza.",
  "Procedimiento OP-7 correspondiente.",
  "Confirmación con el Consulado cuando el padre o madre no esté presente."
 ],
 requisitos_mapeados={
  "menor":"Confirmación de que corresponde a un menor.",
  "padre_ausente":"Procedimiento para el padre o madre ausente.",
  "identidad_padre":"Identificación del padre o madre.",
  "cita":"Confirmación del procedimiento OP-7."
 },
 personas=["padre","madre"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["op7"]},
 especiales=[
  "La OP-7 es preparada por personal consular.",
  "Debe revisarse cuidadosamente antes de firmar.",
  "El divorcio o la separación no eliminan por sí solos la patria potestad."
 ],
 pdf={"titulo":"Autorización OP-7"},
 acciones=[
  {"titulo":"CONSULTAR CITA","url":FUENTES["citas"]},
  {"titulo":"INFORMACIÓN OFICIAL","url":FUENTES["pasaporte"]}
 ]
)

registrar(
 "poder_notarial",
 nombre="Poder notarial",
 categoria="notarial",
 descripcion="Preparación inicial para solicitar información sobre un poder notarial.",
 fuente=FUENTES["poderes"],
 preguntas=[
  P("tipo_poder","texto","¿Qué necesitas autorizar mediante el poder?",True),
  P("interesado","opciones","¿Tienes tus datos de identificación disponibles?",True,SI_NO),
  P("cita","opciones","¿Ya tienes una cita o confirmaste el procedimiento?",True,SI_NO)
 ],
 requisitos_generales=[
  "Datos completos de quien otorga el poder.",
  "Información de la persona que recibirá el poder.",
  "Objeto concreto del poder.",
  "Identificación requerida.",
  "Confirmación del procedimiento y cita."
 ],
 requisitos_mapeados={
  "interesado":"Datos e identificación del interesado.",
  "cita":"Confirmación del procedimiento o cita."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=["Los requisitos pueden variar según el tipo de poder. Confirma el caso específico con el Consulado."],
 pdf={"titulo":"Poder notarial"},
 acciones=[
  {"titulo":"PODERES NOTARIALES","url":FUENTES["poderes"]},
  {"titulo":"CONTACTAR AL CONSULADO","url":FUENTES["consulado"]}
 ]
)

registrar(
 "cartilla_militar",
 nombre="Cartilla del Servicio Militar Nacional",
 categoria="militar",
 descripcion="Preparación informativa para la cartilla militar mexicana.",
 fuente=FUENTES["cartilla"],
 preguntas=[
  P("sexo","opciones","¿Eres hombre mexicano?",True,["Sí","No"]),
  P("edad","texto","¿Qué edad tienes?",True),
  P("acta","opciones","¿Tienes copia certificada de tu acta de nacimiento?",True,SI_NO),
  P("domicilio","opciones","¿Tienes comprobante de domicilio?",True,SI_NO),
  P("cita","opciones","¿Ya confirmaste la cita o forma de atención?",True,SI_NO)
 ],
 requisitos_generales=[
  "La obligación del Servicio Militar Nacional para hombres mexicanos comprende las edades establecidas por la normativa.",
  "Acta de nacimiento certificada.",
  "Comprobante de domicilio.",
  "Documentación adicional que corresponda al trámite."
 ],
 requisitos_mapeados={
  "acta":"Copia certificada del acta de nacimiento.",
  "domicilio":"Comprobante de domicilio.",
  "cita":"Confirmación de la atención correspondiente."
 },
 personas=["adulto"],
 cita={"necesaria":True,"url":FUENTES["citas"],"telefono":CONTACTO["citas"]},
 especiales=["El Consulado informa que los mexicanos de sexo masculino de 18 a 40 años tienen obligación relacionada con el Servicio Militar Nacional aun residiendo en el extranjero."],
 pdf={"titulo":"Cartilla del Servicio Militar Nacional"},
 acciones=[
  {"titulo":"REQUISITOS OFICIALES","url":FUENTES["cartilla"]},
  {"titulo":"CITAS","url":FUENTES["citas"]}
 ]
)

registrar(
 "credencial_votar",
 nombre="Credencial para votar desde el extranjero",
 categoria="electoral",
 descripcion="Información inicial sobre la credencial para votar desde el extranjero.",
 fuente=FUENTES["voto"],
 preguntas=[
  P("identidad","opciones","¿Tienes un documento de identidad mexicano?",True,SI_NO),
  P("domicilio","opciones","¿Tienes un comprobante de domicilio?",True,SI_NO),
  P("cita","opciones","¿Ya revisaste cómo realizar el trámite desde el extranjero?",True,SI_NO)
 ],
 requisitos_generales=[
  "Documento de nacionalidad o identidad aceptado.",
  "Identificación correspondiente.",
  "Comprobante de domicilio cuando sea requerido.",
  "Seguir el procedimiento oficial para mexicanos residentes en el extranjero."
 ],
 requisitos_mapeados={
  "identidad":"Documento de identidad o nacionalidad.",
  "domicilio":"Comprobante de domicilio.",
  "cita":"Confirmación del procedimiento oficial."
 },
 personas=["adulto"],
 cita={"necesaria":False,"url":FUENTES["voto"],"telefono":CONTACTO["citas"]},
 especiales=["La credencial para votar no tiene costo según la información oficial del programa para mexicanos en el extranjero."],
 pdf={"titulo":"Credencial para votar desde el extranjero"},
 acciones=[
  {"titulo":"INFORMACIÓN OFICIAL","url":FUENTES["voto"]}
 ]
)

# ============================================================
# DETECCIÓN DE CASOS
# ============================================================

PALABRAS_CASO={
 "pasaporte_primera_vez":[
  "pasaporte por primera vez","primer pasaporte","sacar pasaporte",
  "obtener pasaporte","nuevo pasaporte"
 ],
 "pasaporte_renovacion":[
  "renovar pasaporte","renovacion pasaporte","renovación pasaporte",
  "vencer pasaporte","se me vence el pasaporte"
 ],
 "pasaporte_perdido_robo_mutilado":[
  "perdi el pasaporte","perdí el pasaporte","pasaporte perdido",
  "pasaporte robado","me robaron el pasaporte","pasaporte destruido",
  "pasaporte mutilado"
 ],
 "pasaporte_menor":[
  "pasaporte de mi hijo","pasaporte de mi hija","pasaporte menor",
  "pasaporte para menor","pasaporte niño","pasaporte niña"
 ],
 "pasaporte_naturalizado":[
  "naturalizado","carta de naturalizacion","carta de naturalización"
 ],
 "pasaporte_apellido_matrimonio":[
  "apellido de casada","apellido matrimonio","apellido del esposo",
  "apellido del cónyuge","apellido del conyuge"
 ],
 "pasaporte_acta_extemporanea":[
  "acta extemporanea","acta extemporánea","registro extemporaneo",
  "registro extemporáneo","acta registrada tarde"
 ],
 "matricula_primera_vez":[
  "matricula por primera vez","matrícula por primera vez",
  "primera matricula","primera matrícula"
 ],
 "matricula_renovacion":[
  "renovar matricula","renovar matrícula","renovacion matricula",
  "renovación matrícula"
 ],
 "matricula_perdida_robo":[
  "perdi la matricula","perdí la matrícula","matricula perdida",
  "matrícula perdida","matricula robada","matrícula robada"
 ],
 "matricula_menor":[
  "matricula de mi hijo","matrícula de mi hijo",
  "matricula de mi hija","matrícula para menor"
 ],
 "acta_nacimiento_certificada":[
  "acta de nacimiento","copia certificada","acta certificada"
 ],
 "doble_nacionalidad":[
  "doble nacionalidad","nacido en estados unidos y mexicano",
  "registrar nacimiento","registro nacimiento extranjero"
 ],
 "op7":[
  "op7","op-7","op 7","permiso del padre","permiso de la madre",
  "padre ausente","madre ausente"
 ],
 "poder_notarial":[
  "poder notarial","poder","dar poder","poderes notariales"
 ],
 "cartilla_militar":[
  "cartilla militar","servicio militar","cartilla"
 ],
 "credencial_votar":[
  "credencial para votar","credencial de elector","votar desde el extranjero",
  "credencial votar"
 ]
}

CATEGORIAS={
 "pasaportes":"Pasaportes",
 "matricula":"Matrícula consular",
 "actas":"Actas",
 "registro_civil":"Registro Civil",
 "menores":"Menores",
 "notarial":"Poderes notariales",
 "militar":"Cartilla militar",
 "electoral":"Credencial para votar"
}

def puntuar_caso(s,cid):
    n=normalizar(s)
    puntos=0
    for p in PALABRAS_CASO.get(cid,[]):
        q=normalizar(p)
        if q in n:puntos+=max(1,len(q.split()))
    return puntos

def identificar_caso(s,servicio=""):
    s=texto(s)
    if not s:return ""

    scores={cid:puntuar_caso(s,cid) for cid in CASOS}
    mejor=max(scores,key=scores.get)

    if scores[mejor]>0:return mejor

    n=normalizar(s)

    if "pasaporte" in n:
        if "renovar" in n or "renovacion" in n:return "pasaporte_renovacion"
        if "perdi" in n or "robo" in n:return "pasaporte_perdido_robo_mutilado"
        if "hijo" in n or "hija" in n or "menor" in n:return "pasaporte_menor"
        return "pasaporte_primera_vez"

    if "matricula" in n or "matrícula" in s.lower():
        if "renovar" in n:return "matricula_renovacion"
        if "perdi" in n or "robo" in n:return "matricula_perdida_robo"
        return "matricula_primera_vez"

    if "acta" in n and "nacimiento" in n:
        return "acta_nacimiento_certificada"

    return ""

def normalizar_servicio(s):
    n=normalizar(s)
    if "document" in n:return "documento"
    if "tramite" in n or "cita" in n:return "tramite"
    return n or "tramite"

# ============================================================
# PREGUNTAS
# ============================================================

def obtener_caso(caso):
    return CASOS.get(caso or "")

def _pregunta_aplica(q,respuestas):
    qid=q.get("id","")

    if qid=="domicilio" and respuestas.get("cambio_domicilio") is not None:
        return si(respuestas.get("cambio_domicilio"))

    return True

def pregunta_por_id(caso,qid):
    c=obtener_caso(caso)
    if not c:return None
    for q in c.get("preguntas",[]):
        if q.get("id")==qid:return q
    return None

def siguiente_pregunta(caso,respuestas=None,actual=""):
    c=obtener_caso(caso)
    if not c:return None

    respuestas=respuestas or {}

    for q in c.get("preguntas",[]):
        if not _pregunta_aplica(q,respuestas):
            continue
        if q.get("id") not in respuestas:
            return q

    return None

def pregunta_json(caso,q,respuestas=None):
    if not q:return None
    respuestas=respuestas or {}
    x=deepcopy(q)

    x["paso"]=next(
        (i+1 for i,z in enumerate(
            obtener_caso(caso).get("preguntas",[])
        ) if z.get("id")==q.get("id")),
        1
    )

    total=sum(
        1 for z in obtener_caso(caso).get("preguntas",[])
        if _pregunta_aplica(z,respuestas) or z.get("id") not in respuestas
    )

    x["total"]=max(total,x["paso"])
    return x

# ============================================================
# RESPUESTAS
# ============================================================

def interpretar_respuesta(caso,qid,valor,respuestas=None):
    q=pregunta_por_id(caso,qid)
    if not q:return texto(valor)

    v=texto(valor)

    if q.get("tipo")=="opciones":
        for op in q.get("opciones",[]):
            if normalizar(v)==normalizar(op):
                return op

    return v

# ============================================================
# PERFIL DESDE RESPUESTAS
# ============================================================

def _perfil_desde(respuestas=None,perfil=None):
    p=fusionar(perfil_vacio(),perfil or {})
    r=respuestas or {}

    for k in CAMPOS_PERSONALES:
        if r.get(k) and not p.get(k):
            p[k]=r[k]

    if r.get("nombre") and not p["nombre"]:
        p["nombre"]=r["nombre"]

    return p

# ============================================================
# REQUISITOS
# ============================================================

def evaluar_requisitos(caso,respuestas):
    c=obtener_caso(caso)
    if not c:
        return {"tiene":[],"falta":[],"confirmar":[],"pendientes":[],"obligatorios":[]}

    respuestas=respuestas or {}
    tiene=[];falta=[];confirmar=[];pendientes=[]
    mapa=c.get("requisitos_mapeados",{})

    for q in c.get("preguntas",[]):
        qid=q.get("id")
        if not _pregunta_aplica(q,respuestas):continue
        if qid not in respuestas:continue

        nombre=mapa.get(qid)
        if not nombre:continue

        v=respuestas.get(qid)

        if si(v):tiene.append(nombre)
        elif no(v):falta.append(nombre)
        elif texto(v):confirmar.append(nombre)
        else:pendientes.append(nombre)

    # Si el usuario respondió que el domicilio NO cambió,
    # el comprobante de domicilio de renovación no aplica.
    if caso=="matricula_renovacion" and no(respuestas.get("cambio_domicilio")):
        falta=[x for x in falta if "domicilio" not in normalizar(x)]
        confirmar=[x for x in confirmar if "domicilio" not in normalizar(x)]

    return {
        "tiene":unicos(tiene),
        "falta":unicos(falta),
        "confirmar":unicos(confirmar),
        "pendientes":unicos(pendientes),
        "obligatorios":unicos(c.get("requisitos_generales",[]))
    }

# ============================================================
# DATOS DEL RESULTADO
# ============================================================

def datos_personales(perfil):
    p=fusionar(perfil_vacio(),perfil or {})
    return [
        ("Nombre",pendiente(p.get("nombre"))),
        ("Nacionalidad",pendiente(p.get("nacionalidad"))),
        ("Teléfono",pendiente(p.get("telefono"))),
        ("Dirección",pendiente(p.get("direccion"))),
        ("Estado",pendiente(p.get("estado"))),
        ("ZIP",pendiente(p.get("zip"))),
        ("Correo electrónico",pendiente(p.get("email")))
    ]

def datos_menor(perfil):
    m=(perfil or {}).get("menor") or {}
    if not m:return []
    return [
        ("Nombre",pendiente(m.get("nombre"))),
        ("Fecha de nacimiento",pendiente(m.get("fecha_nacimiento"))),
        ("Lugar de nacimiento",pendiente(m.get("lugar_nacimiento"))),
        ("Nacionalidad",pendiente(m.get("nacionalidad")))
    ]

def datos_padre_madre_tutor(perfil):
    p=(perfil or {}).get("padre_madre_tutor") or {}
    if not p:return []
    return [
        ("Nombre",pendiente(p.get("nombre"))),
        ("Relación",pendiente(p.get("relacion"))),
        ("Teléfono",pendiente(p.get("telefono"))),
        ("Correo",pendiente(p.get("email"))),
        ("Dirección",pendiente(p.get("direccion")))
    ]

def personas_del_caso(caso,respuestas=None,perfil=None):
    c=obtener_caso(caso)
    if not c:return []

    r=[]
    for x in c.get("personas",[]):
        if x=="adulto":r.append("La persona que realiza el trámite.")
        elif x=="menor":r.append("El menor.")
        elif x=="padre":r.append("El padre, cuando corresponda.")
        elif x=="madre":r.append("La madre, cuando corresponda.")
        elif x=="tutor":r.append("El tutor, cuando corresponda.")
    return unicos(r)

def documentos_del_caso(caso,respuestas):
    c=obtener_caso(caso)
    if not c:return []

    r=[]
    r.extend(c.get("documentos_nacionalidad",[]))
    r.extend(c.get("documentos_identidad",[]))
    return unicos(r)

def originales_del_caso(caso):
    c=obtener_caso(caso)
    if not c:return []
    return unicos(
        list(c.get("documentos_nacionalidad",[]))+
        list(c.get("documentos_identidad",[]))
    )

def copias_del_caso(caso):
    if caso=="cartilla_militar":
        return [
            "Copia del acta de nacimiento certificada.",
            "Copia del comprobante de domicilio."
        ]
    return []

# ============================================================
# CITA / PAGO / VIGENCIA / ENTREGA
# ============================================================

def informacion_cita(caso):
    c=obtener_caso(caso)
    if not c:return {}
    return deepcopy(c.get("cita") or {})

def informacion_pago(caso,respuestas=None):
    c=obtener_caso(caso)
    if not c:return {}

    cat=c.get("categoria")

    if cat=="pasaportes":
        return {
            "necesario":True,
            "cantidad":"La tarifa depende de la vigencia elegida.",
            "mensaje":"Confirma la tarifa vigente antes de acudir.",
            "fuente":FUENTES["tarifas"]
        }

    if cat=="matricula":
        return {
            "necesario":True,
            "cantidad":TARIFAS["matricula"],
            "mensaje":"Confirma la tarifa vigente antes de acudir.",
            "fuente":FUENTES["tarifas"]
        }

    if cat=="actas":
        return {
            "necesario":True,
            "cantidad":TARIFAS["acta_certificada"],
            "mensaje":"Confirma la tarifa vigente.",
            "fuente":FUENTES["tarifas"]
        }

    if cat=="electoral":
        return {
            "necesario":False,
            "cantidad":TARIFAS["credencial_votar"],
            "mensaje":"El servicio indicado aparece como gratuito.",
            "fuente":FUENTES["voto"]
        }

    return {
        "necesario":False,
        "cantidad":"",
        "mensaje":"Confirma directamente con la fuente oficial si existe un pago.",
        "fuente":FUENTES["tarifas"]
    }

def vigencia_del_caso(caso,respuestas=None):
    if caso in ("pasaporte_primera_vez","pasaporte_renovacion","pasaporte_naturalizado"):
        return [
            "Menores de 3 años: 1 o 3 años.",
            "De 3 años a menos de 18: 3 o 6 años.",
            "Adultos: 3, 6 o 10 años.",
            "La vigencia de 10 años corresponde a personas adultas."
        ]

    if caso=="pasaporte_menor":
        return [
            "Menores de 3 años: 1 o 3 años.",
            "De 3 años a menos de 18: 3 o 6 años."
        ]

    if caso in ("matricula_primera_vez","matricula_renovacion","matricula_menor"):
        return ["La matrícula consular tiene vigencia de 5 años."]

    return []

def entrega_del_caso(caso):
    if caso in (
        "pasaporte_primera_vez",
        "pasaporte_renovacion",
        "pasaporte_menor"
    ):
        return [
            "La entrega puede realizarse el mismo día cuando el trámite queda aprobado y no existe una falla del sistema.",
            "El tiempo informado puede ser aproximadamente de dos horas, pero es una referencia y no una garantía."
        ]

    if caso in ("matricula_primera_vez","matricula_menor"):
        return [
            "La matrícula puede entregarse el mismo día cuando el trámite es aprobado y no existe una falla del sistema.",
            "El tiempo informado puede ser aproximadamente de dos horas, pero es una referencia y no una garantía."
        ]

    return []

# ============================================================
# SITUACIONES ESPECIALES
# ============================================================

def situaciones_especiales(caso,respuestas):
    r=[]
    respuestas=respuestas or {}

    if caso=="pasaporte_renovacion" and si(respuestas.get("naturalizado")):
        r.append("Al ser mexicano naturalizado, lleva el documento de naturalización original o la copia certificada que corresponda.")

    if caso=="pasaporte_renovacion" and si(respuestas.get("pasaporte_especial")):
        r.append("Los pasaportes de emergencia, protección, restringidos, no canjeables o de un año pueden tener reglas especiales.")

    if caso=="pasaporte_menor":
        if si(respuestas.get("op7")):
            r.append("La autorización OP-7 debe prepararse mediante el procedimiento consular correspondiente y revisarse antes de firmar.")
        r.append("El divorcio o la separación de los padres no elimina por sí sola la patria potestad.")

    if caso=="matricula_menor":
        if si(respuestas.get("op7")):
            r.append("Puede requerirse autorización del padre o madre que no se encuentre presente.")

    if caso=="pasaporte_perdido_robo_mutilado":
        r.append("Después del reporte correspondiente, el trámite puede requerir documentación como una primera expedición.")

    if caso=="pasaporte_acta_extemporanea":
        r.extend([
            "Los registros de nacimiento extemporáneos pueden requerir revisión adicional.",
            "El Consulado puede solicitar documentación complementaria.",
            "La verificación puede retrasar la expedición del pasaporte."
        ])

    if caso=="doble_nacionalidad":
        r.extend([
            "El registro puede ser gratuito.",
            "Las copias certificadas pueden tener costo.",
            "Confirma antes de la cita si tu caso necesita documentos adicionales."
        ])

    if caso=="op7":
        r.extend([
            "La OP-7 es preparada por personal consular.",
            "Revisa cuidadosamente el documento antes de firmarlo."
        ])

    return unicos(r)

# ============================================================
# ACCIONES
# ============================================================

def acciones_del_caso(caso,respuestas=None):
    c=obtener_caso(caso)
    if not c:return []

    r=[{
        "id":"tramite_oficial",
        "tipo":"oficial",
        "titulo":"IR AL TRÁMITE OFICIAL",
        "texto":"Consulta directamente la información oficial de este trámite.",
        "url":c.get("fuente","")
    }]

    for a in c.get("acciones",[]):
        x=deepcopy(a)
        if x.get("url"):r.append(x)

    return r

# ============================================================
# ESTADO
# ============================================================

def calcular_estado(ev):
    if ev.get("falta"):
        return {
            "codigo":"rojo",
            "titulo":"ATENCIÓN: TODAVÍA NO VAYAS",
            "mensaje":"Hay algo importante que todavía te falta."
        }

    if ev.get("confirmar") or ev.get("pendientes"):
        return {
            "codigo":"amarillo",
            "titulo":"TE FALTA CONFIRMAR ALGO",
            "mensaje":"Antes de ir, confirma la información indicada."
        }

    return {
        "codigo":"verde",
        "titulo":"PARECES LISTO",
        "mensaje":"Con las respuestas proporcionadas no aparece un requisito pendiente."
    }

# ============================================================
# RESULTADO
# ============================================================

def resultado(servicio,caso,respuestas=None,perfil=None):
    c=obtener_caso(caso)

    if not c:
        return {
            "tipo":"error",
            "error":"No se encontró el trámite seleccionado."
        }

    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil or {})

    ev=evaluar_requisitos(caso,respuestas)
    estado=calcular_estado(ev)

    return {
        "tipo":"resultado",
        "estado":estado,
        "estado_codigo":estado["codigo"],
        "servicio":servicio,
        "caso":caso,
        "caso_nombre":c.get("nombre",""),
        "descripcion":c.get("descripcion",""),

        "perfil":perfil,
        "datos_personales":datos_personales(perfil),
        "datos_menor":datos_menor(perfil),
        "datos_padre_madre_tutor":datos_padre_madre_tutor(perfil),

        "personas":personas_del_caso(caso,respuestas,perfil),

        "tiene":ev["tiene"],
        "falta":ev["falta"],
        "confirmar":ev["confirmar"],
        "pendientes":ev["pendientes"],
        "obligatorios":ev["obligatorios"],

        "documentos":documentos_del_caso(caso,respuestas),
        "documentos_originales":originales_del_caso(caso),
        "copias":copias_del_caso(caso),

        "especiales":situaciones_especiales(caso,respuestas),
        "acciones":acciones_del_caso(caso,respuestas),

        "cita":informacion_cita(caso),
        "pago":informacion_pago(caso,respuestas),
        "vigencia":vigencia_del_caso(caso,respuestas),
        "entrega":entrega_del_caso(caso),

        "fuente_oficial":c.get("fuente",""),
        "fuentes":deepcopy(FUENTES),
        "respuestas":respuestas,

        "mensaje":estado["mensaje"],

        "instrucciones":(
            ["NO VAYAS TODAVÍA.","Primero completa lo que te falta."]
            if estado["codigo"]=="rojo"
            else
            ["ANTES DE IR, CONFIRMA LA INFORMACIÓN INDICADA."]
            if estado["codigo"]=="amarillo"
            else
            ["PARECES LISTO.","Revisa todo una vez antes de salir."]
        ),

        "boton_oficial":{
            "titulo":"IR AL TRÁMITE OFICIAL",
            "url":c.get("fuente",""),
            "texto":"Consulta directamente la información oficial."
        },

        "pdf":{
            "titulo":(c.get("pdf") or {}).get("titulo","HOJA DE RUTA")
        }
    }

def pantalla_resultado(servicio,caso,respuestas=None,perfil=None):
    return resultado(servicio,caso,respuestas,perfil)

# ============================================================
# INICIAR
# ============================================================

def iniciar(servicio,respuestas=None,texto=""):
    servicio=normalizar_servicio(servicio)
    respuestas=deepcopy(respuestas or {})
    perfil=extraer_perfil(texto)

    if texto:
        caso=identificar_caso(texto,servicio)

        if caso:
            respuestas["_texto_inicial"]=texto
            return seleccionar_caso(
                servicio,
                caso,
                respuestas,
                perfil
            )

    casos=[
        {
            "id":"pasaporte_primera_vez",
            "nombre":"Pasaporte mexicano"
        },
        {
            "id":"matricula_primera_vez",
            "nombre":"Matrícula consular"
        },
        {
            "id":"acta_nacimiento_certificada",
            "nombre":"Acta de nacimiento mexicana"
        },
        {
            "id":"doble_nacionalidad",
            "nombre":"Doble nacionalidad"
        },
        {
            "id":"credencial_votar",
            "nombre":"Credencial para votar"
        },
        {
            "id":"poder_notarial",
            "nombre":"Poder notarial"
        },
        {
            "id":"cartilla_militar",
            "nombre":"Cartilla militar"
        }
    ]

    return {
        "tipo":"seleccion",
        "servicio":servicio,
        "pregunta":"¿Qué trámite necesitas preparar?",
        "texto":"Elige la opción que más se parece a tu situación.",
        "opciones":casos,
        "casos":casos,
        "respuestas":respuestas,
        "perfil":perfil
    }

# ============================================================
# SELECCIONAR CASO
# ============================================================

def seleccionar_caso(servicio,caso,respuestas=None,perfil=None):
    c=obtener_caso(caso)

    if not c:
        caso=identificar_caso(caso,servicio)
        c=obtener_caso(caso)

    if not c:
        return {
            "tipo":"error",
            "error":"No encontramos un trámite con esa información."
        }

    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil or {})

    q=siguiente_pregunta(caso,respuestas)

    if not q:
        return resultado(
            servicio,
            caso,
            respuestas,
            perfil
        )

    return {
        "tipo":"pregunta",
        "servicio":servicio,
        "caso":caso,
        "caso_nombre":c["nombre"],
        "pregunta":pregunta_json(caso,q,respuestas),
        "pregunta_id":q["id"],
        "respuestas":respuestas,
        "perfil":perfil
    }

# ============================================================
# CONTINUAR
# ============================================================

def continuar(servicio,caso,pregunta_id="",texto="",respuestas=None,perfil=None):
    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil or {})
    valor=str(texto or "").strip()

    if pregunta_id and valor:
        respuestas[pregunta_id]=interpretar_respuesta(
            caso,
            pregunta_id,
            valor,
            respuestas
        )

    perfil=extraer_perfil(valor,perfil)

    q=siguiente_pregunta(
        caso,
        respuestas,
        pregunta_id
    )

    if q:
        return {
            "tipo":"pregunta",
            "servicio":servicio,
            "caso":caso,
            "pregunta":pregunta_json(caso,q,respuestas),
            "pregunta_id":q["id"],
            "respuestas":respuestas,
            "perfil":perfil
        }

    return resultado(
        servicio,
        caso,
        respuestas,
        perfil
    )

# ============================================================
# INTERPRETAR
# ============================================================

def interpretar(
    servicio,
    caso="",
    pregunta_id="",
    texto="",
    respuestas=None,
    perfil=None
):
    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil or {})
    valor=str(texto or "").strip()

    if not caso:
        caso=identificar_caso(valor,servicio)

    if not caso:
        return iniciar(
            servicio,
            respuestas,
            valor
        )

    return continuar(
        servicio,
        caso,
        pregunta_id,
        valor,
        respuestas,
        perfil
    )

# ============================================================
# CATALOGO
# ============================================================

def catalogo():
    return [
        {
            "id":cid,
            "nombre":c.get("nombre",""),
            "categoria":c.get("categoria",""),
            "descripcion":c.get("descripcion",""),
            "fuente":c.get("fuente","")
        }
        for cid,c in CASOS.items()
    ]

def obtener_catalogo():
    return catalogo()

def obtener_fuentes():
    return deepcopy(FUENTES)

def obtener_contacto():
    return deepcopy(CONTACTO)

def obtener_tarifas():
    return deepcopy(TARIFAS)

def obtener_manual():
    return deepcopy(CASOS)

# ============================================================
# CONSULTAS COMPATIBLES
# ============================================================

def caso_info(caso):
    c=obtener_caso(caso)
    if not c:return {}
    return {
        "id":caso,
        "nombre":c.get("nombre",""),
        "categoria":c.get("categoria",""),
        "descripcion":c.get("descripcion",""),
        "fuente":c.get("fuente",""),
        "requisitos":c.get("requisitos_generales",[]),
        "acciones":c.get("acciones",[])
    }

def tramite_oficial(caso):
    c=obtener_caso(caso)
    if not c:return {"titulo":"INFORMACIÓN OFICIAL","url":""}
    return {
        "titulo":"IR AL TRÁMITE OFICIAL",
        "url":c.get("fuente",""),
        "texto":"Consulta directamente la información oficial."
    }

def procesar(servicio="",caso="",pregunta_id="",texto="",respuestas=None,perfil=None,accion=""):
    if accion=="resultado":
        return resultado(servicio,caso,respuestas,perfil)
    if accion=="seleccionar_caso":
        return seleccionar_caso(servicio,caso,respuestas,perfil)
    if texto:
        return interpretar(servicio,caso,pregunta_id,texto,respuestas,perfil)
    if caso:
        return continuar(servicio,caso,pregunta_id,"",respuestas,perfil)
    return iniciar(servicio,respuestas,"")

# ============================================================
# VALIDACIÓN
# ============================================================

def validar_manual():
    errores=[]

    for cid,c in CASOS.items():
        if not c.get("nombre"):
            errores.append(f"{cid}: falta nombre")
        if not c.get("categoria"):
            errores.append(f"{cid}: falta categoria")
        if not c.get("fuente"):
            errores.append(f"{cid}: falta fuente oficial")

        ids=set()

        for q in c.get("preguntas",[]):
            qid=q.get("id")

            if not qid:
                errores.append(f"{cid}: pregunta sin id")
                continue

            if qid in ids:
                errores.append(f"{cid}: pregunta repetida {qid}")

            ids.add(qid)

            if not q.get("texto"):
                errores.append(f"{cid}: pregunta {qid} sin texto")

            if q.get("tipo")=="opciones" and not q.get("opciones"):
                errores.append(f"{cid}: opciones vacías en {qid}")

    return {
        "ok":not errores,
        "errores":errores,
        "casos":len(CASOS)
    }

def resumen_manual():
    categorias={}

    for c in CASOS.values():
        cat=c.get("categoria","otros")
        categorias[cat]=categorias.get(cat,0)+1

    return {
        "app":APP,
        "consulado":CONSULADO,
        "motor":"100% determinístico",
        "ia":False,
        "casos":len(CASOS),
        "categorias":categorias
    }

MANUAL_VALIDACION=validar_manual()
MANUAL_RESUMEN=resumen_manual()
