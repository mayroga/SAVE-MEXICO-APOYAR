import re,unicodedata

FUENTES={
 "pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/pasaportes",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/dconsular",
 "acta":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
 "registro_civil":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/doble-nacionalidad",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "citas":"https://citas.sre.gob.mx",
 "acta_online":"https://www.gob.mx/ActaNacimiento/"
}

CASOS={
"pasaporte_primera_vez":{
 "titulo":"Pasaporte mexicano por primera vez","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"nacionalidad","texto":"¿Cómo demuestras que eres mexicano?","tipo":"texto","required":True},
  {"id":"identificacion","texto":"¿Qué identificación mexicana o de otro país tienes?","tipo":"texto","required":True},
  {"id":"cita","texto":"¿Ya tienes cita para el Consulado?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"presencia","texto":"¿Puedes presentarte personalmente en el Consulado?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona que solicita el pasaporte debe presentarse personalmente."],
 "requisitos":[
  "Documento original que compruebe la nacionalidad mexicana.",
  "Documento original de identidad con fotografía cuyos datos permitan acreditar la identidad.",
  "Cita consular.",
  "Pago de la tarifa vigente."
 ],
 "originales":["Documento original de nacionalidad mexicana.","Identificación original con fotografía."],
 "copias":[],
 "pago":"Confirma la tarifa vigente antes de acudir.",
 "cita":["La solicitud requiere cita.","Puedes consultar el sistema oficial de citas: "+FUENTES["citas"]],
 "importante":["La autoridad consular puede solicitar documentación adicional cuando corresponda."],
 "acciones":["Reúne el documento original que acredita tu nacionalidad mexicana.","Reúne tu identificación original con fotografía.","Obtén o confirma tu cita.","Confirma la tarifa vigente.","Revisa tus datos antes de concluir el trámite."],
 "entrega":"La información oficial de Miami indica entrega el mismo día cuando el trámite procede y no existen fallas del sistema; confirma las condiciones al acudir.",
 "vigencia":"La vigencia depende de la edad y de la opción disponible al momento del trámite."
},
"pasaporte_renovacion":{
 "titulo":"Renovación de pasaporte mexicano","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"pasaporte_actual","texto":"¿Tienes contigo el pasaporte que vas a renovar?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"naturalizado","texto":"¿Eres mexicano por naturalización?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"antiguo","texto":"¿Tu pasaporte es muy antiguo o fue expedido en circunstancias especiales?","tipo":"opciones","opciones":["Sí","No","No estoy seguro"]}
 ],
 "personas":["La persona titular debe presentarse personalmente."],
 "requisitos":["Pasaporte que se desea renovar.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Pasaporte que se desea renovar."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":[
  "Si eres mexicano por naturalización, presenta el original de la carta de naturalización o copia certificada expedida por SRE cuando corresponda.",
  "Pasaportes antiguos o determinados pasaportes especiales pueden requerir documentación adicional.",
  "Un pasaporte de un año no se renueva como una renovación ordinaria."
 ],
 "acciones":["Lleva el pasaporte que vas a renovar.","Si eres naturalizado, prepara tu documento de naturalización.","Confirma tu cita.","Confirma la tarifa vigente.","Revisa todos tus datos antes de concluir."],
 "entrega":"La información oficial señala entrega el mismo día cuando el trámite procede y no existen fallas del sistema."
},
"pasaporte_perdido":{
 "titulo":"Pasaporte perdido, robado o dañado","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"situacion","texto":"¿Qué ocurrió con tu pasaporte?","tipo":"opciones","opciones":["Lo perdí","Me lo robaron","Está destruido o mutilado"]},
  {"id":"reporte","texto":"¿Tienes el reporte de la autoridad correspondiente cuando aplica?","tipo":"opciones","opciones":["Sí","No","No aplica"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "requisitos":["Reporte ante la autoridad competente cuando corresponda.","Documentación de primera expedición.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Pruebas originales de nacionalidad e identidad que correspondan.","Reporte de la autoridad competente cuando corresponda."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["La pérdida, robo, destrucción o mutilación puede hacer que el trámite se atienda como una primera expedición."],
 "acciones":["Realiza el reporte ante la autoridad competente cuando corresponda.","Prepara los documentos de nacionalidad e identidad.","Obtén la cita.","Confirma la tarifa vigente."]
},
"pasaporte_menor":{
 "titulo":"Pasaporte mexicano para un menor","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"edad","texto":"¿Qué edad tiene el menor?","tipo":"texto","required":True},
  {"id":"padres","texto":"¿Pueden presentarse ambos padres o quienes ejercen la patria potestad?","tipo":"opciones","opciones":["Sí","No","No estoy seguro"]},
  {"id":"op7","texto":"Si uno de los padres no puede presentarse, ¿ya existe autorización OP-7 o una situación documentada?","tipo":"opciones","opciones":["Sí","No","No aplica","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienen cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["El menor debe presentarse.","Deben presentarse los padres o quienes ejerzan la patria potestad, según corresponda."],
 "requisitos":[
  "Documento original que compruebe la nacionalidad mexicana del menor.",
  "Documento original de identidad del menor.",
  "Identificaciones de los padres o tutores.",
  "Consentimiento de quienes deban otorgarlo mediante el procedimiento consular correspondiente.",
  "Cita consular.",
  "Pago de la tarifa vigente."
 ],
 "originales":["Nacionalidad original del menor.","Identidad original del menor.","Identificaciones originales de los padres o tutores.","Documentos relacionados con la patria potestad cuando correspondan."],
 "copias":[],
 "pago":"Confirma la tarifa vigente según la edad y vigencia elegida.",
 "cita":["Se requiere cita."],
 "importante":[
  "La separación o el divorcio por sí solos no eliminan la patria potestad.",
  "Cuando un padre no puede acudir pueden existir procedimientos OP-7 u otras resoluciones/documentos según el caso.",
  "El personal consular prepara los formatos OP-5/OP-7 cuando corresponda; deben revisarse antes de firmar."
 ],
 "acciones":["Prepara los documentos originales del menor.","Prepara las identificaciones de los padres o tutores.","Determina quién debe otorgar el consentimiento.","Si falta un padre, confirma el procedimiento OP-7 o el documento judicial aplicable.","Obtén la cita.","Revisa los datos antes de firmar."],
 "entrega":"La información oficial de Miami indica entrega el mismo día cuando el trámite procede y no existen fallas del sistema."
},
"pasaporte_naturalizado":{
 "titulo":"Pasaporte para mexicano por naturalización","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"naturalizacion","texto":"¿Tienes el original de tu carta de naturalización o documento correspondiente?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"identificacion","texto":"¿Tienes una identificación con fotografía?","tipo":"texto","required":True},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "requisitos":["Original de la carta de naturalización o documento de nacionalidad aplicable.","Identificación original con fotografía.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Carta de naturalización original o documento aplicable.","Identificación original con fotografía."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["Para renovaciones, la autoridad puede requerir el documento de naturalización original o copia certificada de SRE según corresponda."],
 "acciones":["Prepara tu carta de naturalización original.","Prepara tu identificación con fotografía.","Obtén la cita.","Confirma la tarifa vigente."]
},
"pasaporte_conyuge":{
 "titulo":"Pasaporte y apellido del cónyuge","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"matrimonio","texto":"¿Tienes el acta de matrimonio que demuestra el apellido de tu cónyuge?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "requisitos":["Documentos normales del pasaporte.","Acta de matrimonio cuando corresponda para acreditar el apellido del cónyuge.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Documentos de nacionalidad e identidad correspondientes.","Acta de matrimonio cuando corresponda."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["El pasaporte conserva los nombres y apellidos de la persona y el apellido del cónyuge se incorpora en el apartado correspondiente cuando procede."],
 "acciones":["Prepara el acta de matrimonio si deseas acreditar el apellido del cónyuge.","Prepara los documentos normales de nacionalidad e identidad.","Obtén la cita.","Confirma la tarifa vigente."]
},
"pasaporte_extemporanea":{
 "titulo":"Pasaporte / nacimiento registrado fuera de plazo","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  {"id":"fecha_nacimiento","texto":"¿Cuál es tu fecha de nacimiento?","tipo":"texto","required":True},
  {"id":"registro_tardio","texto":"¿Tu nacimiento fue registrado fuera del plazo correspondiente?","tipo":"opciones","opciones":["Sí","No","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "requisitos":["Documentación de nacionalidad e identidad correspondiente al caso.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Documentos originales de nacionalidad e identidad que correspondan."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":[
  "La documentación adicional puede depender de la fecha de nacimiento y de cuándo fue registrado el nacimiento.",
  "Miami maneja periodos específicos para registros extemporáneos.",
  "Cuando el registro supera el periodo aplicable, pueden solicitarse pruebas complementarias y verificaciones."
 ],
 "especiales":[
  "Nacidos antes de 1931: hasta 50 años de retraso.",
  "Nacidos de 1931 a 1940: hasta 30 años.",
  "Nacidos de 1941 a 1950: hasta 10 años.",
  "Nacidos de 1951 a 1976: hasta 5 años.",
  "Nacidos desde 1977: hasta 1 año."
 ],
 "acciones":["Indica correctamente la fecha de nacimiento y la fecha de registro.","Confirma si el registro fue extemporáneo.","Si está fuera del periodo aplicable, confirma con el Consulado qué pruebas adicionales corresponden.","Obtén la cita antes de acudir."]
},
"matricula_primera_adulto":{
 "titulo":"Primera matrícula consular","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  {"id":"nacionalidad","texto":"¿Qué documento original tienes para demostrar que eres mexicano?","tipo":"texto","required":True},
  {"id":"identificacion","texto":"¿Qué identificación original con fotografía tienes?","tipo":"texto","required":True},
  {"id":"direccion","texto":"¿Tienes un comprobante de domicilio a tu nombre con tu dirección completa?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "requisitos":["Documento original de nacionalidad mexicana.","Identificación original con fotografía.","Comprobante de domicilio a nombre del solicitante con dirección completa.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Documento original de nacionalidad mexicana.","Identificación original con fotografía.","Comprobante de domicilio correspondiente."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["Si el comprobante de domicilio no está a nombre del solicitante, existen alternativas según la relación con la persona cuyo nombre aparece en el comprobante."],
 "acciones":["Prepara tu documento original de nacionalidad.","Prepara tu identificación con fotografía.","Prepara el comprobante de domicilio.","Si el comprobante no está a tu nombre, confirma la alternativa aplicable.","Obtén la cita.","Confirma la tarifa vigente."]
},
"matricula_renovacion":{
 "titulo":"Renovación de matrícula consular","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  {"id":"matricula_actual","texto":"¿Tienes tu matrícula consular actual?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"cambio_domicilio","texto":"¿Cambiaste de domicilio desde que obtuviste la matrícula?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona titular debe presentarse personalmente."],
 "requisitos":["Matrícula consular actual.","Comprobante de domicilio si cambió la residencia.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Matrícula consular actual.","Comprobante de domicilio cuando corresponda."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["Si no cambió la residencia, el comprobante de domicilio no se exige nuevamente según la información oficial."],
 "acciones":["Lleva tu matrícula actual.","Si cambiaste de domicilio, lleva el comprobante correspondiente.","Obtén la cita.","Confirma la tarifa vigente."]
},
"matricula_perdida":{
 "titulo":"Matrícula consular perdida o robada","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  {"id":"situacion","texto":"¿Qué ocurrió con tu matrícula?","tipo":"opciones","opciones":["La perdí","Me la robaron","No la encuentro"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona solicitante debe presentarse personalmente."],
 "requisitos":["Explicación de las circunstancias mediante el formulario correspondiente en el Consulado.","Documentos de identidad y nacionalidad que correspondan.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Documentos originales de nacionalidad e identidad correspondientes."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["El Consulado indica que, en caso de pérdida o robo, debe llenarse el formulario correspondiente explicando las circunstancias."],
 "acciones":["Prepara los documentos de nacionalidad e identidad.","Obtén la cita.","Explica las circunstancias de la pérdida o robo mediante el formulario consular.","Confirma la tarifa vigente."]
},
"matricula_menor":{
 "titulo":"Matrícula consular para un menor","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  {"id":"edad","texto":"¿Qué edad tiene el menor?","tipo":"texto","required":True},
  {"id":"padres","texto":"¿Pueden presentarse ambos padres o quienes ejercen la patria potestad?","tipo":"opciones","opciones":["Sí","No","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienen cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["Debe presentarse el menor.","Deben presentarse los padres o tutores según corresponda."],
 "requisitos":["Documento original de nacionalidad mexicana del menor.","Documento original de identidad del menor.","Identificaciones de los padres o tutores.","Autorización parental correspondiente.","Cita consular.","Pago de la tarifa vigente."],
 "originales":["Nacionalidad original del menor.","Identidad original del menor.","Identificaciones originales de padres o tutores.","Documentos de patria potestad cuando correspondan."],
 "copias":[],
 "pago":"Confirma la tarifa vigente.",
 "cita":["Se requiere cita."],
 "importante":["La separación o divorcio no elimina por sí solo la patria potestad. Confirma cualquier situación especial directamente con el Consulado."],
 "vigencia":"La matrícula consular para menores tiene vigencia de cinco años según la información oficial de Miami.",
 "entrega":"La información oficial señala entrega el mismo día cuando el trámite procede y no existen fallas del sistema.",
 "acciones":["Prepara la nacionalidad e identidad del menor.","Prepara las identificaciones de los padres o tutores.","Confirma quién debe otorgar la autorización.","Obtén la cita.","Revisa todos los datos antes de imprimir."]
},
"registro_nacimiento_extranjero":{
 "titulo":"Registro de nacimiento de una persona nacida en el extranjero","servicio":"cita","fuente":FUENTES["registro_civil"],
 "preguntas":[
  {"id":"nacido","texto":"¿La persona nació fuera de México?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"padre_madre_mexicano","texto":"¿Uno o ambos padres son mexicanos?","tipo":"opciones","opciones":["Sí","No","No estoy seguro"]},
  {"id":"acta_extranjera","texto":"¿Tienes el acta de nacimiento extranjera original?","tipo":"opciones","opciones":["Sí","No"]},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["Debe presentarse la persona cuyo nacimiento se registra.","Deben presentarse los padres o las personas que correspondan según el caso."],
 "requisitos":["Acta de nacimiento extranjera.","Prueba de nacionalidad mexicana del padre o madre mexicano cuando corresponda.","Identificaciones de las personas que deban comparecer.","Cita previa.","Documentación adicional que determine el Consulado según el caso."],
 "originales":["Acta de nacimiento extranjera original.","Documentos originales que acrediten la nacionalidad mexicana.","Identificaciones originales."],
 "copias":[],
 "pago":"El registro de nacimiento en sí puede ser gratuito; las copias certificadas u otros servicios pueden tener tarifa. Confirma el costo aplicable.",
 "cita":["Los actos del Registro Civil requieren cita previa."],
 "importante":["La documentación exacta puede variar según la situación familiar y documental. Confirma cualquier caso especial con el Consulado antes de acudir."],
 "acciones":["Reúne el acta de nacimiento extranjera.","Reúne la prueba de nacionalidad mexicana del padre o madre mexicano.","Reúne las identificaciones.","Obtén la cita.","Confirma si existe documentación adicional para tu caso."]
},
"acta_nacimiento_mexicana":{
 "titulo":"Copia certificada del acta de nacimiento mexicana","servicio":"documento","fuente":FUENTES["acta"],
 "preguntas":[
  {"id":"identificacion","texto":"¿Tienes una identificación oficial que permita acreditar que eres el titular del acta?","tipo":"opciones","opciones":["Sí","No"],"required":True},
  {"id":"solicitud","texto":"¿Puedes proporcionar los datos necesarios para solicitar el acta?","tipo":"opciones","opciones":["Sí","No"],"required":True},
  {"id":"curp","texto":"¿Tienes CURP?","tipo":"texto","required":False},
  {"id":"pago","texto":"¿Estás preparado para pagar la tarifa correspondiente?","tipo":"opciones","opciones":["Sí","No"],"required":True}
 ],
 "personas":["La persona interesada o quien corresponda debe realizar la solicitud."],
 "requisitos":["Identificación oficial para acreditar la identidad del titular.","Solicitud con los datos necesarios para localizar el acta.","Pago de la tarifa aplicable."],
 "originales":["Identificación oficial."],
 "copias":[],
 "pago":"La copia certificada de acta de nacimiento tiene una tarifa aplicable. Confirma la tarifa vigente antes de acudir.",
 "cita":["Confirma con el Consulado si necesitas cita para la modalidad que vas a utilizar."],
 "importante":[
  "La CURP puede ayudar cuando está disponible, pero no se debe considerar un requisito obligatorio si no cuentas con ella.",
  "También existe la opción oficial de consulta, descarga e impresión en línea."
 ],
 "acciones":["Ten a mano tu identificación oficial.","Prepara los datos del acta.","Si tienes CURP, tenla disponible.","Confirma la tarifa vigente.","También puedes consultar la opción oficial en línea: "+FUENTES["acta_online"]],
 "entrega":"La modalidad presencial y la modalidad en línea tienen procedimientos distintos. Confirma cuál usarás.",
 "especiales":["La autoridad consular puede emitir determinadas copias certificadas de actas mexicanas conforme a las condiciones indicadas por el Consulado."]
},
"poder_notarial":{
 "titulo":"Poder notarial","servicio":"cita","fuente":FUENTES["registro_civil"],
 "preguntas":[
  {"id":"tipo_poder","texto":"¿Qué necesitas hacer con el poder?","tipo":"texto","required":True},
  {"id":"cita","texto":"¿Ya tienes cita?","tipo":"opciones","opciones":["Sí","No"]}
 ],
 "personas":["La persona otorgante debe comparecer personalmente cuando corresponda."],
 "requisitos":["Información completa del poder que se desea otorgar.","Identificación oficial.","Cita consular.","Documentación adicional relacionada con el acto."],
 "originales":["Identificación oficial.","Documentos relacionados con el acto cuando correspondan."],
 "copias":[],
 "pago":"Confirma la tarifa vigente según el tipo de instrumento.",
 "cita":["Confirma la cita y el procedimiento directamente con el área de poderes notariales."],
 "importante":["Los requisitos pueden variar según el tipo de poder y el acto jurídico. No conviene asumir requisitos sin confirmar el caso concreto."],
 "acciones":["Define exactamente qué facultades quieres otorgar.","Prepara tu identificación.","Prepara los datos y documentos relacionados con el acto.","Confirma el procedimiento y la cita con el Consulado."]
}
}

OPCIONES=[
("pasaporte_primera_vez","Pasaporte mexicano por primera vez","cita"),
("pasaporte_renovacion","Renovar pasaporte","cita"),
("pasaporte_perdido","Pasaporte perdido, robado o dañado","cita"),
("pasaporte_menor","Pasaporte para un menor","cita"),
("pasaporte_naturalizado","Pasaporte para mexicano por naturalización","cita"),
("pasaporte_conyuge","Pasaporte y apellido del cónyuge","cita"),
("pasaporte_extemporanea","Pasaporte / nacimiento registrado fuera de plazo","cita"),
("matricula_primera_adulto","Primera matrícula consular","cita"),
("matricula_renovacion","Renovar matrícula consular","cita"),
("matricula_perdida","Matrícula perdida o robada","cita"),
("matricula_menor","Matrícula consular para un menor","cita"),
("registro_nacimiento_extranjero","Registrar nacimiento de una persona nacida en el extranjero","cita"),
("acta_nacimiento_mexicana","Copia certificada del acta de nacimiento mexicana","documento"),
("poder_notarial","Poder notarial","cita")
]

def normalizar(s):
    s=unicodedata.normalize("NFD",str(s or ""))
    return "".join(c for c in s if unicodedata.category(c)!="Mn").lower().strip()

def vacio(v):
    if v is None:return True
    if isinstance(v,str):
        return not v.strip() or normalizar(v) in {"pendiente","pendiente de completar","no se","no se"}
    return False

def si(v):
    return normalizar(v) in {"si","sí","yes","true","1","tengo","puedo","correcto"}

def no(v):
    return normalizar(v) in {"no","false","0","ninguno","ninguna"}

def extraer_perfil(texto):
    t=str(texto or "").strip()
    n=normalizar(t)
    p={}
    m=re.search(r"\b(?:me llamo|mi nombre es|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){1,4})",t,re.I)
    if m:p["nombre"]=m.group(1).strip()
    m=re.search(r"\b(?:telefono|tel[eé]fono|celular|cel)\s*(?:es|:)?\s*(\+?[\d\s().-]{7,})",t,re.I)
    if m:p["telefono"]=m.group(1).strip()
    m=re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",t,re.I)
    if m:p["email"]=m.group(0).strip()
    m=re.search(r"\b(?:zip|c[oó]digo postal)\s*(?:es|:)?\s*(\d{5}(?:-\d{4})?)",t,re.I)
    if m:p["zip"]=m.group(1)
    estados={
      "florida":"Florida","fl":"Florida","texas":"Texas","tx":"Texas","california":"California","ca":"California",
      "arizona":"Arizona","az":"Arizona","new mexico":"New Mexico","nuevo mexico":"New Mexico",
      "new york":"New York","ny":"New York","georgia":"Georgia","ga":"Georgia"
    }
    for k,v in estados.items():
        if re.search(r"\b"+re.escape(k)+r"\b",n):
            p["estado"]=v;break
    m=re.search(r"\b(?:vivo en|vivo|resido en|resido)\s+([^,.]+(?:,\s*[^,.]+)?)",t,re.I)
    if m:
        d=m.group(1).strip()
        if len(d)>2:p["direccion"]=d
    if re.search(r"\bmexicano\s+por\s+naturalizaci[oó]n\b|\bnaturalizado\b",n):
        p["nacionalidad"]="Mexicano por naturalización"
        p["naturalizado"]=True
    elif re.search(r"\bmexicano\b|\bmexicana\b",n):
        p["nacionalidad"]="Mexicano"
    m=re.search(r"\b(?:fecha de nacimiento|naci[oó] el|nac[ií] el)\s*(?:es|:)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",t,re.I)
    if m:p["fecha_nacimiento"]=m.group(1)
    m=re.search(r"\b(?:edad|tengo)\s*(?:es|de|:)?\s*(\d{1,3})\s*(?:años|anos)?\b",t,re.I)
    if m:p["edad"]=m.group(1)
    return p

def fusionar(a,b):
    r=dict(a or {})
    for k,v in (b or {}).items():
        if not vacio(v):r[k]=v
    return r

def guardar_respuesta(pid,v,p):
    if not pid:return
    if not vacio(v):p[pid]=v

def enriquecer_respuesta(pid,v,r):
    if pid=="nacionalidad" and not vacio(v):
        r["nacionalidad"]=v
    if pid in {"direccion","domicilio"} and not vacio(v):
        r["direccion"]=v
    if pid=="telefono" and not vacio(v):r["telefono"]=v
    if pid=="email" and not vacio(v):r["email"]=v
    if pid=="zip" and not vacio(v):r["zip"]=v
    if pid=="estado" and not vacio(v):r["estado"]=v
    if pid=="nombre" and not vacio(v):r["nombre"]=v

def buscar_caso(texto,servicio=None):
    n=normalizar(texto)
    candidatos=[]
    for cid,titulo,s in OPCIONES:
        if servicio and s!=servicio:continue
        score=0
        words=normalizar(titulo).split()
        for w in words:
            if len(w)>3 and w in n:score+=1
        reglas={
          "pasaporte_renovacion":["renovar","renovacion","renovación"],
          "pasaporte_perdido":["perdi","perdido","robaron","robado","danado","dañado"],
          "pasaporte_menor":["menor","hijo","hija","nino","niña","niño"],
          "pasaporte_naturalizado":["naturalizado","naturalizacion","naturalización"],
          "pasaporte_conyuge":["conyuge","cónyuge","esposo","esposa","apellido"],
          "pasaporte_extemporanea":["extemporaneo","extemporánea","registro tardio","tardio"],
          "matricula_primera_adulto":["primera matricula","primera matrícula"],
          "matricula_renovacion":["renovar matricula","renovar matrícula"],
          "matricula_perdida":["perdi matricula","perdi matrícula","matricula perdida","matrícula perdida"],
          "matricula_menor":["matricula menor","matrícula menor"],
          "registro_nacimiento_extranjero":["nacio fuera","nació fuera","nacido en estados unidos","doble nacionalidad","registrar nacimiento"],
          "acta_nacimiento_mexicana":["acta de nacimiento","copia certificada","acta mexicana"],
          "poder_notarial":["poder notarial","poder"]
        }
        for x in reglas.get(cid,[]):
            if normalizar(x) in n:score+=4
        if score:candidatos.append((score,cid))
    if not candidatos:return None
    candidatos.sort(reverse=True)
    return candidatos[0][1]

def catalogo(servicio=None):
    return [
      {"id":cid,"titulo":titulo}
      for cid,titulo,s in OPCIONES if not servicio or s==servicio
    ]

def obtener_caso(caso):
    return CASOS.get(caso)

def _perfil_desde(respuestas):
    p=dict(respuestas.get("_perfil") or {})
    for k,v in respuestas.items():
        if k.startswith("_"):continue
        if k in {"nombre","nacionalidad","telefono","direccion","estado","zip","email","fecha_nacimiento","edad","naturalizado"}:
            if not vacio(v):p[k]=v
    return p

def _guardar_perfil(respuestas,p):
    respuestas["_perfil"]=p
    for k,v in p.items():
        if not vacio(v):respuestas[k]=v

def iniciar(servicio,respuestas=None,_extra=None):
    respuestas=dict(respuestas or {})
    texto=str(_extra or "").strip()
    if texto:
        respuestas["_perfil"]=fusionar(_perfil_desde(respuestas),extraer_perfil(texto))
    if respuestas.get("caso") and respuestas["caso"] in CASOS:
        return continuar(respuestas["caso"],respuestas,"",texto)
    return {
      "servicio":servicio,
      "seleccionar":True,
      "titulo":"¿Qué necesitas?",
      "pregunta":"Elige la opción que más se parece a tu situación.",
      "opciones":catalogo(servicio),
      "respuestas":respuestas
    }

def _respondida(v):
    return not vacio(v)

def pregunta_actual(caso,r):
    c=obtener_caso(caso)
    if not c:return None
    p=_perfil_desde(r)
    for q in c.get("preguntas",[]):
        pid=q["id"]
        if pid=="curp":continue
        if pid=="naturalizado" and p.get("naturalizado") is True:continue
        if pid in p and _respondida(p.get(pid)):continue
        if pid in r and _respondida(r.get(pid)):continue
        return q
    return None

def opciones_pregunta(p):
    if not p:return []
    return p.get("opciones") or []

def documento_estado(caso,r):
    c=obtener_caso(caso)
    if not c:return {}
    p=_perfil_desde(r)
    tiene=[]
    falta=[]
    for q in c.get("preguntas",[]):
        pid=q["id"]
        if pid=="curp":continue
        if _respondida(p.get(pid)) or _respondida(r.get(pid)):
            v=p.get(pid,r.get(pid))
            if normalizar(v) not in {"no","no tengo","no"}:
                tiene.append(f"{q['texto']} — {v}")
        elif q.get("required"):
            falta.append(q["texto"])
    for x in c.get("requisitos",[]):
        encontrado=False
        nx=normalizar(x)
        for k,v in r.items():
            if isinstance(v,str) and v and any(w in nx for w in normalizar(v).split() if len(w)>4):
                encontrado=True;break
        if not encontrado:falta.append(x)
    return {"tiene":tiene,"falta":list(dict.fromkeys(falta))}

def personas(caso,r):
    c=obtener_caso(caso)
    return list(c.get("personas",[])) if c else []

def acciones(caso,r,docs):
    c=obtener_caso(caso)
    a=list(c.get("acciones",[])) if c else []
    if docs.get("falta"):
        a.insert(0,"Completa primero la información que aparece como pendiente.")
    return list(dict.fromkeys(a))

def resultado(caso,r):
    c=obtener_caso(caso)
    if not c:return {}
    p=_perfil_desde(r)
    docs=documento_estado(caso,r)
    faltantes=[]
    for x in docs.get("falta",[]): 
        if x not in faltantes:faltantes.append(x)
    pendientes=[]
    for q in c.get("preguntas",[]):
        pid=q["id"]
        if pid=="curp":continue
        if q.get("required") and vacio(p.get(pid,r.get(pid))):
            pendientes.append(q["texto"])
    for x in pendientes:
        if x not in faltantes:faltantes.append(x)

    revisiones=[]
    for q in c.get("preguntas",[]):
        pid=q["id"]
        v=p.get(pid,r.get(pid))
        if normalizar(v) in {"no","no estoy seguro","no aplica"}:
            revisiones.append(f"Confirma: {q['texto']}")
    if r.get("cita") and no(r.get("cita")):
        revisiones.append("Necesitas obtener o confirmar la cita antes de acudir.")
    if r.get("padres") and normalizar(r.get("padres"))!="si":
        revisiones.append("Confirma quién debe presentarse y quién debe autorizar el trámite.")
    if r.get("op7") and normalizar(r.get("op7")) not in {"si","no aplica"}:
        revisiones.append("Confirma el procedimiento OP-7 o la resolución/documentación aplicable.")

    nivel="verde"
    estado="PARECES LISTO"
    if faltantes:
        nivel="rojo" if any("obligator" in normalizar(x) or "original" in normalizar(x) for x in faltantes) else "amarillo"
        estado="ATENCIÓN / NO VAYAS TODAVÍA" if nivel=="rojo" else "TE FALTA ALGO"
    elif revisiones:
        nivel="amarillo"
        estado="TE FALTA CONFIRMAR ALGO"

    importantes=list(c.get("importante",[]))
    if c.get("especiales"):
        importantes+=c["especiales"]

    perfil={
      "nombre":p.get("nombre"),
      "nacionalidad":p.get("nacionalidad"),
      "telefono":p.get("telefono"),
      "direccion":p.get("direccion"),
      "estado":p.get("estado"),
      "zip":p.get("zip"),
      "email":p.get("email")
    }

    return {
      "caso":caso,
      "titulo":c["titulo"],
      "tramite":c["titulo"],
      "nivel":nivel,
      "estado_texto":estado,
      "perfil":perfil,
      "personas_obligatorias":personas(caso,r),
      "requisitos_obligatorios":list(c.get("requisitos",[])),
      "opcionales":list(c.get("opcionales",[])),
      "documentos":list(c.get("originales",[])),
      "tiene":docs.get("tiene",[]),
      "falta":faltantes,
      "revisar":revisiones,
      "acciones":acciones(caso,r,docs),
      "cita":list(c.get("cita",[])),
      "originales":list(c.get("originales",[])),
      "copias":list(c.get("copias",[])),
      "pago":c.get("pago","Confirma la tarifa vigente."),
      "revision":"Revisa cuidadosamente nombre, apellidos, fechas, lugar de nacimiento y demás datos antes de firmar o imprimir.",
      "vigencia":c.get("vigencia",""),
      "entrega":c.get("entrega",""),
      "importante":importantes,
      "especiales":list(c.get("especiales",[])),
      "confirma":revisiones,
      "fuente":c.get("fuente",""),
      "pendientes":pendientes,
      "checklist":list(c.get("requisitos",[])),
      "respuestas":r
    }

def continuar(caso,respuestas=None,pregunta_id="",texto=""):
    r=dict(respuestas or {})
    c=obtener_caso(caso)
    if not c:raise ValueError("Trámite no válido.")

    p=_perfil_desde(r)
    if texto:
        p=fusionar(p,extraer_perfil(texto))
    if pregunta_id:
        guardar_respuesta(pregunta_id,texto,p)
        enriquecer_respuesta(pregunta_id,texto,r)
        r[pregunta_id]=texto
    _guardar_perfil(r,p)
    r["caso"]=caso

    q=pregunta_actual(caso,r)
    if q:
        opciones=opciones_pregunta(q)
        return {
          "final":False,
          "caso":caso,
          "titulo":c["titulo"],
          "paso":f"PASO {len([x for x in c.get('preguntas',[]) if x.get('id') not in {'curp'} and not (x.get('id')=='naturalizado' and p.get('naturalizado'))])+1}",
          "pregunta_id":q["id"],
          "pregunta":q["texto"],
          "tipo":q.get("tipo","texto"),
          "opciones":opciones,
          "required":bool(q.get("required")),
          "permite_otro":q.get("permite_otro",True),
          "respuestas":r,
          "perfil":p
        }

    return {
      "final":True,
      "caso":caso,
      "resultado":resultado(caso,r),
      "respuestas":r
    }

def seleccionar_caso(caso,respuestas=None,texto_inicial=""):
    if caso not in CASOS:raise ValueError("Trámite no válido.")
    r=dict(respuestas or {})
    r["caso"]=caso
    p=fusionar(_perfil_desde(r),extraer_perfil(texto_inicial))
    _guardar_perfil(r,p)
    return continuar(caso,r,"",texto_inicial)

def interpretar(servicio,texto,respuestas=None,pregunta_id=""):
    texto=str(texto or "").strip()
    r=dict(respuestas or {})
    if not texto:raise ValueError("No se recibió información.")
    p=fusionar(_perfil_desde(r),extraer_perfil(texto))
    _guardar_perfil(r,p)

    caso=r.get("caso")
    if caso in CASOS:
        return continuar(caso,r,pregunta_id,texto)

    caso=buscar_caso(texto,servicio)
    if caso:
        return seleccionar_caso(caso,r,texto)

    return {
      "final":False,
      "seleccionar":True,
      "servicio":servicio,
      "titulo":"¿Qué trámite necesitas?",
      "pregunta":"No quiero hacerte preguntas innecesarias. Elige la opción que más se parece a tu situación.",
      "opciones":catalogo(servicio),
      "respuestas":r,
      "perfil":p
    }
