import re,unicodedata

FUENTES={
 "pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/pasaporte",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/dconsular",
 "acta":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
 "doble_nacionalidad":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/doble-nacionalidad",
 "poderes":"https://consulmex.sre.gob.mx/miami/index.php/poderes-notariales",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "citas":"https://citas.sre.gob.mx"
}

def normalizar(v):
    s=str(v or "").strip().lower()
    s=unicodedata.normalize("NFD",s).encode("ascii","ignore").decode()
    return re.sub(r"\s+"," ",s)

def vacio(v):
    return not str(v or "").strip()

def si(v):
    return normalizar(v) in {"si","yes","s","true","1","confirmado","confirmada"}

def no(v):
    return normalizar(v) in {"no","n","false","0"}

def unico(a):
    r=[]
    for x in a or []:
        x=str(x or "").strip()
        if x and x not in r:r.append(x)
    return r

def _texto_respuestas(r):
    return " ".join(str(v) for v in (r or {}).values() if v)

def extraer_perfil(texto):
    t=str(texto or "").strip()
    if not t:return {}
    p={}
    m=re.search(r"(?:me llamo|mi nombre es|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){1,5})",t,re.I)
    if m:p["nombre"]=m.group(1).strip(" .,")
    m=re.search(r"(?:tel(?:éfono)?|telefono|phone|cel(?:ular)?)\D{0,12}(\+?1?[\s().-]*\d{3}[\s().-]*\d{3}[\s.-]*\d{4})",t,re.I)
    if m:p["telefono"]=re.sub(r"\D","",m.group(1))
    m=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",t)
    if m:p["email"]=m.group(0)
    m=re.search(r"\b\d{5}(?:-\d{4})?\b",t)
    if m:p["zip"]=m.group(0)
    estados="Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming"
    m=re.search(r"\b("+estados+r")\b",t,re.I)
    if m:p["estado"]=m.group(1)
    m=re.search(r"(?:vivo en|vivo por|domicilio|direccion|dirección)\s*:?\s*([^.;\n]+)",t,re.I)
    if m:p["direccion"]=m.group(1).strip(" ,")
    if re.search(r"\bmexican[oa] naturalizad[oa]\b|\bnaturalizad[oa]\s+mexican[oa]\b",t,re.I):
        p["nacionalidad"]="Mexicana por naturalización"
    elif re.search(r"\bmexican[oa]\b",t,re.I):
        p["nacionalidad"]="Mexicana"
    return p

def fusionar(a,b):
    r=dict(a or {})
    for k,v in (b or {}).items():
        if not vacio(v):r[k]=v
    return r

def guardar_respuesta(r,pid,v):
    r=dict(r or {})
    r.setdefault("respuestas",{})[pid]=v
    r["perfil"]=fusionar(r.get("perfil"),extraer_perfil(v))
    return r

def _q(pid,texto,tipo="opciones",opciones=None,required=True,permite_otro=True):
    return {
        "id":pid,"texto":texto,"tipo":tipo,
        "opciones":opciones or ["Sí","No","No estoy seguro"],
        "required":required,"permite_otro":permite_otro
    }

SI_NO=["Sí","No","No estoy seguro"]

CASOS={
"pasaporte_primera":{
 "nombre":"Pasaporte mexicano por primera vez",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "Presentarte personalmente en el Consulado.",
  "Contar con cita.",
  "Presentar un documento original que acredite la nacionalidad mexicana.",
  "Presentar identificación oficial original con fotografía.",
  "Cubrir la tarifa consular vigente."
 ],
 "preguntas":[
  _q("nacionalidad","¿Tienes un documento original que compruebe tu nacionalidad mexicana?",opciones=SI_NO),
  _q("identificacion","¿Tienes una identificación oficial original con fotografía?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita para este trámite?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa consular vigente?",opciones=SI_NO)
 ],
 "personas":["La persona que solicita el pasaporte debe presentarse personalmente."],
 "originales":["Documento original que acredite la nacionalidad mexicana.","Identificación oficial original con fotografía."],
 "copias":[],
 "pago":["Confirma la tarifa vigente antes de acudir."],
 "cita":["La cita se gestiona mediante el sistema oficial de citas de la SRE."],
 "importante":["La autoridad puede solicitar documentación adicional según las circunstancias del caso."]
},
"pasaporte_renovacion":{
 "nombre":"Renovación de pasaporte mexicano",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "Presentarte personalmente.",
  "Contar con cita.",
  "Presentar el pasaporte que deseas renovar.",
  "Cubrir la tarifa consular vigente."
 ],
 "preguntas":[
  _q("pasaporte_actual","¿Tienes el pasaporte que deseas renovar?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa consular vigente?",opciones=SI_NO),
  _q("caso_especial","¿Tu pasaporte es de emergencia, protección, restringido, no canjeable o fue expedido hace muchos años?",opciones=SI_NO,required=False)
 ],
 "personas":["La persona titular del pasaporte debe presentarse personalmente."],
 "originales":["Pasaporte que deseas renovar."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["La renovación requiere cita."],
 "importante":["Pasaportes antiguos o con características especiales pueden requerir documentación adicional.","Un pasaporte de un año no se renueva como una renovación ordinaria."]
},
"pasaporte_perdido":{
 "nombre":"Pasaporte perdido, robado, destruido o mutilado",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "Presentarte personalmente.",
  "Contar con cita.",
  "Presentar el reporte correspondiente ante la autoridad competente.",
  "Cumplir los requisitos de primera expedición cuando corresponda.",
  "Cubrir la tarifa vigente."
 ],
 "preguntas":[
  _q("reporte","¿Ya tienes el reporte de pérdida, robo, destrucción o mutilación ante la autoridad competente?",opciones=SI_NO),
  _q("nacionalidad","¿Tienes un documento original que compruebe tu nacionalidad mexicana?",opciones=SI_NO),
  _q("identificacion","¿Tienes una identificación oficial original con fotografía?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona titular debe presentarse personalmente."],
 "originales":["Reporte correspondiente.","Documento de nacionalidad mexicana.","Identificación oficial."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["La atención requiere cita."],
 "importante":["La reposición por pérdida, robo, destrucción o mutilación puede tratarse como primera expedición."]
},
"pasaporte_menor":{
 "nombre":"Pasaporte mexicano para menor de edad",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "El menor debe presentarse personalmente.",
  "Deben presentarse quienes ejerzan la patria potestad o tutela.",
  "Documento original de nacionalidad del menor.",
  "Documento original de identidad del menor.",
  "Identificación de los padres o tutores.",
  "Autorización correspondiente de quienes ejerzan la patria potestad."
 ],
 "preguntas":[
  _q("menor","¿El solicitante es menor de 18 años y no está casado?",opciones=SI_NO),
  _q("nacionalidad","¿Tienes el documento original que acredita la nacionalidad mexicana del menor?",opciones=SI_NO),
  _q("identidad_menor","¿Tienes identificación original del menor?",opciones=SI_NO),
  _q("padres","¿Pueden presentarse los padres o tutores que correspondan?",opciones=SI_NO),
  _q("identificaciones_padres","¿Tienes las identificaciones de los padres o tutores?",opciones=SI_NO),
  _q("op7","¿Está resuelta la autorización de ambos padres o tutores cuando corresponda?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["El menor debe presentarse.","Deben presentarse los padres o tutores que correspondan."],
 "originales":["Documento de nacionalidad del menor.","Identificación del menor.","Identificaciones de los padres o tutores.","Autorizaciones correspondientes."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["El trámite requiere cita."],
 "importante":["La separación o divorcio por sí solos no eliminan la patria potestad.","Cuando un padre no puede acudir pueden existir procedimientos OP-7 u otras actuaciones consulares.","La autoridad debe preparar y revisar las autorizaciones antes de firmarlas."]
},
"pasaporte_naturalizado":{
 "nombre":"Pasaporte para mexicano por naturalización",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "Documento original de naturalización mexicana o copia certificada cuando corresponda.",
  "Identificación oficial original.",
  "Presentación personal.",
  "Cita.",
  "Tarifa vigente."
 ],
 "preguntas":[
  _q("naturalizacion","¿Tienes tu carta de naturalización mexicana original o la copia certificada que corresponda?",opciones=SI_NO),
  _q("identificacion","¿Tienes identificación oficial original con fotografía?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "originales":["Carta de naturalización mexicana original o documento válido correspondiente.","Identificación oficial."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["La atención requiere cita."],
 "importante":["Conserva el documento de naturalización para presentarlo cuando corresponda."]
},
"pasaporte_apellido_conyuge":{
 "nombre":"Pasaporte con apellido del cónyuge",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "Cumplir los requisitos del pasaporte que corresponda.",
  "Presentar el acta de matrimonio cuando se solicite incorporar el apellido del cónyuge."
 ],
 "preguntas":[
  _q("pasaporte_base","¿Ya cumples los requisitos del pasaporte que vas a solicitar o renovar?",opciones=SI_NO),
  _q("matrimonio","¿Tienes el acta de matrimonio que acredita el apellido del cónyuge?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "originales":["Acta de matrimonio cuando corresponda.","Documentos requeridos para el pasaporte."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["Confirma la cita en el sistema oficial."],
 "importante":["El apellido del cónyuge se incorpora en la sección correspondiente del pasaporte; los nombres y apellidos propios permanecen conforme a las reglas aplicables."]
},
"pasaporte_extemporaneo":{
 "nombre":"Pasaporte con posible problema de registro de nacimiento extemporáneo",
 "servicio":"cita","fuente":FUENTES["pasaporte"],
 "requisitos":[
  "Documento de nacionalidad mexicana.",
  "Identificación oficial.",
  "Cita.",
  "Revisión especial si el registro de nacimiento fue extemporáneo."
 ],
 "preguntas":[
  _q("nacionalidad","¿Tienes tu documento original de nacionalidad mexicana?",opciones=SI_NO),
  _q("identificacion","¿Tienes identificación oficial original?",opciones=SI_NO),
  _q("registro_extemporaneo","¿Tu registro de nacimiento fue realizado fuera del periodo considerado normal?",opciones=SI_NO,required=False),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "originales":["Documento de nacionalidad.","Identificación oficial.","Documentación adicional que solicite el Consulado después de revisar el caso."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["Confirma la cita oficial."],
 "importante":[
  "Los registros extemporáneos pueden requerir comprobaciones o documentos complementarios.",
  "En Miami existen periodos de referencia distintos según el año de nacimiento.",
  "Si la autoridad necesita verificar información, la expedición puede demorarse."
]
},
"matricula_primera":{
 "nombre":"Matrícula Consular por primera vez",
 "servicio":"cita","fuente":FUENTES["matricula"],
 "requisitos":[
  "Presentación personal.",
  "Cita.",
  "Documento original de nacionalidad mexicana.",
  "Identificación oficial original con fotografía.",
  "Comprobante de domicilio en Estados Unidos con dirección completa.",
  "Tarifa vigente."
 ],
 "preguntas":[
  _q("nacionalidad","¿Tienes un documento original que compruebe tu nacionalidad mexicana?",opciones=SI_NO),
  _q("identificacion","¿Tienes identificación oficial original con fotografía?",opciones=SI_NO),
  _q("domicilio","¿Tienes comprobante de domicilio en Estados Unidos con tu dirección completa?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "originales":["Documento de nacionalidad mexicana.","Identificación oficial.","Comprobante de domicilio."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["El trámite requiere cita."],
 "importante":["Si el comprobante de domicilio no está a nombre del solicitante pueden existir alternativas dependiendo de la situación."]
},
"matricula_renovacion":{
 "nombre":"Renovación de Matrícula Consular",
 "servicio":"cita","fuente":FUENTES["matricula"],
 "requisitos":[
  "Presentación personal.",
  "Cita.",
  "Matrícula Consular vigente que se desea renovar.",
  "Comprobante de domicilio si cambió el domicilio.",
  "Tarifa vigente."
 ],
 "preguntas":[
  _q("matricula_actual","¿Tienes la Matrícula Consular que deseas renovar?",opciones=SI_NO),
  _q("domicilio_cambio","¿Cambió tu domicilio desde que obtuviste la matrícula?",opciones=SI_NO,required=False),
  _q("domicilio","Si cambió tu domicilio, ¿tienes comprobante del nuevo domicilio?",opciones=SI_NO,required=False),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona titular debe presentarse personalmente."],
 "originales":["Matrícula Consular que se desea renovar.","Comprobante de nuevo domicilio si cambió la residencia."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["El trámite requiere cita."],
 "importante":["Si no cambió el domicilio, el comprobante de domicilio no se requiere para la renovación ordinaria según la información oficial."]
},
"matricula_perdida":{
 "nombre":"Matrícula Consular perdida o robada",
 "servicio":"cita","fuente":FUENTES["matricula"],
 "requisitos":[
  "Presentación personal.",
  "Cita.",
  "Explicar las circunstancias de la pérdida o robo mediante el formato correspondiente.",
  "Tarifa vigente."
 ],
 "preguntas":[
  _q("perdida","¿La matrícula fue perdida o robada?",opciones=SI_NO),
  _q("formulario","¿Estás preparado para explicar lo ocurrido en el formato correspondiente del Consulado?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "originales":["Documentación de identidad y nacionalidad que corresponda.","Información necesaria para completar el formulario de pérdida o robo."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["Confirma la cita oficial."],
 "importante":["El sistema consular puede requerir el formulario correspondiente antes de emitir una nueva matrícula."]
},
"matricula_menor":{
 "nombre":"Matrícula Consular para menor de edad",
 "servicio":"cita","fuente":FUENTES["matricula"],
 "requisitos":[
  "Presentación del menor.",
  "Presentación de padres o tutores que correspondan.",
  "Documento de nacionalidad del menor.",
  "Identificación del menor.",
  "Identificaciones de los padres o tutores.",
  "Autorizaciones correspondientes.",
  "Tarifa vigente."
 ],
 "preguntas":[
  _q("nacionalidad","¿Tienes el documento original de nacionalidad mexicana del menor?",opciones=SI_NO),
  _q("identidad_menor","¿Tienes identificación original del menor?",opciones=SI_NO),
  _q("padres","¿Pueden presentarse los padres o tutores que correspondan?",opciones=SI_NO),
  _q("identificaciones_padres","¿Tienes las identificaciones de los padres o tutores?",opciones=SI_NO),
  _q("autorizacion","¿Está resuelta la autorización de quienes deben otorgarla?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa vigente?",opciones=SI_NO)
 ],
 "personas":["El menor debe presentarse.","Deben presentarse los padres o tutores que correspondan."],
 "originales":["Documento de nacionalidad del menor.","Identificación del menor.","Identificaciones de padres o tutores.","Autorizaciones correspondientes."],
 "copias":[],
 "pago":["Confirma la tarifa vigente."],
 "cita":["Confirma la cita oficial."],
 "importante":["La matrícula tiene una vigencia de cinco años.","La separación o divorcio no elimina por sí sola la patria potestad."]
},
"registro_nacimiento_extranjero":{
 "nombre":"Registro de nacimiento de persona nacida en el extranjero",
 "servicio":"cita","fuente":FUENTES["doble_nacionalidad"],
 "requisitos":[
  "Presentar a la persona cuyo nacimiento se registra.",
  "Acta de nacimiento extranjera.",
  "Prueba de nacionalidad mexicana del padre o madre mexicano.",
  "Identificaciones correspondientes de las personas que deben comparecer.",
  "Cita previa."
 ],
 "preguntas":[
  _q("nacido_extranjero","¿La persona cuyo nacimiento se registrará nació fuera de México?",opciones=SI_NO),
  _q("acta_extranjera","¿Tienes el acta de nacimiento extranjera correspondiente?",opciones=SI_NO),
  _q("nacionalidad_padre","¿Tienes el documento que demuestra la nacionalidad mexicana del padre o madre mexicano?",opciones=SI_NO),
  _q("identificaciones","¿Tienes las identificaciones requeridas de las personas que deben comparecer?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO)
 ],
 "personas":["La persona cuyo nacimiento se registra debe presentarse.","También deben presentarse las personas que determine la autoridad para el registro."],
 "originales":["Acta de nacimiento extranjera.","Documento de nacionalidad mexicana del padre o madre mexicano.","Identificaciones correspondientes."],
 "copias":[],
 "pago":["El registro puede ser gratuito; las copias certificadas tienen tarifa. Confirma los costos vigentes."],
 "cita":["El Registro Civil requiere cita previa."],
 "importante":["El Consulado puede solicitar documentos adicionales según el caso.","Confirma los requisitos directamente antes de la cita."]
},
"acta_nacimiento_mexicana":{
 "nombre":"Copia certificada del acta de nacimiento mexicana",
 "servicio":"documento","fuente":FUENTES["acta"],
 "requisitos":[
  "Presentarse en la oficina consular cuando se solicite presencialmente.",
  "Identificación oficial que acredite la identidad del titular.",
  "Datos necesarios para localizar el acta.",
  "Pago de la tarifa aplicable.",
  "CURP si se cuenta con ella."
 ],
 "preguntas":[
  _q("identificacion","¿Tienes una identificación oficial que permita acreditar la identidad del titular?",opciones=SI_NO),
  _q("solicitud","¿Puedes proporcionar los datos necesarios para localizar el acta?",opciones=SI_NO),
  _q("pago","¿Estás preparado para pagar la tarifa aplicable?",opciones=SI_NO),
  _q("curp","¿Tienes la CURP del titular?",opciones=SI_NO,required=False)
 ],
 "personas":["La persona interesada o quien corresponda para solicitar la copia debe cumplir el procedimiento oficial."],
 "originales":["Identificación oficial.","Datos del acta para localizar el registro."],
 "copias":[],
 "pago":["La copia certificada tiene una tarifa consular vigente; confirma el monto antes de solicitarla."],
 "cita":["Confirma si necesitas acudir al Consulado o si puedes obtener el acta mediante el sistema oficial en línea."],
 "importante":[
  "La copia certificada también puede obtenerse mediante el portal oficial de actas del Gobierno de México cuando el registro esté disponible.",
  "Portal oficial: https://www.gob.mx/ActaNacimiento/"
]
},
"poder_notarial":{
 "nombre":"Poderes notariales",
 "servicio":"cita","fuente":FUENTES["poderes"],
 "requisitos":[
  "Identificación oficial vigente.",
  "Información completa de la persona que otorgará el poder.",
  "Información necesaria de la persona que recibirá el poder.",
  "Explicar claramente para qué se utilizará el poder.",
  "Cita y tarifa según el servicio."
 ],
 "preguntas":[
  _q("identificacion","¿Tienes identificación oficial vigente?",opciones=SI_NO),
  _q("otorgante","¿Tienes completos los datos de la persona que otorgará el poder?",opciones=SI_NO),
  _q("apoderado","¿Tienes completos los datos de la persona que recibirá el poder?",opciones=SI_NO),
  _q("finalidad","¿Puedes explicar claramente para qué se utilizará el poder?",opciones=SI_NO),
  _q("cita","¿Ya tienes una cita?",opciones=SI_NO),
  _q("pago","¿Estás preparado para cubrir la tarifa correspondiente?",opciones=SI_NO)
 ],
 "personas":["Debe comparecer quien otorgará el poder conforme al procedimiento notarial."],
 "originales":["Identificación oficial vigente.","Información y documentos necesarios para preparar el poder."],
 "copias":[],
 "pago":["Confirma la tarifa aplicable al poder específico."],
 "cita":["Confirma la cita y procedimiento directamente con el área de poderes notariales."],
 "importante":["Los requisitos pueden cambiar según el tipo de poder y el acto que se desea realizar."]
}
}

OPCIONES={
 "cita":[
  ("pasaporte_primera","Pasaporte mexicano por primera vez"),
  ("pasaporte_renovacion","Renovación de pasaporte"),
  ("pasaporte_perdido","Pasaporte perdido, robado, destruido o mutilado"),
  ("pasaporte_menor","Pasaporte para menor de edad"),
  ("pasaporte_naturalizado","Pasaporte para mexicano por naturalización"),
  ("pasaporte_apellido_conyuge","Pasaporte con apellido del cónyuge"),
  ("pasaporte_extemporaneo","Pasaporte con posible registro de nacimiento extemporáneo"),
  ("matricula_primera","Matrícula Consular por primera vez"),
  ("matricula_renovacion","Renovación de Matrícula Consular"),
  ("matricula_perdida","Matrícula Consular perdida o robada"),
  ("matricula_menor","Matrícula Consular para menor"),
  ("registro_nacimiento_extranjero","Registro de nacimiento de persona nacida en el extranjero"),
  ("poder_notarial","Poderes notariales")
 ],
 "documento":[
  ("acta_nacimiento_mexicana","Copia certificada del acta de nacimiento mexicana"),
  ("pasaporte_primera","Pasaporte mexicano por primera vez"),
  ("matricula_primera","Matrícula Consular por primera vez")
 ]
}

def catalogo(servicio=None):
    if servicio in OPCIONES:
        return [{"id":i,"nombre":n} for i,n in OPCIONES[servicio]]
    return [{"id":i,"nombre":c["nombre"]} for i,c in CASOS.items()]

def buscar_caso(texto,servicio=None):
    t=normalizar(texto)
    if not t:return None
    reglas=[
     (["acta de nacimiento","copia certificada","acta mexicana"],"acta_nacimiento_mexicana"),
     (["poder notarial","poderes notariales"],"poder_notarial"),
     (["doble nacionalidad","registro de nacimiento","nacido en estados unidos","nacio en estados unidos"],"registro_nacimiento_extranjero"),
     (["matricula consular","matricula"],"matricula_primera"),
     (["pasaporte","passport"],"pasaporte_primera")
    ]
    if "perdid" in t or "robad" in t:
        if "matricula" in t:return "matricula_perdida"
        if "pasaporte" in t:return "pasaporte_perdido"
    if "renovar" in t or "renovacion" in t or "renovación" in t:
        if "matricula" in t:return "matricula_renovacion"
        if "pasaporte" in t:return "pasaporte_renovacion"
    if "menor" in t or "hijo" in t or "hija" in t:
        if "matricula" in t:return "matricula_menor"
        if "pasaporte" in t:return "pasaporte_menor"
    if "naturaliz" in t and "pasaporte" in t:return "pasaporte_naturalizado"
    if ("espos" in t or "conyuge" in t or "cónyuge" in t) and "pasaporte" in t:return "pasaporte_apellido_conyuge"
    for palabras,c in reglas:
        if any(x in t for x in palabras):
            if servicio and c not in [x[0] for x in OPCIONES.get(servicio,[])]:continue
            return c
    return None

def _perfil_desde(r):
    r=r or {}
    return fusionar(r.get("perfil") or {},extraer_perfil(_texto_respuestas(r.get("respuestas") or {})))

def _guardar_perfil(r):
    r["perfil"]=_perfil_desde(r)
    return r

def opciones_pregunta(caso,pid=None):
    c=CASOS.get(caso)
    if not c:return []
    for q in c["preguntas"]:
        if pid is None or q["id"]==pid:return q
    return None

def pregunta_actual(caso,respuestas):
    c=CASOS.get(caso)
    if not c:return None
    respuestas=respuestas or {}
    for q in c["preguntas"]:
        if q["id"] not in respuestas or vacio(respuestas[q["id"]):
            return q
    return None

MAPA_REQUISITOS={
 "nacionalidad":"Documento original que acredite la nacionalidad mexicana.",
 "identificacion":"Identificación oficial original.",
 "cita":"Cita correspondiente.",
 "pago":"Pago de la tarifa aplicable.",
 "pasaporte_actual":"Pasaporte que se desea renovar.",
 "reporte":"Reporte correspondiente ante la autoridad competente.",
 "menor":"Condición y presencia del menor conforme al trámite.",
 "nacionalidad_menor":"Documento original de nacionalidad del menor.",
 "identidad_menor":"Identificación original del menor.",
 "padres":"Presentación de padres o tutores que correspondan.",
 "identificaciones_padres":"Identificaciones de padres o tutores.",
 "op7":"Autorización correspondiente de los padres o tutores.",
 "naturalizacion":"Documento original de naturalización mexicana.",
 "matrimonio":"Acta de matrimonio correspondiente.",
 "matricula_actual":"Matrícula Consular que se desea renovar.",
 "domicilio":"Comprobante de domicilio cuando corresponda.",
 "domicilio_cambio":"Confirmación de si cambió el domicilio.",
 "perdida":"Confirmación de pérdida o robo.",
 "formulario":"Información para completar el formulario correspondiente.",
 "autorizacion":"Autorización de quienes deben otorgarla.",
 "acta_extranjera":"Acta de nacimiento extranjera.",
 "nacionalidad_padre":"Documento que acredita la nacionalidad mexicana del padre o madre.",
 "identificaciones":"Identificaciones de las personas que deben comparecer.",
 "nacido_extranjero":"Confirmación de nacimiento fuera de México.",
 "registro_extemporaneo":"Revisión especial por registro de nacimiento extemporáneo.",
 "pasaporte_base":"Requisitos base del pasaporte.",
 "finalidad":"Finalidad claramente definida del poder.",
 "otorgante":"Datos completos de quien otorgará el poder.",
 "apoderado":"Datos completos de quien recibirá el poder.",
 "identidad":"Identificación oficial.",
 "solicitud":"Datos necesarios para localizar el acta."
}

def _etiqueta(q):
    return MAPA_REQUISITOS.get(q["id"],q["texto"])

def documento_estado(caso,r):
    c=CASOS.get(caso)
    if not c:return {"tiene":[],"falta":[],"confirmar":[]}
    respuestas=(r or {}).get("respuestas") or {}
    tiene,falta,confirmar=[],[],[]

    for q in c["preguntas"]:
        pid=q["id"]
        v=respuestas.get(pid)
        if vacio(v):
            if q.get("required"):
                falta.append(_etiqueta(q))
            continue
        nv=normalizar(v)
        etiqueta=_etiqueta(q)
        if q["tipo"]=="opciones":
            if si(v):
                tiene.append(etiqueta)
            elif no(v):
                falta.append(etiqueta)
            else:
                confirmar.append(etiqueta)
        elif pid=="curp":
            if not vacio(v):tiene.append("CURP proporcionada")
        elif not vacio(v):
            tiene.append(f"{etiqueta}: {v}")

    return {
      "tiene":unico(tiene),
      "falta":unico(falta),
      "confirmar":unico(confirmar)
    }

def personas(caso):
    return CASOS.get(caso,{}).get("personas",[])

def acciones(caso,estado):
    c=CASOS.get(caso,{})
    a=[]
    if estado["falta"]:
        a.append("Completa primero los puntos que aparecen en «LO QUE TE FALTA».")
    if estado["confirmar"]:
        a.append("Confirma los puntos marcados en «LO QUE DEBES CONFIRMAR» antes de acudir.")
    if not estado["falta"] and not estado["confirmar"]:
        a.append("Revisa nuevamente tus datos y documentos antes de acudir.")
    a.append("Consulta la información oficial del Consulado antes de la cita o solicitud.")
    return unico(a)

def resultado(caso,r):
    c=CASOS.get(caso)
    if not c:return {}
    r=_guardar_perfil(dict(r or {}))
    e=documento_estado(caso,r)
    criticas=set()

    for q in c["preguntas"]:
        if q.get("required") and q["id"] in (r.get("respuestas") or {}):
            if no(r["respuestas"][q["id"]]):criticas.add(q["id"])
    if criticas:
        estado="🔴 ATENCIÓN / NO VAYAS TODAVÍA"
        nivel="rojo"
    elif e["falta"]:
        estado="🟡 TE FALTA ALGO"
        nivel="amarillo"
    else:
        estado="🟢 PARECES LISTO"
        nivel="verde"

    return {
      "estado":estado,
      "nivel":nivel,
      "servicio":r.get("servicio",""),
      "caso":caso,
      "nombre_tramite":c["nombre"],
      "tramite":c["nombre"],
      "perfil":r.get("perfil",{}),
      "personas":personas(caso),
      "requisitos_obligatorios":c.get("requisitos",[]),
      "tiene":e["tiene"],
      "lo_que_ya_tienes":e["tiene"],
      "falta":e["falta"],
      "faltantes":e["falta"],
      "lo_que_te_falta":e["falta"],
      "confirmar":e["confirmar"],
      "revisar":e["confirmar"],
      "lo_que_debes_confirmar":e["confirmar"],
      "acciones":acciones(caso,e),
      "que_debes_hacer":acciones(caso,e),
      "cita":c.get("cita",[]),
      "documentos_originales":c.get("originales",[]),
      "copias":c.get("copias",[]),
      "pago":c.get("pago",[]),
      "antes_de_firmar":[
        "Revisa que tu nombre, fechas y demás datos estén correctos antes de firmar o imprimir."
      ],
      "vigencia":c.get("vigencia",[]),
      "entrega":c.get("entrega",[]),
      "importante":c.get("importante",[]),
      "fuente":c.get("fuente",FUENTES["citas"])
    }

def _respuesta_pregunta(caso,r):
    q=pregunta_actual(caso,r.get("respuestas") or {})
    if not q:return resultado(caso,r)
    preguntas=CASOS[caso]["preguntas"]
    n=next((i+1 for i,x in enumerate(preguntas) if x["id"]==q["id"]),1)
    return {
      "tipo":"pregunta",
      "servicio":r.get("servicio"),
      "caso":caso,
      "pregunta_id":q["id"],
      "pregunta":q,
      "numero":n,
      "paso":n,
      "total":len(preguntas),
      "perfil":r.get("perfil",{}),
      "respuestas":r.get("respuestas",{})
    }

def iniciar(servicio,respuestas=None,texto=""):
    r={
      "servicio":servicio,
      "respuestas":dict(respuestas or {}),
      "perfil":{}
    }
    r["perfil"]=extraer_perfil(texto)
    caso=buscar_caso(texto,servicio)

    if caso:
        r["caso"]=caso
        return _respuesta_pregunta(caso,r)

    return {
      "tipo":"seleccionar",
      "servicio":servicio,
      "seleccionar":True,
      "titulo":"ELIGE EL TRÁMITE QUE MÁS SE PARECE A TU SITUACIÓN",
      "casos":catalogo(servicio),
      "perfil":r["perfil"],
      "respuestas":r["respuestas"]
    }

def seleccionar_caso(caso,r=None):
    r=dict(r or {})
    r["caso"]=caso
    r.setdefault("respuestas",{})
    r.setdefault("perfil",{})
    r["perfil"]=_perfil_desde(r)
    return _respuesta_pregunta(caso,r)

def continuar(caso,r):
    return _respuesta_pregunta(caso,r)

def interpretar(texto,servicio="",caso="",respuestas=None,perfil=None):
    r={
      "servicio":servicio,
      "caso":caso,
      "respuestas":dict(respuestas or {}),
      "perfil":fusionar(perfil or {},extraer_perfil(texto))
    }
    if not caso:
        caso=buscar_caso(texto,servicio)
    if caso:
        r["caso"]=caso
        return _respuesta_pregunta(caso,r)
    return {
      "tipo":"seleccionar",
      "servicio":servicio,
      "seleccionar":True,
      "titulo":"ELIGE EL TRÁMITE QUE MÁS SE PARECE A TU SITUACIÓN",
      "casos":catalogo(servicio),
      "perfil":r["perfil"],
      "respuestas":r["respuestas"]
    }

def enriquecer_respuesta(caso,r):
    return resultado(caso,r)

def obtener_caso(caso):
    return CASOS.get(caso)

def continuar_respuesta(caso,r):
    return continuar(caso,r)

def guardar_respuesta_final(caso,r):
    return resultado(caso,r)
