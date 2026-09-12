# MEXICANO APOYA MEXICANO — MOTOR CONSULAR
import re,unicodedata
from typing import Any
from urllib.parse import quote_plus

OFICIAL_MIAMI="https://consulmex.sre.gob.mx/miami"
FUENTES={
 "pasaporte":f"{OFICIAL_MIAMI}/index.php/pasaportes",
 "matricula":f"{OFICIAL_MIAMI}/index.php/matricula-consular",
 "acta":f"{OFICIAL_MIAMI}/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
 "doble":f"{OFICIAL_MIAMI}/index.php/registro-civil-y-poderes-notariales/doble-nacionalidad",
 "tarifas":f"{OFICIAL_MIAMI}/index.php/tarifas-consulares",
 "citas":"https://miconsulado.sre.gob.mx",
 "acta_online":"https://www.gob.mx/ActaNacimiento/"
}

def limpio(x):
    if x is None:return ""
    return " ".join(str(x).strip().split())

def clave(x):
    x=limpio(x).lower()
    return "".join(c for c in unicodedata.normalize("NFD",x) if unicodedata.category(c)!="Mn")

def si(x):
    return clave(x) in {"si","s","yes","y","tengo","tengo todo","correcto","listo","ya"}

def no(x):
    return clave(x) in {"no","n","todavia no","me falta","no tengo","pendiente"}

def opcion(i,t):
    return {"id":i,"texto":t}

# ============================================================
# CATÁLOGO PRINCIPAL — NO ELIMINAR SERVICIOS EXISTENTES
# ============================================================
SERVICIOS={
 "cita":{
  "titulo":"QUIERO PREPARAR UN TRÁMITE",
  "pregunta":"¿Qué trámite necesitas preparar?",
  "casos":[
   opcion("pasaporte","Pasaporte mexicano"),
   opcion("matricula","Matrícula consular"),
   opcion("matricula_menor","Matrícula consular para un menor"),
   opcion("acta","Copia certificada del acta de nacimiento mexicana"),
   opcion("doble","Registro de nacimiento por doble nacionalidad"),
   opcion("op7","Permiso OP-7 para un menor"),
   opcion("cartilla","Cartilla del Servicio Militar Nacional"),
   opcion("poderes","Poderes notariales y actuaciones notariales"),
   opcion("credencial","Credencial para votar desde el extranjero"),
   opcion("otro","Otro trámite consular")
  ]
 },
 "documento":{
  "titulo":"NECESITO UN DOCUMENTO",
  "pregunta":"¿Qué documento necesitas?",
  "casos":[
   opcion("pasaporte","Pasaporte mexicano"),
   opcion("matricula","Matrícula consular"),
   opcion("matricula_menor","Matrícula consular para un menor"),
   opcion("acta","Copia certificada del acta de nacimiento mexicana"),
   opcion("credencial","Credencial para votar desde el extranjero"),
   opcion("cartilla","Cartilla del Servicio Militar Nacional"),
   opcion("otro","Otro documento")
  ]
 }
}

# ============================================================
# MATRIZ CONSULAR COMPLETA
# ============================================================
TRAMITES={
"acta":{
 "titulo":"Copia certificada del acta de nacimiento mexicana",
 "personas":["La persona interesada o quien corresponda debe realizar la solicitud."],
 "req":[
  "Identificación oficial que acredite que eres el titular del acta.",
  "CURP, si cuentas con ella.",
  "Solicitud correspondiente cuando se realiza en Oficina Consular.",
  "Pago correspondiente."
 ],
 "originales":["Identificación oficial correspondiente."],
 "copias":[],
 "cita":["Confirma si el servicio que necesitas requiere cita."],
 "pago":"La tarifa publicada por el Consulado de Miami para 2026 indica $20 USD por copia certificada de acta de nacimiento. Confirma el monto y forma de pago vigente antes de acudir.",
 "hacer":[
  "Completa primero la información que aparezca como pendiente.",
  "Ten a mano tu identificación oficial.",
  "Prepara los datos necesarios para localizar el acta.",
  "Si tienes CURP, tenla disponible.",
  "Si realizas el trámite en una Oficina Consular, llena la solicitud correspondiente.",
  "También puedes consultar, descargar e imprimir la copia certificada en línea mediante gob.mx/ActaNacimiento."
 ],
 "importante":[
  "La CURP puede ayudar cuando está disponible, pero no se debe considerar un requisito obligatorio si no cuentas con ella.",
  "También existe la opción oficial de obtener la copia certificada en línea.",
  "Si eliges la opción en línea, no necesitas trasladarte al Consulado para obtener esa copia.",
  "La disponibilidad de los datos del acta puede afectar la posibilidad de impresión.",
  "La autoridad consular puede verificar los documentos y solicitar información adicional."
 ],
 "fuente":FUENTES["acta"],
 "online":FUENTES["acta_online"],
 "entrega":"La modalidad presencial y la modalidad en línea tienen procedimientos distintos. Confirma cuál utilizarás."
},
"matricula":{
 "titulo":"Matrícula consular",
 "personas":["La persona solicitante debe presentarse personalmente ante la Oficina Consular."],
 "req":[
  "Cita previamente agendada.",
  "Acreditar la nacionalidad mexicana con ORIGINAL de un documento válido.",
  "Acreditar la identidad con ORIGINAL de una identificación oficial con fotografía cuyos datos coincidan.",
  "Comprobante de domicilio ORIGINAL a nombre del solicitante, con dirección completa.",
  "Pago correspondiente."
 ],
 "nacionalidad":[
  "Acta de nacimiento.",
  "Certificado de nacionalidad mexicana.",
  "Declaratoria de nacionalidad mexicana por nacimiento.",
  "Carta de naturalización.",
  "Pasaporte mexicano vigente."
 ],
 "identidad":[
  "Pasaporte mexicano vigente.",
  "Credencial para votar vigente.",
  "Cartilla o Precartilla del Servicio Militar Nacional.",
  "Cédula profesional.",
  "Título profesional.",
  "Certificado de nacionalidad mexicana.",
  "Declaratoria de nacionalidad mexicana.",
  "Carta de naturalización.",
  "Licencia de conducir mexicana con medidas de seguridad.",
  "Licencia de conducir de Estados Unidos.",
  "Identificación oficial emitida por autoridad de Estados Unidos.",
  "Tarjeta de Residencia de Estados Unidos.",
  "Certificado escolar con fotografía y sello oficial.",
  "Boleta certificada con fotografía y sello oficial.",
  "Credencial del IMSS, ISSSTE u otra institución mexicana."
 ],
 "domicilio":[
  "El comprobante debe estar a nombre del solicitante.",
  "Debe indicar número y nombre de la calle, número interior, ciudad y código postal.",
  "Si vives con un familiar, puede utilizarse el acta de nacimiento del familiar para acreditar el parentesco, según la información oficial.",
  "Si el comprobante está a nombre de otra persona y no vives con un familiar, consulta directamente al Consulado sobre la documentación aceptada."
 ],
 "originales":["Documento ORIGINAL de nacionalidad.","Documento ORIGINAL de identidad.","Comprobante ORIGINAL de domicilio."],
 "copias":[],
 "cita":["Cita previamente agendada antes de acudir."],
 "pago":"La tarifa publicada por el Consulado de Miami para 2026 indica $41 USD para Matrícula Consular. Confirma el monto y forma de pago vigente antes de acudir.",
 "hacer":[
  "Agenda tu cita.",
  "Prepara el ORIGINAL que acredita tu nacionalidad mexicana.",
  "Prepara el ORIGINAL que acredita tu identidad.",
  "Prepara tu comprobante de domicilio.",
  "Revisa que los nombres y datos coincidan.",
  "Revisa cuidadosamente la información antes de firmar."
 ],
 "importante":[
  "Si en tu identificación aparece el apellido de tu cónyuge, consulta la documentación que corresponde para acreditarlo.",
  "Los formatos de matrícula y autorización para menores son llenados por personal de la Oficina Consular; el solicitante debe revisarlos cuidadosamente cuando se los entreguen.",
  "La autoridad consular puede verificar los documentos y solicitar información adicional."
 ],
 "vigencia":"La matrícula consular tiene una vigencia de cinco años a partir de su expedición.",
 "entrega":"Una vez cumplidos los requisitos en la cita, la matrícula consular se entrega el mismo día; la información oficial señala que puede tomar alrededor de dos horas si no hay fallas del sistema.",
 "fuente":FUENTES["matricula"]
},
"matricula_menor":{
 "titulo":"Matrícula consular para un menor",
 "personas":[
  "El menor debe presentarse.",
  "Deben presentarse personalmente los padres o quienes ejerzan la patria potestad o tutela, según corresponda."
 ],
 "req":[
  "Cita previamente agendada.",
  "Documento ORIGINAL que acredite la nacionalidad mexicana del menor.",
  "Documento ORIGINAL que acredite la identidad del menor.",
  "Identificaciones y documentación correspondiente de los padres o tutores.",
  "Pago correspondiente."
 ],
 "nacionalidad":[
  "Acta de nacimiento del menor.",
  "Certificado de nacionalidad mexicana.",
  "Declaratoria de nacionalidad mexicana por nacimiento.",
  "Carta de naturalización.",
  "Pasaporte mexicano vigente."
 ],
 "identidad":[
  "Pasaporte mexicano vigente.",
  "Certificado escolar mexicano con fotografía y sello.",
  "Boleta certificada con fotografía y sello.",
  "Credencial de estudiante emitida por la institución educativa local.",
  "Constancia de grado de estudios con fotografía y sello.",
  "Identificación oficial emitida por autoridad de Estados Unidos.",
  "Tarjeta de Residencia de Estados Unidos.",
  "Para menores de 7 años, constancia con fotografía y sello de una institución médica o médico particular del lugar donde radica el menor."
 ],
 "originales":[
  "Documento ORIGINAL de nacionalidad del menor.",
  "Documento ORIGINAL de identidad del menor.",
  "Identificaciones correspondientes de los padres o tutores."
 ],
 "copias":[],
 "cita":["Cita previamente agendada.","El menor y quienes deban comparecer deben acudir personalmente."],
 "pago":"Confirma la tarifa consular vigente correspondiente a la matrícula del menor antes de acudir.",
 "hacer":[
  "Completa los datos personales que aparezcan pendientes.",
  "Prepara el ORIGINAL que acredita la nacionalidad del menor.",
  "Prepara el ORIGINAL que acredita su identidad.",
  "Prepara las identificaciones correspondientes de los padres o tutores.",
  "Confirma quién debe comparecer.",
  "Revisa los formatos antes de firmarlos."
 ],
 "importante":[
  "La separación o el divorcio de los padres no elimina por sí solo la patria potestad.",
  "Si existe una sentencia judicial sobre la patria potestad o sobre quién puede realizar el trámite, debe consultarse directamente con el Consulado.",
  "Los formatos de matrícula y autorización para menores son llenados por personal de la Oficina Consular.",
  "La autoridad consular puede verificar los documentos y solicitar información adicional."
 ],
 "vigencia":"La matrícula consular tiene una vigencia de cinco años.",
 "entrega":"La información oficial indica que, una vez cumplidos los requisitos, la matrícula consular se entrega el mismo día de la cita; puede tomar alrededor de dos horas si no hay fallas del sistema.",
 "fuente":FUENTES["matricula"]
},
"pasaporte":{
 "titulo":"Pasaporte mexicano",
 "personas":["La persona solicitante debe comparecer personalmente ante la Oficina Consular, de acuerdo con la modalidad del trámite."],
 "req":[
  "Cita correspondiente.",
  "Acreditación de nacionalidad mexicana mediante documento ORIGINAL aceptado.",
  "Identificación oficial vigente con fotografía.",
  "Documentación adicional cuando corresponda al caso.",
  "Pago de los derechos consulares."
 ],
 "originales":["Documento ORIGINAL que acredite la nacionalidad.","Identificación oficial vigente con fotografía.","Documentación adicional que corresponda al caso."],
 "copias":[],
 "cita":["Confirma y agenda la cita correspondiente antes de acudir."],
 "pago":"La tarifa depende de la vigencia del pasaporte y de las condiciones del trámite. Confirma la tarifa vigente antes de acudir.",
 "hacer":[
  "Completa tus datos personales.",
  "Prepara el ORIGINAL que acredita tu nacionalidad mexicana.",
  "Prepara una identificación oficial vigente con fotografía.",
  "Revisa si tu caso necesita documentación adicional.",
  "Agenda o confirma tu cita.",
  "Confirma el pago correspondiente."
 ],
 "importante":[
  "Los requisitos pueden variar según la situación concreta del solicitante.",
  "La autoridad consular puede verificar los documentos y solicitar información adicional."
 ],
 "fuente":FUENTES["pasaporte"]
},
"doble":{
 "titulo":"Registro de nacimiento por doble nacionalidad",
 "personas":["Deben presentarse las personas que correspondan al registro y los testigos cuando sean requeridos."],
 "req":[
  "Solicitud con los datos completos.",
  "Certificado de nacimiento de Estados Unidos y documentación correspondiente.",
  "Documentos que acrediten la nacionalidad mexicana de los padres.",
  "Identificaciones oficiales correspondientes.",
  "Documentación adicional según el caso."
 ],
 "originales":["Documentos originales que acrediten el nacimiento, nacionalidad e identidad de las personas que intervienen."],
 "copias":["Las copias requeridas dependen del caso y de las instrucciones del Consulado."],
 "cita":["Confirma y agenda la cita correspondiente."],
 "pago":"El registro de nacimiento por doble nacionalidad es gratuito; las copias certificadas tienen derechos consulares. Confirma los costos vigentes.",
 "hacer":[
  "Completa todos los datos de las personas que intervienen.",
  "Prepara los documentos originales.",
  "Prepara las copias que correspondan.",
  "Confirma quién debe presentarse.",
  "Agenda la cita y revisa las instrucciones del Consulado."
 ],
 "importante":[
  "La información necesaria puede variar según el caso.",
  "Por práctica consular pueden solicitarse documentos adicionales."
 ],
 "fuente":FUENTES["doble"]
},
"op7":{
 "titulo":"Permiso OP-7 para un menor",
 "personas":["Deben presentarse las personas que correspondan según la autorización y el trámite del menor."],
 "req":[
  "Documentación de identidad del menor.",
  "Documentación de identidad de los padres o quienes ejerzan la patria potestad o tutela.",
  "Información y autorización correspondiente.",
  "Cita cuando corresponda."
 ],
 "originales":["Identificaciones y documentos originales correspondientes al menor y a quienes comparezcan."],
 "copias":["Confirma directamente con el Consulado las copias necesarias para tu caso."],
 "cita":["Confirma la cita y la modalidad de atención antes de acudir."],
 "pago":"Confirma si existen derechos consulares aplicables a tu caso.",
 "hacer":["Completa los datos pendientes.","Prepara documentos originales.","Confirma quién debe comparecer.","Revisa la autorización antes de firmarla."],
 "importante":["La autoridad consular puede verificar los documentos y solicitar información adicional."],
 "fuente":f"{OFICIAL_MIAMI}/index.php/pasaportes"
},
"cartilla":{
 "titulo":"Cartilla del Servicio Militar Nacional",
 "personas":["La persona interesada debe acudir personalmente a la Oficina Consular."],
 "req":[
  "Acudir personalmente.",
  "Copia certificada del acta de nacimiento.",
  "Comprobante de domicilio en el extranjero.",
  "Documentación adicional que corresponda a la situación militar del interesado."
 ],
 "originales":["Documentos originales que correspondan al trámite."],
 "copias":["Copia certificada del acta de nacimiento y copia fotostática.","Copia del comprobante de domicilio cuando corresponda."],
 "cita":["Confirma directamente la modalidad y cita correspondiente."],
 "pago":"Confirma los derechos aplicables al servicio que vas a realizar.",
 "hacer":["Completa tus datos.","Prepara tu acta de nacimiento.","Prepara comprobante de domicilio.","Confirma los requisitos finales con el Consulado."],
 "importante":["La información oficial indica que los mexicanos varones de 18 a 40 años tienen obligación de cumplir con el Servicio Militar Nacional aun residiendo en el extranjero."],
 "fuente":FUENTES["cartilla"] if "cartilla" in FUENTES else f"{OFICIAL_MIAMI}/index.php/cartilla-militar"
},
"poderes":{
 "titulo":"Poderes notariales y actuaciones notariales",
 "personas":["La persona interesada debe comparecer según el acto que realizará."],
 "req":[
  "Cita correspondiente.",
  "Solicitud o formato de información correspondiente.",
  "Documentos originales de identidad y nacionalidad.",
  "Documentación relacionada con el acto notarial.",
  "Pago de los derechos consulares."
 ],
 "originales":["Identificación y documentos originales correspondientes al acto."],
 "copias":["Según el trámite pueden requerirse originales y copias legibles de los documentos."],
 "cita":["Agenda o confirma la cita correspondiente antes de acudir."],
 "pago":"Confirma el pago vigente y la forma de pago aceptada para tu actuación notarial.",
 "hacer":["Completa los datos pendientes.","Prepara originales y copias.","Prepara la documentación relacionada con el acto.","Confirma la cita y forma de pago."],
 "importante":["Los requisitos cambian según el tipo de actuación notarial. La autoridad consular puede solicitar información adicional."],
 "fuente":FUENTES["poderes"] if "poderes" in FUENTES else f"{OFICIAL_MIAMI}/index.php/poderes-notariales"
},
"credencial":{
 "titulo":"Credencial para votar desde el extranjero",
 "personas":["La persona solicitante debe presentarse conforme al procedimiento vigente."],
 "req":["Documento de nacionalidad mexicana aceptado.","Identificación correspondiente.","Comprobante de domicilio cuando corresponda.","Cita o procedimiento indicado por la autoridad."],
 "originales":["Documento original de nacionalidad e identificación correspondiente."],
 "copias":[],
 "cita":["Confirma el procedimiento y la cita aplicable antes de acudir."],
 "pago":"La credencial para votar desde el extranjero se tramita sin costo. Confirma el procedimiento vigente.",
 "hacer":["Completa tus datos.","Prepara los originales.","Confirma el procedimiento oficial.","Revisa todos los datos antes de firmar."],
 "importante":["La autoridad competente determina la aceptación de documentos y el resultado del trámite."],
 "fuente":f"{OFICIAL_MIAMI}/index.php/credencial-para-votar"
},
"otro":{
 "titulo":"Otro trámite consular",
 "personas":["PENDIENTE DE COMPLETAR"],
 "req":["Describe el trámite para identificar los requisitos específicos."],
 "originales":["PENDIENTE DE COMPLETAR"],
 "copias":["PENDIENTE DE COMPLETAR"],
 "cita":["Confirma directamente con el Consulado si necesitas cita."],
 "pago":"Confirma el costo vigente del servicio correspondiente.",
 "hacer":["Describe con claridad qué necesitas.","Completa los datos personales pendientes.","Confirma la información oficial antes de acudir."],
 "importante":["La autoridad consular puede verificar los documentos y solicitar información adicional."],
 "fuente":OFICIAL_MIAMI
}
}

# ============================================================
# PREGUNTAS: UNA POR PANTALLA
# ============================================================
def preguntas(caso):
    base=[
      ("nombre","¿Cuál es tu nombre completo?"),
      ("nacionalidad","¿Cuál es tu nacionalidad?"),
      ("telefono","¿Cuál es tu teléfono?"),
      ("direccion","¿Cuál es tu dirección en Estados Unidos?"),
      ("estado","¿En qué estado de Estados Unidos vives?"),
      ("zip","¿Cuál es tu ZIP Code?"),
      ("email","¿Cuál es tu correo electrónico?")
    ]
    if caso in {"matricula","matricula_menor","pasaporte"}:
        base += [
         ("tiene_nacionalidad","¿Tienes el documento original que acredita la nacionalidad mexicana?"),
         ("tiene_identidad","¿Tienes una identificación oficial vigente?"),
        ]
    if caso=="matricula":
        base += [("tiene_domicilio","¿Tienes un comprobante de domicilio a tu nombre?")]
    if caso=="matricula_menor":
        base += [
         ("tiene_nacionalidad_menor","¿Tienes el documento original que acredita la nacionalidad del menor?"),
         ("tiene_identidad_menor","¿Tienes el documento original que acredita la identidad del menor?"),
         ("padres_presentes","¿Pueden presentarse los padres o quienes ejerzan la patria potestad o tutela?")
        ]
    if caso=="acta":
        base += [
         ("tiene_identidad","¿Tienes una identificación oficial que permita acreditar que eres el titular del acta?"),
         ("tiene_datos_acta","¿Puedes proporcionar los datos necesarios para localizar el acta?"),
         ("tiene_pago","¿Estás preparado para pagar la tarifa correspondiente?")
        ]
    return [{"id":i,"pregunta":p,"tipo":"opciones" if i.startswith("tiene_") or i=="padres_presentes" else "texto","opciones":[opcion("si","Sí"),opcion("no","No")] if i.startswith("tiene_") or i=="padres_presentes" else []} for i,p in base]

def perfil_desde(res):
    return {
      "nombre":res.get("nombre",""),
      "nacionalidad":res.get("nacionalidad",""),
      "telefono":res.get("telefono",""),
      "direccion":res.get("direccion",""),
      "estado":res.get("estado",""),
      "zip":res.get("zip",""),
      "email":res.get("email","")
    }

def construir_resultado(caso,res):
    t=TRAMITES.get(caso,TRAMITES["otro"])
    tiene=[];falta=[];revisar=[]
    if caso=="acta":
        pares=[
         ("tiene_identidad","Identificación oficial que acredite que eres el titular del acta."),
         ("tiene_datos_acta","Solicitud con los datos necesarios para localizar el acta."),
         ("tiene_pago","Pago de la tarifa aplicable.")
        ]
    elif caso=="matricula":
        pares=[
         ("tiene_nacionalidad","Documento original que acredita la nacionalidad mexicana."),
         ("tiene_identidad","Identificación oficial vigente."),
         ("tiene_domicilio","Comprobante de domicilio a tu nombre.")
        ]
    elif caso=="matricula_menor":
        pares=[
         ("tiene_nacionalidad_menor","Documento original que acredita la nacionalidad del menor."),
         ("tiene_identidad_menor","Documento original que acredita la identidad del menor."),
         ("padres_presentes","Presentación de los padres o quienes ejerzan la patria potestad o tutela.")
        ]
    else:
        pares=[]
    for k,txt in pares:
        if si(res.get(k)):tiene.append(txt)
        elif no(res.get(k)):falta.append(txt)
        else:revisar.append(txt)
    for k in ("nombre","nacionalidad","telefono","direccion","estado","zip","email"):
        if not limpio(res.get(k)):revisar.append(f"Falta completar el dato personal: {k.replace('_',' ').title()}.")
    if not revisar:revisar=list(t.get("confirmar",[]))
    estado="LISTO PARA REVISAR" if not falta and not revisar else "TE FALTA ALGO"
    return {
      "estado":"resuelto","tipo":"resultado","estado_texto":estado,
      "nivel":"verde" if not falta and not revisar else "amarillo",
      "perfil":perfil_desde(res),"tramite":t["titulo"],"titulo":t["titulo"],
      "personas_obligatorias":t.get("personas",[]),"requisitos_obligatorios":t.get("req",[]),
      "checklist":{"tiene":tiene,"falta":falta,"revisar":revisar},
      "especiales":t.get("nacionalidad",[])+t.get("identidad",[])+t.get("domicilio",[]),
      "prepara":"\n".join(t.get("hacer",[])) or "Completa la información pendiente y confirma los requisitos oficiales.",
      "cita":t.get("cita",[]),"originales":t.get("originales",[]),"copias":t.get("copias",[]),
      "pago":t.get("pago","Confirma el costo vigente del servicio correspondiente."),
      "revision":"Revisa cuidadosamente nombre, apellidos, fechas, lugar de nacimiento y demás datos antes de firmar o imprimir.",
      "vigencia":t.get("vigencia",""),"entrega":t.get("entrega",""),
      "importante":t.get("importante",[]),"fuente":t.get("fuente",OFICIAL_MIAMI),
      "online":t.get("online",""),"confirma":"La autoridad consular puede verificar los documentos y solicitar información adicional."
    }

def iniciar(servicio):
    servicio=clave(servicio)
    s=SERVICIOS.get(servicio)
    if not s:return {"tipo":"error","estado":"error","mensaje":"Servicio no disponible."}
    return {"tipo":"catalogo","catalogo":True,"servicio":servicio,"titulo":s["titulo"],"pregunta":s["pregunta"],"opciones":s["casos"]}

def seleccionar_caso(servicio,caso,respuestas=None):
    caso=clave(caso)
    if caso not in TRAMITES:return {"tipo":"error","estado":"error","mensaje":"No se encontró el trámite solicitado."}
    return continuar(servicio,caso,"inicio",respuestas or {})

def interpretar(servicio,caso,pregunta_id,texto,respuestas=None):
    respuestas=dict(respuestas or {})
    if pregunta_id:respuestas[pregunta_id]=limpio(texto)
    return continuar(servicio,caso,pregunta_id,respuestas)

def continuar(servicio,caso,pregunta_id,respuestas=None):
    caso=clave(caso);respuestas=dict(respuestas or {})
    qs=preguntas(caso)
    if pregunta_id=="inicio":idx=0
    else:
        idx=next((i+1 for i,q in enumerate(qs) if q["id"]==pregunta_id),0)
    while idx<len(qs):
        q=qs[idx]
        if q["id"] not in respuestas or not limpio(respuestas.get(q["id"])):
            return {
             "tipo":"pregunta","estado":"preguntando","servicio":servicio,"caso":caso,
             "pregunta_id":q["id"],"titulo":TRAMITES[caso]["titulo"],
             "pregunta":q["pregunta"],"opciones":q["opciones"],"respuestas":respuestas,
             "perfil":perfil_desde(respuestas)
            }
        idx+=1
    return construir_resultado(caso,respuestas)
