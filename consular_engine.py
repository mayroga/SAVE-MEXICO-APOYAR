# consular_engine.py — MEXICANO APOYA MEXICANO
# MOTOR 100% DETERMINÍSTICO — SIN IA
# PARTE 1/3
import re,unicodedata
from copy import deepcopy

APP="MEXICANO APOYA MEXICANO"
CONSULADO="Consulado de México en Miami"

FUENTES={
 "pasaportes":"https://consulmex.sre.gob.mx/miami/index.php/pasaportes",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
 "identidad":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/dconsular",
 "acta":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
 "doble_nacionalidad":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/doble-nacionalidad",
 "notaria":"https://consulmex.sre.gob.mx/miami/index.php/poderes-notariales",
 "cartilla":"https://consulmex.sre.gob.mx/miami/index.php/cartilla-militar",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "citas":"https://citas.sre.gob.mx",
 "acta_online":"https://www.gob.mx/ActaNacimiento/"
}

CONTACTO={
 "citas":"1-424-309-0009",
 "telefono_general":"786-268-4900",
 "emergencia":"305-979-1534",
 "direccion":"2555 Ponce de Leon Blvd., 4th Floor, Coral Gables, FL 33134",
 "registro_civil":"786-268-4900 ext. 4905 / 4917",
 "notaria":"786-268-4900 ext. 4908",
 "op7":"786-268-4900 ext. 4923 / 4924"
}

TARIFAS={
 "pasaporte_1":"$44 USD",
 "pasaporte_3":"$101 USD",
 "pasaporte_6":"$137 USD",
 "pasaporte_10":"$209 USD",
 "matricula":"$41 USD",
 "acta_certificada":"$20 USD",
 "registro_nacimiento_extranjero":"GRATUITO",
 "credencial_votar":"GRATUITA",
 "acta_matrimonio_certificada":"$20 USD"
}

def normalizar(v):
    if v is None:return ""
    s=str(v).strip().lower()
    s=unicodedata.normalize("NFD",s)
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

def texto(v):
    return "" if v is None else str(v).strip()

def vacio(v):
    if v is None:return True
    if isinstance(v,str):
        return not v.strip() or normalizar(v) in {
            "no se","no se","desconozco","desconocido",
            "pendiente","pendiente de completar","n/a","na"
        }
    return False

def si(v):
    return normalizar(v) in {
        "si","sí","s","tengo","ya tengo","lo tengo",
        "correcto","correcta","cuenta","puedo","puedo hacerlo"
    }

def no(v):
    return normalizar(v) in {
        "no","n","no tengo","no cuento","me falta",
        "no lo tengo","no la tengo"
    }

def unicos(items):
    r=[]
    for x in items or []:
        x=texto(x)
        if x and x not in r:r.append(x)
    return r

def lista(v):
    if isinstance(v,list):return [texto(x) for x in v if texto(x)]
    return []

def fusionar(a,b):
    r=deepcopy(a or {})
    for k,v in (b or {}).items():
        if isinstance(v,dict):
            r[k]=fusionar(r.get(k) or {},v)
        elif not vacio(v):
            r[k]=v
    return r

def buscar(texto_usuario,*palabras):
    t=normalizar(texto_usuario)
    return any(normalizar(p) in t for p in palabras)

def edad_menor(v):
    try:return int(v)<18
    except:return False

def pendiente(v):
    return texto(v) or "PENDIENTE DE COMPLETAR"

def opcion(id_,texto_,valor=None):
    return {
        "id":id_,
        "texto":texto_,
        "valor":valor if valor is not None else id_
    }

# ============================================================
# DATOS PERSONALES
# ============================================================

CAMPOS_PERSONALES={
 "nombre":"Nombre",
 "apellido_paterno":"Apellido paterno",
 "apellido_materno":"Apellido materno",
 "nacionalidad":"Nacionalidad",
 "tipo_nacionalidad":"Tipo de nacionalidad mexicana",
 "fecha_nacimiento":"Fecha de nacimiento",
 "lugar_nacimiento":"Lugar de nacimiento",
 "telefono":"Teléfono",
 "email":"Correo electrónico",
 "direccion":"Dirección",
 "ciudad":"Ciudad",
 "estado":"Estado",
 "zip":"ZIP",
 "curp":"CURP"
}

CAMPOS_MENOR={
 "nombre":"Nombre del menor",
 "apellido_paterno":"Apellido paterno del menor",
 "apellido_materno":"Apellido materno del menor",
 "fecha_nacimiento":"Fecha de nacimiento del menor",
 "lugar_nacimiento":"Lugar de nacimiento del menor",
 "nacionalidad":"Nacionalidad del menor"
}

CAMPOS_PADRE={
 "nombre":"Nombre del padre/madre/tutor",
 "relacion":"Relación con el menor",
 "telefono":"Teléfono",
 "email":"Correo electrónico",
 "direccion":"Dirección"
}

def perfil_vacio():
    return {
        "nombre":"",
        "apellido_paterno":"",
        "apellido_materno":"",
        "nacionalidad":"",
        "tipo_nacionalidad":"",
        "fecha_nacimiento":"",
        "lugar_nacimiento":"",
        "telefono":"",
        "email":"",
        "direccion":"",
        "ciudad":"",
        "estado":"",
        "zip":"",
        "curp":"",
        "menor":{},
        "padre_madre_tutor":{},
        "personas":[]
    }

# ============================================================
# DOCUMENTOS DE IDENTIDAD ACEPTABLES
# ============================================================

IDENTIDADES_ACEPTABLES=[
 "Matrícula Consular de Alta Seguridad",
 "INE",
 "Cartilla del Servicio Militar Nacional",
 "Cédula profesional o título profesional",
 "Documento de nacionalidad mexicana que contenga fotografía",
 "Licencia de conducir mexicana con medidas de seguridad",
 "Licencia de conducir de Estados Unidos",
 "Identificación oficial del gobierno de Estados Unidos",
 "Tarjeta de Residente Permanente de Estados Unidos",
 "Certificado o constancia escolar con fotografía y sello",
 "Identificación institucional mexicana con fotografía"
]

PRUEBAS_NACIONALIDAD=[
 "Acta de nacimiento mexicana",
 "Certificado de nacionalidad mexicana",
 "Declaración de nacionalidad mexicana",
 "Carta de naturalización",
 "Matrícula Consular de Alta Seguridad expedida después de 2005"
]

# ============================================================
# CATÁLOGO PRINCIPAL DE PROCEDIMIENTOS
# ============================================================

CASOS={}

def registrar(caso):
    CASOS[caso["id"]]=caso
    return caso

# ------------------------------------------------------------
# PASAPORTE — PRIMERA VEZ ADULTO
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_primera_vez",
 "categoria":"pasaportes",
 "nombre":"Pasaporte mexicano — primera vez",
 "descripcion":"Preparación para solicitar por primera vez un pasaporte mexicano.",
 "fuente":FUENTES["pasaportes"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "requisitos_generales":[
    "Presentarse personalmente.",
    "Tener cita.",
    "Acreditar la nacionalidad mexicana.",
    "Presentar identificación oficial con fotografía.",
    "Cubrir la tarifa vigente."
 ],
 "documentos_nacionalidad":PRUEBAS_NACIONALIDAD,
 "documentos_identidad":IDENTIDADES_ACEPTABLES,
 "preguntas":[
    {
     "id":"nacionalidad",
     "texto":"¿Tienes un documento que pruebe que eres mexicano?",
     "tipo":"si_no",
     "campo":"nacionalidad",
     "required":True,
     "permite_otro":True,
     "ayuda":"Puede ser, por ejemplo, tu acta de nacimiento mexicana o carta de naturalización."
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación con fotografía?",
     "tipo":"si_no",
     "campo":"identidad",
     "required":True,
     "permite_otro":True,
     "ayuda":"La identificación debe corresponder a los documentos aceptados por el Consulado."
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "campo":"cita",
     "required":True,
     "ayuda":"La cita se realiza por el sistema oficial correspondiente."
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "campo":"pago",
     "required":True,
     "ayuda":"La cantidad depende de la vigencia del pasaporte. Confirma siempre la tarifa vigente."
    }
 ],
 "requisitos_mapeados":{
    "nacionalidad":"Documento original que acredita nacionalidad mexicana",
    "identidad":"Identificación oficial aceptable con fotografía",
    "cita":"Cita para el trámite",
    "pago":"Pago de la tarifa correspondiente"
 },
 "acciones":[
    {
     "id":"agendar_cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Si todavía no tienes cita, entra al sistema oficial.",
     "url":FUENTES["citas"]
    },
    {
     "id":"ver_requisitos",
     "tipo":"fuente",
     "titulo":"VER TRÁMITE OFICIAL",
     "texto":"Consulta directamente los requisitos oficiales de pasaporte.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"ver_tarifa",
     "tipo":"tarifa",
     "titulo":"VER TARIFAS",
     "texto":"Consulta la tarifa vigente antes de acudir.",
     "url":FUENTES["tarifas"]
    }
 ],
 "especiales":[
    "Si no tienes identificación con fotografía, puede existir una alternativa específica de constancia de identidad. Debe confirmarse según tu caso.",
    "Si eres mexicano por naturalización, revisa los requisitos específicos para naturalizados."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — PASAPORTE MEXICANO",
    "secciones":["datos_personales","tramite","personas","requisitos","documentos","cita","pago","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# PASAPORTE — RENOVACIÓN
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_renovacion",
 "categoria":"pasaportes",
 "nombre":"Renovación de pasaporte mexicano",
 "descripcion":"Preparación para renovar un pasaporte mexicano.",
 "fuente":FUENTES["pasaportes"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "requisitos_generales":[
    "Presentarse personalmente.",
    "Tener cita.",
    "Presentar el pasaporte que se desea renovar.",
    "Cubrir la tarifa vigente."
 ],
 "preguntas":[
    {
     "id":"pasaporte_actual",
     "texto":"¿Tienes contigo el pasaporte que vas a renovar?",
     "tipo":"si_no",
     "required":True,
     "permite_otro":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"naturalizado",
     "texto":"¿Eres mexicano por naturalización?",
     "tipo":"si_no",
     "required":True,
     "ayuda":"Si eres naturalizado, puede ser necesario presentar tu carta de naturalización original o copia certificada según el caso."
    },
    {
     "id":"pasaporte_especial",
     "texto":"¿Tu pasaporte anterior fue de emergencia, protección, restringido, no canjeable o tiene alguna situación especial?",
     "tipo":"si_no",
     "required":False,
     "ayuda":"Los pasaportes con situaciones especiales pueden requerir un procedimiento diferente."
    }
 ],
 "requisitos_mapeados":{
    "pasaporte_actual":"Pasaporte que se desea renovar",
    "cita":"Cita para renovación",
    "pago":"Pago de la tarifa correspondiente"
 },
 "acciones":[
    {
     "id":"agendar_cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Agenda o confirma tu cita oficial.",
     "url":FUENTES["citas"]
    },
    {
     "id":"tramite_oficial",
     "tipo":"fuente",
     "titulo":"VER RENOVACIÓN OFICIAL",
     "texto":"Consulta directamente la información oficial.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"tarifas",
     "tipo":"tarifa",
     "titulo":"VER TARIFAS",
     "texto":"Consulta la tarifa vigente.",
     "url":FUENTES["tarifas"]
    }
 ],
 "especiales":[
    "Los pasaportes mexicanos por naturalización pueden requerir documentación adicional.",
    "Pasaportes antiguos pueden requerir documentación de primera vez.",
    "Un pasaporte de un año no necesariamente puede renovarse como una renovación ordinaria.",
    "Pasaportes de emergencia, protección, restringidos o no canjeables pueden requerir revisión especial."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — RENOVACIÓN DE PASAPORTE",
    "secciones":["datos_personales","tramite","personas","requisitos","documentos","cita","pago","especiales","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# PASAPORTE — PÉRDIDA / ROBO / MUTILACIÓN
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_perdido_robo_mutilado",
 "categoria":"pasaportes",
 "nombre":"Pasaporte perdido, robado, destruido o mutilado",
 "descripcion":"Preparación para solicitar un nuevo pasaporte después de pérdida, robo, destrucción o mutilación.",
 "fuente":FUENTES["pasaportes"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"situacion_pasaporte",
     "texto":"¿Qué pasó con tu pasaporte?",
     "tipo":"opciones",
     "required":True,
     "opciones":[
        opcion("perdido","Lo perdí"),
        opcion("robado","Me lo robaron"),
        opcion("destruido","Se destruyó"),
        opcion("mutilado","Está mutilado o dañado")
     ]
    },
    {
     "id":"reporte",
     "texto":"¿Ya tienes el reporte o constancia de la autoridad correspondiente?",
     "tipo":"si_no",
     "required":True,
     "ayuda":"Para pérdida, robo, destrucción o mutilación puede ser necesario acreditar lo ocurrido ante la autoridad correspondiente."
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"nacionalidad",
     "texto":"¿Tienes un documento original que pruebe tu nacionalidad mexicana?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación con fotografía?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "reporte":"Reporte o constancia correspondiente",
    "cita":"Cita",
    "nacionalidad":"Documento que acredita nacionalidad mexicana",
    "identidad":"Identificación oficial con fotografía"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER TRÁMITE OFICIAL",
     "texto":"Consulta el procedimiento oficial para tu situación.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial de citas.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "La pérdida, robo, destrucción o mutilación puede llevar a requisitos de primera vez.",
    "La situación concreta debe revisarse con la información oficial."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — PASAPORTE PERDIDO, ROBADO O DAÑADO",
    "secciones":["datos_personales","tramite","situacion","requisitos","documentos","cita","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# PASAPORTE — MENOR
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_menor",
 "categoria":"pasaportes",
 "nombre":"Pasaporte mexicano para menor de edad",
 "descripcion":"Preparación para tramitar pasaporte mexicano de una persona menor de 18 años.",
 "fuente":FUENTES["pasaportes"],
 "personas":["menor","padre","madre","tutor"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"nacionalidad_menor",
     "texto":"¿Tienes el documento que prueba que el menor es mexicano?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad_menor",
     "texto":"¿Tienes la identificación del menor que corresponda a los requisitos?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"padres",
     "texto":"¿Pueden presentarse los padres o las personas que legalmente deben autorizar el trámite?",
     "tipo":"si_no",
     "required":True,
     "ayuda":"La presencia y autorización dependen de la situación familiar y legal."
    },
    {
     "id":"op7",
     "texto":"¿Necesitas realizar un OP-7 porque uno de los padres no estará presente?",
     "tipo":"si_no",
     "required":False,
     "ayuda":"El OP-7 se utiliza en situaciones específicas de autorización de menores."
    },
    {
     "id":"identidades_padres",
     "texto":"¿Tienes las identificaciones de los padres o tutores que deben intervenir?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "nacionalidad_menor":"Documento original de nacionalidad mexicana del menor",
    "identidad_menor":"Documento de identidad del menor",
    "padres":"Presencia/autorización de quienes deban intervenir",
    "identidades_padres":"Identificaciones de padres/tutores",
    "cita":"Cita",
    "pago":"Pago correspondiente"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER PASAPORTE PARA MENOR",
     "texto":"Consulta directamente la información oficial.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Entra al sistema oficial de citas.",
     "url":FUENTES["citas"]
    },
    {
     "id":"op7",
     "tipo":"op7",
     "titulo":"INFORMACIÓN SOBRE OP-7",
     "texto":"Si un padre no puede acudir, revisa primero cómo debe hacerse la autorización.",
     "url":FUENTES["pasaportes"]
    }
 ],
 "especiales":[
    "Para menores de edad y solteros deben intervenir las personas que legalmente correspondan.",
    "La separación o divorcio por sí sola no elimina la patria potestad.",
    "En determinados casos puede intervenir una autoridad judicial.",
    "El personal consular prepara los formatos OP-5 u OP-7 que correspondan para revisión y firma."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — PASAPORTE DE MENOR",
    "secciones":["datos_personales","menor","padre_madre_tutor","tramite","requisitos","documentos","op7","cita","pago","especiales","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# PASAPORTE — NATURALIZADO
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_naturalizado",
 "categoria":"pasaportes",
 "nombre":"Pasaporte mexicano para persona naturalizada",
 "descripcion":"Preparación del caso de una persona que adquirió la nacionalidad mexicana por naturalización.",
 "fuente":FUENTES["pasaportes"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"carta_naturalizacion",
     "texto":"¿Tienes tu carta de naturalización mexicana original o el documento que corresponda?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación oficial con fotografía?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "carta_naturalizacion":"Carta de naturalización o documento correspondiente",
    "identidad":"Identificación oficial",
    "cita":"Cita",
    "pago":"Pago"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER PASAPORTE OFICIAL",
     "texto":"Consulta la información oficial para naturalizados.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial de citas.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "La carta de naturalización es especialmente importante para acreditar la nacionalidad mexicana por naturalización.",
    "En determinados casos puede requerirse original o copia certificada."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — PASAPORTE DE PERSONA NATURALIZADA",
    "secciones":["datos_personales","tramite","requisitos","documentos","cita","pago","especiales","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# PASAPORTE — APELLIDO POR MATRIMONIO
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_apellido_matrimonio",
 "categoria":"pasaportes",
 "nombre":"Pasaporte y apellido por matrimonio",
 "descripcion":"Preparación de documentación relacionada con apellido del cónyuge.",
 "fuente":FUENTES["pasaportes"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"acta_matrimonio",
     "texto":"¿Tienes el acta de matrimonio que corresponda?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pasaporte",
     "texto":"¿Tienes el pasaporte o documento que estás tramitando?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "acta_matrimonio":"Acta de matrimonio",
    "pasaporte":"Documento/pasaporte correspondiente",
    "cita":"Cita"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER INFORMACIÓN OFICIAL",
     "texto":"Consulta cómo se manejan los nombres y apellidos.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "El pasaporte conserva los nombres y apellidos correspondientes y el apellido del cónyuge se maneja en el apartado establecido para ello."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — PASAPORTE Y MATRIMONIO",
    "secciones":["datos_personales","tramite","documentos","cita","especiales","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# ACTA EXTEMPORÁNEA
# ------------------------------------------------------------

registrar({
 "id":"pasaporte_acta_extemporanea",
 "categoria":"pasaportes",
 "nombre":"Pasaporte con acta de nacimiento extemporánea",
 "descripcion":"Caso especial cuando el registro de nacimiento fue realizado fuera de los periodos ordinarios.",
 "fuente":FUENTES["pasaportes"],
 "personas":["adulto","menor"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "periodos_extemporaneos":{
    "antes_1931":"hasta 50 años después del nacimiento",
    "1931_1940":"hasta 30 años después",
    "1941_1950":"hasta 10 años después",
    "1951_1976":"hasta 5 años después",
    "1977_en_adelante":"hasta 1 año después"
 },
 "preguntas":[
    {
     "id":"fecha_nacimiento",
     "texto":"¿Sabes tu fecha de nacimiento?",
     "tipo":"texto",
     "required":True
    },
    {
     "id":"fecha_registro",
     "texto":"¿Sabes aproximadamente cuándo fue registrada tu acta de nacimiento?",
     "tipo":"texto",
     "required":True
    },
    {
     "id":"acta",
     "texto":"¿Tienes el acta de nacimiento mexicana?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "acta":"Acta de nacimiento mexicana",
    "cita":"Cita"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER CASOS ESPECIALES DE PASAPORTE",
     "texto":"Consulta la información oficial.",
     "url":FUENTES["pasaportes"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "Si el registro se realizó fuera del periodo correspondiente, pueden solicitarse pruebas complementarias.",
    "El Consulado puede realizar verificaciones electrónicas o por escrito.",
    "La verificación puede retrasar la expedición del pasaporte."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — ACTA EXTEMPORÁNEA",
    "secciones":["datos_personales","tramite","fechas","requisitos","documentos","cita","especiales","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# MATRÍCULA CONSULAR — PRIMERA VEZ
# ------------------------------------------------------------

registrar({
 "id":"matricula_primera_vez",
 "categoria":"matricula",
 "nombre":"Matrícula consular — primera vez",
 "descripcion":"Preparación para obtener por primera vez una matrícula consular.",
 "fuente":FUENTES["matricula"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"nacionalidad",
     "texto":"¿Tienes un documento que pruebe que eres mexicano?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación con fotografía?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"domicilio",
     "texto":"¿Tienes un comprobante de domicilio a tu nombre con la dirección completa?",
     "tipo":"si_no",
     "required":True,
     "ayuda":"Si el comprobante no está a tu nombre, existen situaciones en las que pueden aceptarse alternativas."
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "nacionalidad":"Documento original de nacionalidad mexicana",
    "identidad":"Identificación con fotografía",
    "domicilio":"Comprobante de domicilio con dirección completa",
    "cita":"Cita",
    "pago":"Pago de matrícula"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER MATRÍCULA CONSULAR",
     "texto":"Consulta directamente el trámite oficial.",
     "url":FUENTES["matricula"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    },
    {
     "id":"tarifa",
     "tipo":"tarifa",
     "titulo":"VER TARIFA",
     "texto":"Consulta la tarifa vigente.",
     "url":FUENTES["tarifas"]
    }
 ],
 "especiales":[
    "Si el comprobante de domicilio no está a tu nombre, existen alternativas dependiendo de la relación con la persona cuyo nombre aparece en el comprobante."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — MATRÍCULA CONSULAR",
    "secciones":["datos_personales","tramite","requisitos","documentos","domicilio","cita","pago","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# MATRÍCULA — RENOVACIÓN
# ------------------------------------------------------------

registrar({
 "id":"matricula_renovacion",
 "categoria":"matricula",
 "nombre":"Renovación de matrícula consular",
 "descripcion":"Preparación para renovar una matrícula consular.",
 "fuente":FUENTES["matricula"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"matricula_actual",
     "texto":"¿Tienes tu matrícula consular actual?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cambio_domicilio",
     "texto":"¿Cambió tu domicilio desde que obtuviste tu matrícula?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"domicilio",
     "texto":"¿Tienes comprobante de tu nuevo domicilio?",
     "tipo":"si_no",
     "required":False
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "matricula_actual":"Matrícula consular actual",
    "domicilio":"Comprobante de domicilio cuando corresponda",
    "cita":"Cita",
    "pago":"Pago"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER RENOVACIÓN DE MATRÍCULA",
     "texto":"Consulta el procedimiento oficial.",
     "url":FUENTES["matricula"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "Si cambió tu residencia, el comprobante de domicilio vuelve a ser importante.",
    "Si no cambió tu domicilio, revisa la información oficial sobre la documentación que corresponde."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — RENOVACIÓN DE MATRÍCULA CONSULAR",
    "secciones":["datos_personales","tramite","documentos","domicilio","cita","pago","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# MATRÍCULA — PÉRDIDA / ROBO
# ------------------------------------------------------------

registrar({
 "id":"matricula_perdida_robo",
 "categoria":"matricula",
 "nombre":"Matrícula consular perdida o robada",
 "descripcion":"Preparación para reponer una matrícula consular perdida o robada.",
 "fuente":FUENTES["matricula"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"situacion",
     "texto":"¿Perdiste o te robaron tu matrícula?",
     "tipo":"opciones",
     "required":True,
     "opciones":[
        opcion("perdida","La perdí"),
        opcion("robo","Me la robaron")
     ]
    },
    {
     "id":"formulario",
     "texto":"¿Estás preparado para explicar al Consulado lo que ocurrió?",
     "tipo":"si_no",
     "required":True,
     "ayuda":"El Consulado indica que debe llenarse un formulario explicando las circunstancias."
    },
    {
     "id":"nacionalidad",
     "texto":"¿Tienes un documento que pruebe tu nacionalidad mexicana?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación con fotografía?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"domicilio",
     "texto":"¿Tienes comprobante de domicilio?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "formulario":"Formulario sobre la pérdida o robo",
    "nacionalidad":"Documento de nacionalidad mexicana",
    "identidad":"Identificación con fotografía",
    "domicilio":"Comprobante de domicilio",
    "cita":"Cita"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER MATRÍCULA PERDIDA O ROBADA",
     "texto":"Consulta el procedimiento oficial.",
     "url":FUENTES["matricula"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "La reposición por pérdida o robo requiere explicar las circunstancias en el formulario correspondiente."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — MATRÍCULA PERDIDA O ROBADA",
    "secciones":["datos_personales","tramite","situacion","requisitos","documentos","cita","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# MATRÍCULA — MENOR
# ------------------------------------------------------------

registrar({
 "id":"matricula_menor",
 "categoria":"matricula",
 "nombre":"Matrícula consular para menor",
 "descripcion":"Preparación de matrícula consular para una persona menor de edad.",
 "fuente":FUENTES["matricula"],
 "personas":["menor","padre","madre","tutor"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"nacionalidad_menor",
     "texto":"¿Tienes el documento que prueba que el menor es mexicano?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad_menor",
     "texto":"¿Tienes el documento de identidad del menor?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"padres",
     "texto":"¿Pueden presentarse las personas que deben autorizar el trámite?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidades_padres",
     "texto":"¿Tienes las identificaciones de los padres o tutores?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar la tarifa correspondiente?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "nacionalidad_menor":"Documento de nacionalidad mexicana del menor",
    "identidad_menor":"Identificación del menor",
    "padres":"Autorización/presencia de quienes correspondan",
    "identidades_padres":"Identificaciones de padres/tutores",
    "cita":"Cita",
    "pago":"Pago"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER MATRÍCULA PARA MENOR",
     "texto":"Consulta el procedimiento oficial.",
     "url":FUENTES["matricula"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "Para menores de edad se requiere la intervención de los padres o tutores que legalmente correspondan.",
    "Si uno de los padres no puede acudir, debe revisarse el procedimiento de autorización correspondiente.",
    "La separación o divorcio por sí sola no elimina la patria potestad."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — MATRÍCULA DE MENOR",
    "secciones":["datos_personales","menor","padre_madre_tutor","tramite","requisitos","documentos","cita","pago","especiales","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# ACTA DE NACIMIENTO MEXICANA — COPIA CERTIFICADA
# ------------------------------------------------------------

registrar({
 "id":"acta_nacimiento_certificada",
 "categoria":"actas",
 "nombre":"Copia certificada de acta de nacimiento mexicana",
 "descripcion":"Obtención de copia certificada de un acta de nacimiento mexicana.",
 "fuente":FUENTES["acta"],
 "personas":["adulto","menor"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"titular",
     "texto":"¿La copia del acta es para ti?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación oficial que pruebe la identidad del titular?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"curp",
     "texto":"¿Tienes la CURP del titular, si la conoces?",
     "tipo":"si_no",
     "required":False,
     "ayuda":"La CURP puede ser útil si está disponible."
    },
    {
     "id":"cita",
     "texto":"¿Ya sabes cómo vas a obtener el acta?",
     "tipo":"opciones",
     "required":True,
     "opciones":[
        opcion("consulado","En el Consulado"),
        opcion("internet","Por Internet")
     ]
    },
    {
     "id":"pago",
     "texto":"¿Estás preparado para pagar si eliges la copia certificada con costo?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "identidad":"Identificación oficial",
    "curp":"CURP si está disponible",
    "cita":"Procedimiento de obtención seleccionado",
    "pago":"Pago correspondiente"
 },
 "acciones":[
    {
     "id":"consulado",
     "tipo":"fuente",
     "titulo":"VER ACTA EN EL CONSULADO",
     "texto":"Consulta los requisitos oficiales.",
     "url":FUENTES["acta"]
    },
    {
     "id":"online",
     "tipo":"tramite",
     "titulo":"OBTENER ACTA POR INTERNET",
     "texto":"Puedes consultar, descargar e imprimir tu acta certificada en el portal oficial.",
     "url":FUENTES["acta_online"]
    },
    {
     "id":"tarifa",
     "tipo":"tarifa",
     "titulo":"VER TARIFA",
     "texto":"Consulta la tarifa vigente.",
     "url":FUENTES["tarifas"]
    }
 ],
 "especiales":[
    "La copia certificada del acta de nacimiento mexicana puede obtenerse también por Internet mediante el portal oficial.",
    "El acta descargada del portal oficial tiene validez legal."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — ACTA DE NACIMIENTO MEXICANA",
    "secciones":["datos_personales","tramite","titular","requisitos","documentos","forma_obtencion","pago","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# DOBLE NACIONALIDAD / REGISTRO DE NACIMIENTO
# ------------------------------------------------------------

registrar({
 "id":"doble_nacionalidad",
 "categoria":"registro_civil",
 "nombre":"Registro de nacimiento por doble nacionalidad",
 "descripcion":"Preparación para registrar como mexicano a una persona nacida en el extranjero cuando corresponde.",
 "fuente":FUENTES["doble_nacionalidad"],
 "personas":["menor","adulto","padre","madre"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"nacido_extranjero",
     "texto":"¿La persona nació fuera de México?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"padre_madre_mexicano",
     "texto":"¿Uno de sus padres es mexicano?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"acta_extranjera",
     "texto":"¿Tienes el acta de nacimiento extranjera?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"nacionalidad_padre",
     "texto":"¿Tienes el documento que prueba la nacionalidad mexicana del padre o madre?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidades",
     "texto":"¿Tienes las identificaciones de las personas que deben presentarse?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "acta_extranjera":"Acta de nacimiento extranjera",
    "nacionalidad_padre":"Documento que acredita nacionalidad mexicana del padre/madre",
    "identidades":"Identificaciones correspondientes",
    "cita":"Cita"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER DOBLE NACIONALIDAD",
     "texto":"Consulta los requisitos oficiales del Registro Civil.",
     "url":FUENTES["doble_nacionalidad"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"AGENDAR CITA",
     "texto":"Consulta cómo solicitar la cita.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "El registro de nacimiento en el extranjero es diferente de solicitar una copia certificada de un acta mexicana ya existente.",
    "El registro de nacimiento es gratuito; las copias certificadas pueden tener tarifa.",
    "El Consulado puede solicitar documentación adicional según el caso."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — DOBLE NACIONALIDAD",
    "secciones":["datos_personales","persona_registrada","padres","tramite","requisitos","documentos","cita","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# OP-7
# ------------------------------------------------------------

registrar({
 "id":"op7",
 "categoria":"menores",
 "nombre":"OP-7 — autorización para menor",
 "descripcion":"Preparación informativa para una autorización consular relacionada con un menor.",
 "fuente":FUENTES["pasaportes"],
 "personas":["menor","padre","madre","tutor"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"menor",
     "texto":"¿La autorización es para un menor de 18 años?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"padre_ausente",
     "texto":"¿Uno de los padres no puede presentarse?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes la identificación de la persona que realizará la autorización?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"datos_menor",
     "texto":"¿Tienes los datos y documentos del menor?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "identidad":"Identificación de quien realiza la autorización",
    "datos_menor":"Datos y documentos del menor"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER INFORMACIÓN OFICIAL OP-7",
     "texto":"Consulta la información oficial antes de firmar.",
     "url":FUENTES["pasaportes"]
    }
 ],
 "especiales":[
    "El personal consular prepara el formato que corresponda.",
    "La persona debe revisar cuidadosamente los datos antes de firmar.",
    "La separación o divorcio por sí sola no elimina la patria potestad.",
    "Los casos de patria potestad o autorización judicial pueden requerir documentación específica."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — OP-7",
    "secciones":["datos_personales","menor","padre_madre_tutor","tramite","documentos","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# PODERES / NOTARÍA
# ------------------------------------------------------------

registrar({
 "id":"poder_notarial",
 "categoria":"notaria",
 "nombre":"Poder notarial",
 "descripcion":"Preparación inicial para servicios de fe pública y poderes notariales.",
 "fuente":FUENTES["notaria"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"tipo_poder",
     "texto":"¿Sabes qué necesitas autorizar?",
     "tipo":"texto",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación oficial vigente?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya tienes cita?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "identidad":"Identificación oficial",
    "cita":"Cita",
    "tipo_poder":"Información sobre el poder que se necesita"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER PODERES Y NOTARÍA",
     "texto":"Consulta directamente la información oficial.",
     "url":FUENTES["notaria"]
    },
    {
     "id":"cita",
     "tipo":"cita",
     "titulo":"CONSULTAR CITA",
     "texto":"Consulta el sistema oficial.",
     "url":FUENTES["citas"]
    }
 ],
 "especiales":[
    "El tipo de poder determina la documentación y condiciones aplicables.",
    "No debe asumirse que todos los poderes requieren exactamente los mismos documentos."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — PODER NOTARIAL",
    "secciones":["datos_personales","tramite","tipo_poder","requisitos","documentos","cita","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# CARTILLA MILITAR
# ------------------------------------------------------------

registrar({
 "id":"cartilla_militar",
 "categoria":"cartilla",
 "nombre":"Cartilla del Servicio Militar Nacional",
 "descripcion":"Preparación informativa para el trámite de cartilla militar en el Consulado.",
 "fuente":FUENTES["cartilla"],
 "personas":["adulto"],
 "cita":{
    "necesaria":True,
    "url":FUENTES["citas"],
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"edad",
     "texto":"¿Tienes entre 18 y 40 años?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"acta",
     "texto":"¿Tienes copia certificada de tu acta de nacimiento mexicana y copia?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"domicilio",
     "texto":"¿Tienes comprobante de domicilio y copia?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"cita",
     "texto":"¿Ya sabes cómo debes presentarte para el trámite?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "edad":"Edad dentro del rango aplicable",
    "acta":"Acta de nacimiento certificada y copia",
    "domicilio":"Comprobante de domicilio y copia",
    "cita":"Preparación para presentación"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER CARTILLA MILITAR",
     "texto":"Consulta directamente los requisitos oficiales.",
     "url":FUENTES["cartilla"]
    }
 ],
 "especiales":[
    "El Consulado indica la obligación del Servicio Militar Nacional para mexicanos varones de 18 a 40 años, incluso viviendo en el extranjero.",
    "Debe revisarse la situación particular antes de acudir."
 ],
 "pdf":{
    "titulo":"HOJA DE RUTA — CARTILLA MILITAR",
    "secciones":["datos_personales","tramite","requisitos","documentos","cita","acciones","fuente"]
 }
})

# ------------------------------------------------------------
# CREDENCIAL PARA VOTAR
# ------------------------------------------------------------

registrar({
 "id":"credencial_votar",
 "categoria":"electoral",
 "nombre":"Credencial para votar desde el extranjero",
 "descripcion":"Preparación informativa para obtener o actualizar la credencial para votar desde el extranjero.",
 "fuente":"https://www.votoextranjero.mx/",
 "personas":["adulto"],
 "cita":{
    "necesaria":False,
    "telefono":CONTACTO["citas"]
 },
 "preguntas":[
    {
     "id":"nacionalidad",
     "texto":"¿Tienes un documento que pruebe tu nacionalidad mexicana?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"identidad",
     "texto":"¿Tienes una identificación aceptable?",
     "tipo":"si_no",
     "required":True
    },
    {
     "id":"domicilio",
     "texto":"¿Tienes un comprobante de domicilio?",
     "tipo":"si_no",
     "required":True
    }
 ],
 "requisitos_mapeados":{
    "nacionalidad":"Documento de nacionalidad mexicana",
    "identidad":"Identificación aceptable",
    "domicilio":"Comprobante de domicilio"
 },
 "acciones":[
    {
     "id":"tramite",
     "tipo":"fuente",
     "titulo":"VER CREDENCIAL PARA VOTAR",
     "texto":"Consulta la información oficial.",
     "url":"https://www.votoextranjero.mx/"
    }
 ],
 "especiales":[],
 "pdf":{
    "titulo":"HOJA DE RUTA — CREDENCIAL PARA VOTAR",
    "secciones":["datos_personales","tramite","requisitos","documentos","acciones","fuente"]
 }
})

# ============================================================
# ALIAS / CATEGORÍAS PARA RECONOCER LO QUE ESCRIBE EL CLIENTE
# ============================================================

PALABRAS_CASO={
 "pasaporte_renovacion":[
    "renovar pasaporte","renovacion pasaporte","renuevo pasaporte",
    "renovar mi pasaporte","pasaporte vencido","pasaporte por vencer"
 ],
 "pasaporte_primera_vez":[
    "sacar pasaporte","primer pasaporte","primera vez pasaporte",
    "pasaporte por primera vez","quiero mi pasaporte"
 ],
 "pasaporte_perdido_robo_mutilado":[
    "perdi mi pasaporte","perdi el pasaporte","pasaporte perdido",
    "me robaron el pasaporte","pasaporte robado",
    "pasaporte roto","pasaporte mutilado","pasaporte destruido"
 ],
 "pasaporte_menor":[
    "pasaporte de mi hijo","pasaporte de mi hija","pasaporte menor",
    "pasaporte para mi hijo","pasaporte para mi hija",
    "pasaporte niño","pasaporte niña","pasaporte menor de edad"
 ],
 "pasaporte_naturalizado":[
    "soy naturalizado","naturalizacion","carta de naturalizacion",
    "mexicano naturalizado"
 ],
 "pasaporte_apellido_matrimonio":[
    "apellido de casada","apellido por matrimonio","apellido del esposo",
    "apellido del conyuge","pasaporte matrimonio","casada y pasaporte"
 ],
 "pasaporte_acta_extemporanea":[
    "acta extemporanea","registro extemporaneo",
    "me registraron tarde","acta registrada tarde",
    "nacimiento extemporaneo"
 ],
 "matricula_renovacion":[
    "renovar matricula","renovacion matricula",
    "renovar mi matricula","matricula vencida"
 ],
 "matricula_primera_vez":[
    "sacar matricula","matricula por primera vez",
    "primera matricula","quiero matricula"
 ],
 "matricula_perdida_robo":[
    "perdi la matricula","matricula perdida",
    "me robaron la matricula","matricula robada"
 ],
 "matricula_menor":[
    "matricula de mi hijo","matricula de mi hija",
    "matricula para menor","matricula menor",
    "matricula niño","matricula niña"
 ],
 "acta_nacimiento_certificada":[
    "acta de nacimiento","copia del acta","acta certificada",
    "sacar acta","necesito mi acta","acta mexicana"
 ],
 "doble_nacionalidad":[
    "doble nacionalidad","registrar a mi hijo mexicano",
    "registrar nacimiento extranjero","nacio en estados unidos",
    "nacio en usa y quiero hacerlo mexicano",
    "nacido en el extranjero","registro de nacimiento"
 ],
 "op7":[
    "op7","op-7","op 7","permiso del padre","permiso de la madre",
    "padre no puede ir","madre no puede ir","autorizacion menor"
 ],
 "poder_notarial":[
    "poder notarial","poder","notaria","notario",
    "dar poder","mandar poder a mexico"
 ],
 "cartilla_militar":[
    "cartilla militar","cartilla","servicio militar",
    "servicio militar nacional","smn"
 ],
 "credencial_votar":[
    "credencial para votar","credencial de elector",
    "votar","credencial ine","ine desde estados unidos"
 ]
}

# ============================================================
# CATEGORÍAS PARA LA PRIMERA PANTALLA
# ============================================================

CATEGORIAS=[
 {
  "id":"pasaportes",
  "texto":"PASAPORTE",
  "ayuda":"Primera vez, renovación, menor, pérdida, robo y otros casos."
 },
 {
  "id":"matricula",
  "texto":"MATRÍCULA CONSULAR",
  "ayuda":"Primera vez, renovación, menor, pérdida o robo."
 },
 {
  "id":"actas",
  "texto":"ACTA DE NACIMIENTO",
  "ayuda":"Copia certificada de un acta mexicana."
 },
 {
  "id":"registro_civil",
  "texto":"DOBLE NACIONALIDAD",
  "ayuda":"Registro de nacimiento de una persona nacida fuera de México."
 },
 {
  "id":"menores",
  "texto":"OP-7 / TRÁMITES DE MENORES",
  "ayuda":"Autorizaciones y situaciones relacionadas con menores."
 },
 {
  "id":"notaria",
  "texto":"PODERES / NOTARÍA",
  "ayuda":"Servicios notariales y poderes."
 },
 {
  "id":"cartilla",
  "texto":"CARTILLA MILITAR",
  "ayuda":"Servicio Militar Nacional."
 },
 {
  "id":"electoral",
  "texto":"CREDENCIAL PARA VOTAR",
  "ayuda":"Información para mexicanos en el extranjero."
 }
]

# ============================================================
# FRASES PREESCRITAS — SIN IA
# ============================================================

MENSAJES={
 "bienvenida":"Te voy a ayudar a preparar tu trámite paso por paso.",
 "no_entendido":"No te preocupes. Elige una de las opciones que aparecen en la pantalla.",
 "faltante":"Todavía te falta algo antes de ir.",
 "listo":"PARECES LISTO",
 "atencion":"ATENCIÓN: TODAVÍA NO VAYAS",
 "confirmar":"HAY ALGO QUE DEBES CONFIRMAR",
 "sin_datos":"Todavía no tenemos ese dato.",
 "guardar":"Esta información se usará para preparar tu hoja de ruta.",
 "oficial":"Aquí puedes consultar directamente la información oficial de tu trámite.",
 "cita":"Si tu trámite necesita cita, aquí tienes el acceso oficial.",
 "tarifa":"La tarifa puede cambiar. Confirma siempre el importe vigente antes de acudir.",
 "no_inventar":"Si un dato no está confirmado, te lo vamos a señalar. No vamos a inventarlo.",
 "pdf":"Tu hoja de ruta reúne tu información, lo que ya tienes, lo que te falta y lo que debes hacer."
}

# ============================================================
# PREGUNTAS GENERALES DE APOYO
# ============================================================

PREGUNTAS_GENERALES={
 "nombre":{
   "id":"nombre",
   "texto":"¿Cuál es tu nombre?",
   "tipo":"texto",
   "campo":"nombre",
   "required":False
 },
 "telefono":{
   "id":"telefono",
   "texto":"¿Cuál es tu número de teléfono?",
   "tipo":"texto",
   "campo":"telefono",
   "required":False
 },
 "email":{
   "id":"email",
   "texto":"¿Cuál es tu correo electrónico?",
   "tipo":"texto",
   "campo":"email",
   "required":False
 },
 "direccion":{
   "id":"direccion",
   "texto":"¿Cuál es tu dirección?",
   "tipo":"texto",
   "campo":"direccion",
   "required":False
 },
 "estado":{
   "id":"estado",
   "texto":"¿En qué estado vives?",
   "tipo":"texto",
   "campo":"estado",
   "required":False
 },
 "zip":{
   "id":"zip",
   "texto":"¿Cuál es tu ZIP?",
   "tipo":"texto",
   "campo":"zip",
   "required":False
 }
}

# ============================================================
# FIN DE LA PARTE 1
# La PARTE 2 contendrá:
# - extracción determinística de datos
# - identificación del trámite
# - selección de caso
# - manejo de preguntas
# - memoria de respuestas
# - menores/padres/tutores
# - reglas de requisitos
# - estados VERDE / AMARILLO / ROJO
# - acciones
# ============================================================

# ============================================================
# consular_engine.py — PARTE 2/3
# MOTOR DETERMINÍSTICO — SIN IA
# ============================================================

# ============================================================
# EXTRACCIÓN DETERMINÍSTICA DE DATOS PERSONALES
# ============================================================

def limpiar_nombre(v):
    v=re.sub(r"\s+"," ",texto(v)).strip(" .,:;")
    return v

def extraer_email(t):
    m=re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+",t,re.I)
    return m.group(0).strip() if m else ""

def extraer_telefono(t):
    patrones=[
        r"(?:tel[eé]fono|telefono|celular|cel|m[oó]vil|movil|phone)\s*(?:es|:|-)?\s*(\+?1?[\s().-]*\d[\d\s().-]{7,}\d)",
        r"(\+?1[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
        r"(\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4})"
    ]
    for p in patrones:
        m=re.search(p,t,re.I)
        if m:return re.sub(r"\s+"," ",m.group(1)).strip()
    return ""

def extraer_zip(t):
    m=re.search(r"\b\d{5}(?:-\d{4})?\b",t)
    return m.group(0) if m else ""

def extraer_email_y_telefono(t):
    return {
        "email":extraer_email(t),
        "telefono":extraer_telefono(t),
        "zip":extraer_zip(t)
    }

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
 "West Virginia","Wisconsin","Wyoming","District of Columbia"
]

ESTADOS_MX=[
 "Aguascalientes","Baja California","Baja California Sur","Campeche",
 "Chiapas","Chihuahua","Coahuila","Colima","Durango","Guanajuato",
 "Guerrero","Hidalgo","Jalisco","Mexico","Estado de México",
 "Michoacan","Michoacán","Morelos","Nayarit","Nuevo Leon","Nuevo León",
 "Oaxaca","Puebla","Queretaro","Querétaro","Quintana Roo",
 "San Luis Potosi","San Luis Potosí","Sinaloa","Sonora","Tabasco",
 "Tamaulipas","Tlaxcala","Veracruz","Yucatan","Yucatán","Zacatecas"
]

def extraer_estado(t):
    n=normalizar(t)
    for e in ESTADOS_USA+ESTADOS_MX:
        if normalizar(e) in n:
            return e
    return ""

def extraer_nombre(t):
    patrones=[
        r"(?:me llamo|mi nombre es|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]{3,80})",
        r"(?:nombre)\s*(?:es|:)\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]{3,80})"
    ]
    for p in patrones:
        m=re.search(p,t,re.I)
        if m:
            v=limpiar_nombre(m.group(1))
            v=re.split(
                r"\b(?:soy|vivo|resido|tengo|quiero|necesito|naci|nací|telefono|teléfono|correo|email|mi)\b",
                v,1,flags=re.I
            )[0].strip(" ,.;")
            if len(v.split())>=2:return v
    return ""

def extraer_direccion(t):
    patrones=[
        r"(?:vivo en|resido en|mi direccion es|mi dirección es|domicilio es|domicilio:)\s+(.+?)(?=(?:\b(?:telefono|teléfono|celular|correo|email|zip|c[oó]digo postal)\b)|$)"
    ]
    for p in patrones:
        m=re.search(p,t,re.I)
        if m:
            v=limpiar_nombre(m.group(1))
            return v.strip(" ,.;")
    return ""

def extraer_fecha(t):
    patrones=[
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
    ]
    for p in patrones:
        m=re.search(p,t)
        if m:return m.group(0)
    return ""

def extraer_nacionalidad(t):
    n=normalizar(t)
    if "naturalizado" in n or "naturalizada" in n:
        return "Mexicana por naturalización"
    if "naci en mexico" in n or "nacido en mexico" in n or "nacida en mexico" in n:
        return "Mexicana por nacimiento"
    if "mexicano" in n or "mexicana" in n:
        return "Mexicana"
    return ""

def extraer_parentesco(t):
    n=normalizar(t)
    if "mi hijo" in n or "mi hijo menor" in n:return "Padre/madre de menor"
    if "mi hija" in n or "mi hija menor" in n:return "Padre/madre de menor"
    if "mi nieto" in n or "mi nieta" in n:return "Familiar del menor"
    if "tutor" in n:return "Tutor"
    if "padre" in n:return "Padre"
    if "madre" in n:return "Madre"
    return ""

def extraer_perfil(t,perfil=None):
    t=texto(t)
    p=fusionar(perfil_vacio(),perfil or {})
    if not t:return p

    datos=extraer_email_y_telefono(t)

    nombre=extraer_nombre(t)
    if nombre:p["nombre"]=nombre

    if datos["email"]:p["email"]=datos["email"]
    if datos["telefono"]:p["telefono"]=datos["telefono"]
    if datos["zip"]:p["zip"]=datos["zip"]

    estado=extraer_estado(t)
    if estado:p["estado"]=estado

    direccion=extraer_direccion(t)
    if direccion:p["direccion"]=direccion

    nac=extraer_nacionalidad(t)
    if nac:
        p["nacionalidad"]="Mexicana"
        p["tipo_nacionalidad"]=nac

    fecha=extraer_fecha(t)
    if fecha:p["fecha_nacimiento"]=fecha

    parentesco=extraer_parentesco(t)
    if parentesco:
        p["padre_madre_tutor"]["relacion"]=parentesco

    n=normalizar(t)

    if "curp" in n:
        m=re.search(r"\b[A-Z]{4}\d{6}[A-Z]{6}[A-Z0-9]\d\b",t,re.I)
        if m:p["curp"]=m.group(0).upper()

    # Datos explícitos del menor
    if any(x in n for x in [
        "mi hijo","mi hija","mi hijo menor","mi hija menor",
        "para mi hijo","para mi hija"
    ]):
        p["menor"]["relacion"]="hijo/hija"
        if nombre:
            p["menor"]["nombre"]=nombre

    return p

# ============================================================
# IDENTIFICACIÓN DEL CASO
# ============================================================

def puntuar_caso(t,caso_id):
    n=normalizar(t)
    palabras=PALABRAS_CASO.get(caso_id,[])
    puntos=0
    for palabra in palabras:
        q=normalizar(palabra)
        if q in n:
            puntos+=max(1,len(q.split()))
    return puntos

def identificar_caso(t,servicio=""):
    t=texto(t)
    if not t:return ""

    candidatos=[]

    for caso_id in CASOS:
        p=puntuar_caso(t,caso_id)
        if p:
            candidatos.append((p,caso_id))

    if not candidatos:
        return ""

    candidatos.sort(key=lambda x:(x[0],len(x[1])),reverse=True)
    return candidatos[0][1]

def casos_de_categoria(categoria):
    return [
        c for c in CASOS.values()
        if c.get("categoria")==categoria
    ]

def catalogo(servicio=""):
    servicio=normalizar(servicio)

    if servicio in ("cita","documento",""):
        return [
            {
                "id":x["id"],
                "texto":x["texto"],
                "ayuda":x.get("ayuda","")
            } for x in CATEGORIAS
        ]

    r=[]
    for c in casos_de_categoria(servicio):
        r.append({
            "id":c["id"],
            "texto":c["nombre"],
            "ayuda":c.get("descripcion","")
        })
    return r

# ============================================================
# NORMALIZACIÓN DE SERVICIO
# ============================================================

def normalizar_servicio(servicio):
    n=normalizar(servicio)

    if n in ("cita","documento",""):
        return n

    equivalencias={
        "pasaporte":"pasaportes",
        "pasaportes":"pasaportes",
        "matricula":"matricula",
        "matricula consular":"matricula",
        "acta":"actas",
        "actas":"actas",
        "acta nacimiento":"actas",
        "doble nacionalidad":"registro_civil",
        "registro civil":"registro_civil",
        "op7":"menores",
        "op 7":"menores",
        "notaria":"notaria",
        "notaria y poderes":"notaria",
        "poder":"notaria",
        "cartilla":"cartilla",
        "cartilla militar":"cartilla",
        "electoral":"electoral",
        "credencial":"electoral"
    }
    return equivalencias.get(n,n)

# ============================================================
# PERFIL DESDE RESPUESTAS
# ============================================================

def _perfil_desde(respuestas=None,perfil=None):
    p=fusionar(perfil_vacio(),perfil or {})
    r=respuestas or {}

    for campo in CAMPOS_PERSONALES:
        if campo in r and not vacio(r[campo]):
            p[campo]=r[campo]

    if isinstance(r.get("menor"),dict):
        p["menor"]=fusionar(p.get("menor") or {},r["menor"])

    if isinstance(r.get("padre_madre_tutor"),dict):
        p["padre_madre_tutor"]=fusionar(
            p.get("padre_madre_tutor") or {},
            r["padre_madre_tutor"]
        )

    return p

def guardar_respuesta(respuestas,pregunta_id,valor):
    r=deepcopy(respuestas or {})
    if not pregunta_id:return r

    if isinstance(valor,dict):
        r[pregunta_id]=fusionar(r.get(pregunta_id) or {},valor)
    elif not vacio(valor):
        r[pregunta_id]=valor

    return r

# ============================================================
# ENCONTRAR CASO
# ============================================================

def obtener_caso(caso):
    if not caso:return None
    return CASOS.get(caso)

def pregunta_por_id(caso,pregunta_id):
    c=obtener_caso(caso)
    if not c:return None

    for q in c.get("preguntas",[]):
        if q.get("id")==pregunta_id:
            return q
    return None

def primera_pregunta(caso):
    c=obtener_caso(caso)
    if not c:return None

    preguntas=c.get("preguntas",[])
    return preguntas[0] if preguntas else None

def siguiente_pregunta(caso,respuestas=None,pregunta_actual_id=""):
    c=obtener_caso(caso)
    if not c:return None

    respuestas=respuestas or {}
    preguntas=c.get("preguntas",[])

    empezar=0

    if pregunta_actual_id:
        for i,q in enumerate(preguntas):
            if q.get("id")==pregunta_actual_id:
                empezar=i+1
                break

    # Buscar primero una pregunta posterior que todavía no esté contestada.
    for q in preguntas[empezar:]:
        qid=q.get("id")
        if qid not in respuestas or vacio(respuestas.get(qid)):
            if _pregunta_aplica(q,respuestas):
                return q

    # Por si una respuesta anterior creó una pregunta pendiente.
    for q in preguntas:
        qid=q.get("id")
        if qid not in respuestas or vacio(respuestas.get(qid)):
            if _pregunta_aplica(q,respuestas):
                return q

    return None

def _pregunta_aplica(q,respuestas):
    qid=q.get("id","")

    # La pregunta de comprobante de domicilio para renovación
    # solamente es necesaria si el domicilio cambió.
    if qid=="domicilio" and "cambio_domicilio" in (respuestas or {}):
        return si(respuestas.get("cambio_domicilio"))

    # Preguntas relacionadas con OP-7
    if qid=="op7" and "padres" in (respuestas or {}):
        return True

    return True

# ============================================================
# OPCIONES DE UNA PREGUNTA
# ============================================================

def opciones_pregunta(q):
    if not q:return []

    if q.get("tipo")=="si_no":
        return [
            opcion("si","SÍ"),
            opcion("no","NO")
        ]

    if q.get("tipo")=="opciones":
        return q.get("opciones",[])

    return []

# ============================================================
# REPRESENTACIÓN DE UNA PREGUNTA
# ============================================================

def pregunta_json(caso,q,respuestas=None):
    if not q:return {}

    opciones=opciones_pregunta(q)

    return {
        "tipo":"pregunta",
        "servicio":CASOS.get(caso,{}).get("categoria",""),
        "caso":caso,
        "caso_nombre":CASOS.get(caso,{}).get("nombre",""),
        "pregunta_id":q.get("id",""),
        "pregunta":q.get("texto",""),
        "tipo_pregunta":q.get("tipo","texto"),
        "tipo":q.get("tipo","texto"),
        "opciones":opciones,
        "required":bool(q.get("required",False)),
        "permite_otro":q.get("permite_otro",False),
        "ayuda":q.get("ayuda",""),
        "respuestas":respuestas or {}
    }

# ============================================================
# RESPUESTAS A PREGUNTAS
# ============================================================

def interpretar_respuesta(q,valor):
    if not q:return valor

    tipo=q.get("tipo","texto")
    v=texto(valor)

    if tipo=="si_no":
        n=normalizar(v)
        if n in ("si","s","yes","y","tengo","ya tengo"):
            return "si"
        if n in ("no","n","no tengo","me falta"):
            return "no"

    if tipo=="opciones":
        for op in q.get("opciones",[]):
            if isinstance(op,dict):
                if normalizar(v) in {
                    normalizar(op.get("id","")),
                    normalizar(op.get("texto","")),
                    normalizar(op.get("valor",""))
                }:
                    return op.get("id") or op.get("valor")
            elif normalizar(v)==normalizar(op):
                return op

    return v

# ============================================================
# EXTRAER DATOS SIN USAR LA FRASE COMO RESPUESTA UNIVERSAL
# ============================================================

def responde_pregunta_con_texto(q,t):
    if not q or not texto(t):
        return None

    n=normalizar(t)
    qid=q.get("id","")

    if q.get("tipo")=="si_no":
        positivos=[
            "si","sí","si tengo","sí tengo","ya tengo",
            "lo tengo","la tengo","los tengo","puedo","correcto"
        ]
        negativos=[
            "no","no tengo","no lo tengo","no la tengo",
            "me falta","no puedo"
        ]

        for x in positivos:
            if re.search(r"\b"+re.escape(normalizar(x))+r"\b",n):
                return "si"

        for x in negativos:
            if re.search(r"\b"+re.escape(normalizar(x))+r"\b",n):
                return "no"

    if qid=="nacionalidad":
        if "naturalizado" in n or "naturalizada" in n:
            return "si"
        if "mexicano" in n or "mexicana" in n:
            return "si"

    if qid in ("nacionalidad_menor","nacionalidad_padre"):
        if "mexicano" in n or "mexicana" in n:
            return "si"

    if qid=="cita" and ("tengo cita" in n or "ya tengo cita" in n):
        return "si"

    if qid=="cita" and ("no tengo cita" in n or "sin cita" in n):
        return "no"

    if qid=="pago" and ("ya pague" in n or "ya pagué" in n):
        return "si"

    if qid=="identidad":
        if "licencia" in n or "ine" in n or "matricula" in n:
            return "si"

    if qid=="pasaporte_actual":
        if "tengo mi pasaporte" in n or "tengo el pasaporte" in n:
            return "si"

    if qid=="matricula_actual":
        if "tengo mi matricula" in n or "tengo la matricula" in n:
            return "si"

    return None

# ============================================================
# ENRIQUECER UNA RESPUESTA
# ============================================================

def enriquecer_respuesta(respuestas,pregunta_id,valor,texto_original=""):
    r=guardar_respuesta(respuestas,pregunta_id,valor)

    # El texto completo sirve para extraer información personal,
    # pero NO se copia automáticamente a todas las respuestas.
    if texto_original:
        r["_texto_libre_ultimo"]=texto(texto_original)

    return r

# ============================================================
# IDENTIFICACIÓN AUTOMÁTICA DESDE UN TEXTO LARGO
# ============================================================

def analizar_texto_inicial(texto_usuario,servicio="",respuestas=None,perfil=None):
    t=texto(texto_usuario)
    r=deepcopy(respuestas or {})
    p=_perfil_desde(r,perfil)

    # Primero extraemos información personal.
    p=extraer_perfil(t,p)

    # Después buscamos el caso.
    caso=identificar_caso(t,servicio)

    # Si todavía no aparece un caso específico, intentamos por servicio.
    if not caso:
        s=normalizar_servicio(servicio)
        posibles=casos_de_categoria(s)
        if len(posibles)==1:
            caso=posibles[0]["id"]

    # Finalmente intentamos responder SOLO la pregunta que corresponda.
    if caso:
        q=primera_pregunta(caso)
        if q:
            v=responde_pregunta_con_texto(q,t)
            if v is not None:
                r=enriquecer_respuesta(r,q.get("id"),v,t)

    return {
        "caso":caso,
        "respuestas":r,
        "perfil":p,
        "texto":t
    }

# ============================================================
# INICIO DEL SERVICIO
# ============================================================

def iniciar(servicio,respuestas=None,texto=""):
    servicio=normalizar_servicio(servicio)
    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas)

    if texto:
        analisis=analizar_texto_inicial(
            texto,
            servicio,
            respuestas,
            perfil
        )
        respuestas=analisis["respuestas"]
        perfil=analisis["perfil"]
        caso=analisis["caso"]

        if caso:
            q=siguiente_pregunta(caso,respuestas)
            if q:
                return pregunta_json(caso,q,respuestas)

            return resultado(
                servicio,
                caso,
                respuestas,
                perfil
            )

    if servicio in ("cita","documento",""):
        return {
            "tipo":"seleccion_servicio",
            "servicio":servicio,
            "opciones":CATEGORIAS,
            "respuestas":respuestas,
            "perfil":perfil
        }

    casos=casos_de_categoria(servicio)

    if len(casos)==1:
        caso=casos[0]["id"]
        q=siguiente_pregunta(caso,respuestas)
        if q:return pregunta_json(caso,q,respuestas)
        return resultado(servicio,caso,respuestas,perfil)

    return {
        "tipo":"seleccion_caso",
        "servicio":servicio,
        "opciones":[
            {
                "id":c["id"],
                "texto":c["nombre"],
                "ayuda":c.get("descripcion","")
            } for c in casos
        ],
        "respuestas":respuestas,
        "perfil":perfil
    }

# ============================================================
# SELECCIONAR CASO
# ============================================================

def seleccionar_caso(
    servicio,
    caso,
    respuestas=None,
    perfil=None
):
    # Compatibilidad con llamadas antiguas:
    # seleccionar_caso(servicio,caso,respuestas,perfil)
    if isinstance(respuestas,str) and isinstance(perfil,dict):
        pass

    servicio=normalizar_servicio(servicio)
    c=obtener_caso(caso)

    if not c:
        return {
            "tipo":"error",
            "error":"No se encontró el trámite seleccionado."
        }

    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil)

    q=siguiente_pregunta(caso,respuestas)

    if q:
        return pregunta_json(caso,q,respuestas)

    return resultado(
        servicio,
        caso,
        respuestas,
        perfil
    )

# ============================================================
# CONTINUAR — MOTOR PRINCIPAL DE PREGUNTAS
# ============================================================

def continuar(
    servicio,
    caso,
    pregunta_id="",
    texto="",
    respuestas=None,
    perfil=None
):
    # Compatibilidad con llamadas donde el tercer argumento
    # puede haber sido enviado como diccionario.
    if isinstance(pregunta_id,dict):
        if respuestas is None:
            respuestas=pregunta_id
        pregunta_id=""

    servicio=normalizar_servicio(servicio)
    c=obtener_caso(caso)

    if not c:
        return {
            "tipo":"error",
            "error":"No se encontró el trámite."
        }

    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil)

    q=pregunta_por_id(caso,pregunta_id)

    # Si llega texto libre, primero intenta responder
    # exclusivamente la pregunta actual.
    valor=responde_pregunta_con_texto(q,texto) if q else None

    if valor is None and texto:
        if q and q.get("tipo")=="texto":
            valor=texto(texto)
        elif q and q.get("tipo")=="opciones":
            valor=interpretar_respuesta(q,texto)
        elif q and q.get("tipo")=="si_no":
            valor=None

    if q and valor is not None:
        respuestas=enriquecer_respuesta(
            respuestas,
            pregunta_id,
            valor,
            texto
        )

    # Siempre aprovechamos información personal contenida
    # en el texto, sin convertirla en respuesta de otras preguntas.
    if texto:
        perfil=extraer_perfil(texto,perfil)

    siguiente=siguiente_pregunta(
        caso,
        respuestas,
        pregunta_id
    )

    if siguiente:
        j=pregunta_json(caso,siguiente,respuestas)
        j["perfil"]=perfil
        return j

    return resultado(
        servicio,
        caso,
        respuestas,
        perfil
    )

# ============================================================
# INTERPRETAR — ENTRADA LIBRE
# ============================================================

def interpretar(
    servicio,
    caso="",
    pregunta_id="",
    texto="",
    respuestas=None,
    perfil=None
):
    servicio=normalizar_servicio(servicio)
    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil)

    if not texto:
        if caso:
            q=siguiente_pregunta(caso,respuestas,pregunta_id)
            if q:
                j=pregunta_json(caso,q,respuestas)
                j["perfil"]=perfil
                return j
            return resultado(servicio,caso,respuestas,perfil)

        return iniciar(servicio,respuestas)

    # Si ya conocemos el caso, NO lo volvemos a cambiar
    # salvo que el texto contenga una selección explícita.
    if caso and caso in CASOS:
        perfil=extraer_perfil(texto,perfil)

        q=pregunta_por_id(caso,pregunta_id)

        valor=responde_pregunta_con_texto(q,texto)

        if valor is not None:
            respuestas=enriquecer_respuesta(
                respuestas,
                pregunta_id,
                valor,
                texto
            )

        siguiente=siguiente_pregunta(
            caso,
            respuestas,
            pregunta_id
        )

        if siguiente:
            j=pregunta_json(caso,siguiente,respuestas)
            j["perfil"]=perfil
            return j

        return resultado(
            servicio,
            caso,
            respuestas,
            perfil
        )

    # No conocemos todavía el caso.
    analisis=analizar_texto_inicial(
        texto,
        servicio,
        respuestas,
        perfil
    )

    caso=analisis["caso"]
    respuestas=analisis["respuestas"]
    perfil=analisis["perfil"]

    if caso:
        q=siguiente_pregunta(caso,respuestas)

        if q:
            j=pregunta_json(caso,q,respuestas)
            j["perfil"]=perfil
            return j

        return resultado(
            servicio,
            caso,
            respuestas,
            perfil
        )

    # No inventamos el trámite.
    return {
        "tipo":"seleccion_caso",
        "servicio":servicio,
        "opciones":catalogo(servicio),
        "respuestas":respuestas,
        "perfil":perfil,
        "mensaje":MENSAJES["no_entendido"]
    }

# ============================================================
# INFORMACIÓN DEL CASO
# ============================================================

def caso_info(caso):
    c=obtener_caso(caso)
    if not c:return {}

    return {
        "id":c["id"],
        "categoria":c.get("categoria",""),
        "nombre":c.get("nombre",""),
        "descripcion":c.get("descripcion",""),
        "fuente":c.get("fuente",""),
        "personas":c.get("personas",[]),
        "cita":c.get("cita",{}),
        "requisitos_generales":c.get("requisitos_generales",[]),
        "documentos_nacionalidad":c.get("documentos_nacionalidad",[]),
        "documentos_identidad":c.get("documentos_identidad",[]),
        "especiales":c.get("especiales",[]),
        "acciones":c.get("acciones",[]),
        "pdf":c.get("pdf",{})
    }

# ============================================================
# FIN DE LA PARTE 2
#
# LA PARTE 3 CONTENDRÁ:
# - evaluación de requisitos
# - qué ya tiene el cliente
# - qué le falta realmente
# - qué debe confirmar
# - estados VERDE / AMARILLO / ROJO
# - personas y datos para PDF
# - acciones finales
# - resultado completo
# - compatibilidad con app.py
# - funciones auxiliares finales
# ============================================================

# ============================================================
# consular_engine.py — PARTE 3/3
# RESULTADOS, REQUISITOS, ACCIONES Y COMPATIBILIDAD
# ============================================================

# ============================================================
# REQUISITOS: NO CONFUNDIR "REQUISITO GENERAL" CON "FALTA"
# ============================================================

def estado_respuesta(valor):
    if si(valor):
        return "tiene"
    if no(valor):
        return "falta"
    if vacio(valor):
        return "pendiente"
    return "confirmar"

def requisito_nombre(caso,pregunta_id):
    c=obtener_caso(caso)
    if not c:return ""

    return texto(
        (c.get("requisitos_mapeados") or {}).get(pregunta_id)
    )

def evaluar_requisitos(caso,respuestas):
    c=obtener_caso(caso)
    if not c:
        return {
            "tiene":[],
            "falta":[],
            "confirmar":[],
            "pendientes":[],
            "obligatorios":[]
        }

    respuestas=respuestas or {}

    tiene=[]
    falta=[]
    confirmar=[]
    pendientes=[]

    mapeados=c.get("requisitos_mapeados") or {}

    for q in c.get("preguntas",[]):
        qid=q.get("id","")

        # Una pregunta opcional no se convierte automáticamente
        # en una obligación.
        if not q.get("required",False) and qid not in respuestas:
            continue

        # Algunas preguntas pueden no aplicar.
        if not _pregunta_aplica(q,respuestas):
            continue

        valor=respuestas.get(qid)

        # Si existe un requisito explícito asociado,
        # lo evaluamos.
        nombre=mapeados.get(qid)

        if nombre:
            e=estado_respuesta(valor)

            if e=="tiene":
                tiene.append(nombre)
            elif e=="falta":
                falta.append(nombre)
            elif e=="confirmar":
                confirmar.append(nombre)
            else:
                pendientes.append(nombre)

    # Requisitos generales son información del trámite.
    # NO se convierten automáticamente en "faltantes".
    obligatorios=unicos(c.get("requisitos_generales") or [])

    return {
        "tiene":unicos(tiene),
        "falta":unicos(falta),
        "confirmar":unicos(confirmar),
        "pendientes":unicos(pendientes),
        "obligatorios":unicos(obligatorios)
    }

# ============================================================
# DOCUMENTOS ESPECÍFICOS
# ============================================================

def documentos_del_caso(caso,respuestas):
    c=obtener_caso(caso)
    if not c:return []

    docs=[]

    docs.extend(c.get("documentos_nacionalidad") or [])
    docs.extend(c.get("documentos_identidad") or [])

    m=c.get("requisitos_mapeados") or {}

    for qid,doc in m.items():
        valor=(respuestas or {}).get(qid)

        # Solo agregar como documento específico cuando
        # realmente aplica al caso.
        if qid in ("nacionalidad","nacionalidad_menor","nacionalidad_padre"):
            continue
        if qid in ("identidad","identidad_menor","identidades","identidades_padres"):
            continue

        if valor is not None:
            docs.append(doc)

    return unicos(docs)

# ============================================================
# PERSONAS QUE DEBEN PRESENTARSE
# ============================================================

def personas_del_caso(caso,respuestas=None,perfil=None):
    c=obtener_caso(caso)
    if not c:return []

    personas=[]
    tipos=c.get("personas") or []

    for tipo in tipos:
        if tipo=="adulto":
            personas.append("La persona que realiza el trámite")

        elif tipo=="menor":
            personas.append("El menor")

        elif tipo=="padre":
            personas.append("El padre, cuando corresponda")

        elif tipo=="madre":
            personas.append("La madre, cuando corresponda")

        elif tipo=="tutor":
            personas.append("El tutor, cuando corresponda")

    return unicos(personas)

# ============================================================
# DATOS PERSONALES PARA EL RESULTADO
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

    if not m:
        return []

    return [
        ("Nombre del menor",pendiente(m.get("nombre"))),
        ("Apellido paterno",pendiente(m.get("apellido_paterno"))),
        ("Apellido materno",pendiente(m.get("apellido_materno"))),
        ("Fecha de nacimiento",pendiente(m.get("fecha_nacimiento"))),
        ("Lugar de nacimiento",pendiente(m.get("lugar_nacimiento"))),
        ("Nacionalidad",pendiente(m.get("nacionalidad")))
    ]

def datos_padre_madre_tutor(perfil):
    p=(perfil or {}).get("padre_madre_tutor") or {}

    if not p:
        return []

    return [
        ("Nombre",pendiente(p.get("nombre"))),
        ("Relación",pendiente(p.get("relacion"))),
        ("Teléfono",pendiente(p.get("telefono"))),
        ("Correo",pendiente(p.get("email"))),
        ("Dirección",pendiente(p.get("direccion")))
    ]

# ============================================================
# DETECTAR SITUACIONES ESPECIALES
# ============================================================

def situaciones_especiales(caso,respuestas):
    c=obtener_caso(caso)
    if not c:return []

    r=[]

    for q in c.get("preguntas",[]):
        qid=q.get("id","")
        valor=(respuestas or {}).get(qid)

        if vacio(valor):
            continue

        if qid in (
            "naturalizado",
            "pasaporte_especial",
            "op7",
            "padre_ausente",
            "situacion_pasaporte",
            "situacion",
            "cambio_domicilio"
        ):
            if si(valor) or texto(valor) not in ("no",""):
                r.append(
                    q.get("ayuda") or
                    "Este caso tiene una situación que debe revisarse."
                )

    r.extend(c.get("especiales") or [])

    return unicos(r)

# ============================================================
# ACCIONES DEL CASO
# ============================================================

def acciones_del_caso(caso,respuestas=None):
    c=obtener_caso(caso)
    if not c:return []

    acciones=[]

    for a in c.get("acciones",[]):
        x=deepcopy(a)

        # Toda acción tiene una función clara.
        x["accion"]=x.get("accion") or x.get("titulo") or "CONSULTAR"
        x["url"]=x.get("url") or c.get("fuente","")

        acciones.append(x)

    # Botón oficial obligatorio para cada trámite.
    fuente=c.get("fuente","")

    if fuente:
        acciones.insert(
            0,
            {
                "id":"tramite_especifico",
                "tipo":"oficial",
                "titulo":"IR AL TRÁMITE OFICIAL",
                "texto":"Abre directamente la información oficial de este trámite.",
                "url":fuente
            }
        )

    return acciones

# ============================================================
# CITA
# ============================================================

def informacion_cita(caso):
    c=obtener_caso(caso)

    if not c:
        return {}

    x=deepcopy(c.get("cita") or {})

    if x.get("necesaria"):
        x["telefono"]=x.get("telefono") or CONTACTO["citas"]
        x["url"]=x.get("url") or FUENTES["citas"]
        x["mensaje"]="Si tu caso requiere cita, usa únicamente el sistema oficial."

    return x

# ============================================================
# PAGO
# ============================================================

def informacion_pago(caso,respuestas=None):
    c=obtener_caso(caso)
    if not c:return {}

    categoria=c.get("categoria","")

    pago={
        "necesario":False,
        "cantidad":"",
        "mensaje":"Confirma siempre la tarifa vigente antes de acudir.",
        "fuente":FUENTES["tarifas"]
    }

    if categoria=="pasaportes":
        pago["necesario"]=True
        pago["cantidad"]="Depende de la vigencia del pasaporte."

    elif categoria=="matricula":
        pago["necesario"]=True
        pago["cantidad"]=TARIFAS["matricula"]

    elif categoria=="actas":
        pago["necesario"]=True
        pago["cantidad"]=TARIFAS["acta_certificada"]

    elif categoria=="registro_civil":
        pago["necesario"]=True
        pago["cantidad"]="El registro puede ser gratuito; las copias certificadas pueden tener costo."

    elif categoria=="electoral":
        pago["necesario"]=False
        pago["cantidad"]=TARIFAS["credencial_votar"]

    return pago

# ============================================================
# COPIAS
# ============================================================

def copias_del_caso(caso):
    c=obtener_caso(caso)
    if not c:return []

    r=[]

    # Solo incluir copias cuando la información oficial del
    # procedimiento las contempla explícitamente.
    if caso=="cartilla_militar":
        r=[
            "Copia del acta de nacimiento certificada.",
            "Copia del comprobante de domicilio."
        ]

    return r

# ============================================================
# DOCUMENTOS ORIGINALES
# ============================================================

def originales_del_caso(caso):
    c=obtener_caso(caso)
    if not c:return []

    r=[]

    for x in c.get("documentos_nacionalidad") or []:
        r.append(x)

    for x in c.get("documentos_identidad") or []:
        r.append(x)

    return unicos(r)

# ============================================================
# VIGENCIA
# ============================================================

def vigencia_del_caso(caso,respuestas=None):
    if caso=="pasaporte_primera_vez":
        return [
            "Menores de 3 años: 1 o 3 años.",
            "De 3 años a menos de 18: 3 o 6 años.",
            "Adultos: 3, 6 o 10 años.",
            "La vigencia de 10 años corresponde a personas adultas."
        ]

    if caso=="matricula_primera_vez" or caso=="matricula_menor":
        return ["La matrícula consular tiene vigencia de 5 años."]

    return []

# ============================================================
# ENTREGA
# ============================================================

def entrega_del_caso(caso):
    if caso in (
        "pasaporte_primera_vez",
        "pasaporte_renovacion",
        "pasaporte_menor"
    ):
        return [
            "En el Consulado de México en Estados Unidos,
            la entrega puede realizarse el mismo día cuando
            el trámite queda aprobado y no existe una falla
            del sistema.",
            "El tiempo informado puede ser aproximadamente
            de dos horas, pero debe entenderse como una
            referencia y no como una garantía."
        ]

    if caso in ("matricula_primera_vez","matricula_menor"):
        return [
            "La matrícula puede entregarse el mismo día cuando
            el trámite es aprobado y no existe una falla del sistema.",
            "El tiempo informado puede ser aproximadamente de dos horas."
        ]

    return []

# ============================================================
# RESULTADO VERDE / AMARILLO / ROJO
# ============================================================

def calcular_estado(evaluacion):
    falta=lista(evaluacion.get("falta"))
    confirmar=lista(evaluacion.get("confirmar"))
    pendientes=lista(evaluacion.get("pendientes"))

    if falta:
        return {
            "codigo":"rojo",
            "titulo":"ATENCIÓN: TODAVÍA NO VAYAS",
            "mensaje":"Hay algo importante que todavía te falta."
        }

    if confirmar or pendientes:
        return {
            "codigo":"amarillo",
            "titulo":"TE FALTA CONFIRMAR ALGO",
            "mensaje":"Antes de ir, confirma la información que aparece abajo."
        }

    return {
        "codigo":"verde",
        "titulo":"PARECES LISTO",
        "mensaje":"Con las respuestas que nos diste, no aparece un requisito pendiente."
    }

# ============================================================
# TEXTO AMIGABLE DEL ESTADO
# ============================================================

def mensaje_estado(estado,evaluacion):
    if estado["codigo"]=="rojo":
        return estado["mensaje"]

    if estado["codigo"]=="amarillo":
        return estado["mensaje"]

    return (
        "Revisamos las respuestas que nos diste. "
        "No aparece un requisito pendiente en esas respuestas. "
        "Antes de acudir, revisa la información oficial."
    )

# ============================================================
# RESULTADO COMPLETO
# ============================================================

def resultado(servicio,caso,respuestas=None,perfil=None):
    c=obtener_caso(caso)

    if not c:
        return {
            "tipo":"error",
            "error":"No se encontró el trámite."
        }

    respuestas=deepcopy(respuestas or {})
    perfil=_perfil_desde(respuestas,perfil)

    evaluacion=evaluar_requisitos(caso,respuestas)
    estado=calcular_estado(evaluacion)

    documentos=documentos_del_caso(caso,respuestas)
    originales=originales_del_caso(caso)
    copias=copias_del_caso(caso)

    personas=personas_del_caso(
        caso,
        respuestas,
        perfil
    )

    especiales=situaciones_especiales(
        caso,
        respuestas
    )

    acciones=acciones_del_caso(
        caso,
        respuestas
    )

    cita=informacion_cita(caso)
    pago=informacion_pago(caso,respuestas)
    vigencia=vigencia_del_caso(caso,respuestas)
    entrega=entrega_del_caso(caso)

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

        "personas":personas,

        "evaluacion":evaluacion,

        "tiene":evaluacion["tiene"],
        "falta":evaluacion["falta"],
        "confirmar":evaluacion["confirmar"],
        "pendientes":evaluacion["pendientes"],
        "obligatorios":evaluacion["obligatorios"],

        "documentos":documentos,
        "documentos_originales":originales,
        "copias":copias,

        "cita":cita,
        "pago":pago,

        "vigencia":vigencia,
        "entrega":entrega,

        "especiales":especiales,
        "acciones":acciones,

        "fuente_oficial":c.get("fuente",""),
        "fuentes":FUENTES,

        "respuestas":respuestas,

        "mensaje":mensaje_estado(
            estado,
            evaluacion
        ),

        "pdf":{
            "titulo":(c.get("pdf") or {}).get(
                "titulo",
                "HOJA DE RUTA"
            ),
            "secciones":(c.get("pdf") or {}).get(
                "secciones",
                []
            )
        }
    }

# ============================================================
# CONTINUAR DESDE UN RESULTADO
# ============================================================

def continuar_resultado(
    servicio,
    caso,
    respuestas=None,
    perfil=None
):
    return resultado(
        servicio,
        caso,
        respuestas or {},
        perfil or {}
    )

# ============================================================
# FUNCIÓN DE COMPATIBILIDAD PARA app.py
# ============================================================

def procesar(
    servicio="",
    caso="",
    pregunta_id="",
    texto="",
    respuestas=None,
    perfil=None,
    accion=""
):
    servicio=normalizar_servicio(servicio)

    if accion=="seleccionar_caso":
        return seleccionar_caso(
            servicio,
            caso,
            respuestas,
            perfil
        )

    if accion=="resultado":
        return resultado(
            servicio,
            caso,
            respuestas,
            perfil
        )

    if texto:
        return interpretar(
            servicio,
            caso,
            pregunta_id,
            texto,
            respuestas,
            perfil
        )

    if caso:
        q=siguiente_pregunta(
            caso,
            respuestas or {},
            pregunta_id
        )

        if q:
            j=pregunta_json(
                caso,
                q,
                respuestas or {}
            )
            j["perfil"]=_perfil_desde(
                respuestas,
                perfil
            )
            return j

        return resultado(
            servicio,
            caso,
            respuestas or {},
            perfil or {}
        )

    return iniciar(
        servicio,
        respuestas or {},
        ""
    )

# ============================================================
# VALIDACIÓN INTERNA DEL MANUAL
# ============================================================

def validar_manual():
    errores=[]

    for cid,c in CASOS.items():

        if not c.get("nombre"):
            errores.append(
                f"{cid}: falta nombre"
            )

        if not c.get("categoria"):
            errores.append(
                f"{cid}: falta categoria"
            )

        if not c.get("fuente"):
            errores.append(
                f"{cid}: falta fuente oficial"
            )

        ids=set()

        for q in c.get("preguntas",[]):
            qid=q.get("id")

            if not qid:
                errores.append(
                    f"{cid}: pregunta sin id"
                )
                continue

            if qid in ids:
                errores.append(
                    f"{cid}: pregunta repetida {qid}"
                )

            ids.add(qid)

            if not q.get("texto"):
                errores.append(
                    f"{cid}: pregunta {qid} sin texto"
                )

            if q.get("tipo")=="opciones":
                if not q.get("opciones"):
                    errores.append(
                        f"{cid}: opciones vacías en {qid}"
                    )

        for a in c.get("acciones",[]):
            if not a.get("url") and not c.get("fuente"):
                errores.append(
                    f"{cid}: acción sin URL"
                )

    return {
        "ok":not errores,
        "errores":errores,
        "casos":len(CASOS)
    }

# ============================================================
# RESUMEN DEL MANUAL
# ============================================================

def resumen_manual():
    categorias={}

    for c in CASOS.values():
        cat=c.get("categoria","otros")
        categorias.setdefault(cat,0)
        categorias[cat]+=1

    return {
        "app":APP,
        "consulado":CONSULADO,
        "motor":"100% determinístico",
        "ia":False,
        "casos":len(CASOS),
        "categorias":categorias,
        "fuentes":len(FUENTES),
        "contactos":CONTACTO
    }

# ============================================================
# FUNCIONES DE CONSULTA PARA app.py / PRUEBAS
# ============================================================

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
# BOTÓN OFICIAL — SIEMPRE DIRECTO AL TRÁMITE
# ============================================================

def tramite_oficial(caso):
    c=obtener_caso(caso)

    if not c:
        return {
            "titulo":"INFORMACIÓN OFICIAL",
            "url":"",
            "texto":"No se encontró el trámite."
        }

    return {
        "titulo":"IR AL TRÁMITE OFICIAL",
        "url":c.get("fuente",""),
        "texto":"Consulta directamente la información oficial de este trámite."
    }

# ============================================================
# MENSAJES PARA PERSONAS CON BAJA ALFABETIZACIÓN
# ============================================================

def instrucciones_simples(caso,estado,respuestas=None):
    c=obtener_caso(caso)
    if not c:return []

    r=[]

    if estado=="rojo":
        r.append("NO VAYAS TODAVÍA.")
        r.append("Primero completa lo que te falta.")

    elif estado=="amarillo":
        r.append("ANTES DE IR, CONFIRMA LO QUE APARECE AQUÍ.")

    else:
        r.append("PARECES LISTO.")
        r.append("REVISA TODO UNA VEZ ANTES DE SALIR.")

    r.append(
        "SI QUIERES VER LA INFORMACIÓN OFICIAL, "
        "PRESIONA EL BOTÓN DEL TRÁMITE."
    )

    if c.get("cita",{}).get("necesaria"):
        r.append(
            "SI NECESITAS CITA, USA EL BOTÓN DE CITA."
        )

    return r

# ============================================================
# RESPUESTA FINAL SIMPLIFICADA PARA PANTALLA
# ============================================================

def pantalla_resultado(
    servicio,
    caso,
    respuestas=None,
    perfil=None
):
    r=resultado(
        servicio,
        caso,
        respuestas or {},
        perfil or {}
    )

    r["instrucciones"]=instrucciones_simples(
        caso,
        r["estado_codigo"],
        respuestas
    )

    r["boton_oficial"]=tramite_oficial(caso)

    return r

# ============================================================
# ARRANQUE DEL MOTOR
# ============================================================

MANUAL_VALIDACION=validar_manual()
MANUAL_RESUMEN=resumen_manual()
