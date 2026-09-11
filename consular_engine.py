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
("nombre","¿Cuál es tu nombre completo?","texto",1),("nacionalidad","¿Cómo acreditas tu nacionalidad mexicana?","texto",1),
("identidad","¿Qué identificación oficial con fotografía tienes?","texto",1),("cita","¿Ya tienes cita para el trámite?","si_no",1),
("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Documento ORIGINAL que acredite la nacionalidad mexicana","Identificación ORIGINAL con fotografía","Cita previa","Pago de la tarifa vigente"],
"originales":["Documento ORIGINAL de nacionalidad","Identificación ORIGINAL con fotografía"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa y forma de pago vigente antes de acudir.",
"importante":["La autoridad consular revisará la documentación presentada y puede solicitar información adicional."],
"entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos; el tiempo puede variar."
},
"pasaporte_renovacion":{
"titulo":"Renovación de pasaporte mexicano","servicio":"cita","fuente":FUENTES["pasaporte"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("pasaporte_actual","¿Tienes el pasaporte que vas a renovar?","si_no",1),
("cita","¿Ya tienes cita?","si_no",1),("naturalizado","¿Eres mexicano por naturalización?","si_no",0),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Presentación personal","Pasaporte que se desea renovar","Cita previa","Pago de la tarifa vigente"],
"originales":["Pasaporte que se desea renovar"],"personas":["La persona solicitante debe presentarse personalmente."],
"cita":["Debes contar con cita previa."],"pago":"Confirma la tarifa y forma de pago vigente.",
"importante":["Si eres mexicano por naturalización, puede corresponder presentar la carta de naturalización original o copia certificada correspondiente.","Pasaportes antiguos o casos especiales pueden requerir documentación adicional.","Un pasaporte de un año no puede renovarse como renovación ordinaria."],
"entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos."
},
"pasaporte_perdido":{
"titulo":"Pasaporte perdido, robado, destruido o mutilado","servicio":"cita","fuente":FUENTES["pasaporte"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("reporte","¿Ya tienes el reporte de la autoridad correspondiente?","si_no",1),
("cita","¿Ya tienes cita?","si_no",1),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Reporte ante la autoridad competente","Documentación correspondiente al trámite de primera vez","Cita previa","Pago vigente"],
"originales":["Reporte correspondiente","Documentos originales de nacionalidad e identidad que correspondan"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","importante":["La pérdida, robo, destrucción o mutilación puede requerir documentación de primera vez.","La autoridad consular puede solicitar información adicional."]
},
"pasaporte_menor":{
"titulo":"Pasaporte mexicano para un menor","servicio":"cita","fuente":FUENTES["pasaporte"],
"preguntas":[
("menor_nombre","¿Cuál es el nombre completo del menor?","texto",1),("menor_nacionalidad","¿Cómo se acredita la nacionalidad mexicana del menor?","texto",1),
("menor_identidad","¿Qué identificación tiene el menor?","texto",1),("padre1","¿Cuál es el nombre del padre, madre o tutor que acompañará al menor?","texto",1),
("padre1_id","¿Qué identificación tiene esa persona?","texto",1),("padre2","¿Se presentará el otro padre, madre o tutor?","si_no",1),
("op7","¿La autorización OP-7 ya está preparada o corresponde realizarla?","texto",1),("cita","¿Ya tienen cita?","si_no",1),
("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Menor de 18 años y no casado","Presencia del menor","Documentación ORIGINAL de nacionalidad del menor","Identificación ORIGINAL del menor","Identificaciones de los padres o tutores","Consentimiento de quienes ejercen la patria potestad mediante el procedimiento correspondiente","Cita previa","Pago vigente"],
"originales":["Documento ORIGINAL de nacionalidad del menor","Identificación ORIGINAL del menor","Identificaciones originales de padres o tutores"],
"personas":["El menor debe presentarse.","Deben presentarse los padres o tutores que correspondan."],"cita":["Debe existir cita para el trámite."],
"pago":"Confirma la tarifa vigente.","importante":["La separación o el divorcio por sí solos no eliminan la patria potestad.","Cuando un padre no puede acudir pueden existir procedimientos OP-7 mediante SRE o Consulado.","La autoridad consular prepara los formatos correspondientes y deben revisarse antes de firmar."]
},
"pasaporte_naturalizado":{
"titulo":"Pasaporte para mexicano por naturalización","servicio":"cita","fuente":FUENTES["pasaporte"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("naturalizacion","¿Tienes el original de tu carta de naturalización o copia certificada correspondiente?","si_no",1),
("identidad","¿Qué identificación oficial tienes?","texto",1),("cita","¿Ya tienes cita?","si_no",1),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Original de la carta de naturalización o copia certificada correspondiente","Identificación oficial","Cita previa","Pago vigente"],
"originales":["Carta de naturalización original o copia certificada correspondiente","Identificación original"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","importante":["La documentación puede variar en casos especiales."]
},
"pasaporte_conyuge":{
"titulo":"Pasaporte y apellido del cónyuge","servicio":"cita","fuente":FUENTES["pasaporte"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("matrimonio","¿Tienes el acta de matrimonio correspondiente?","si_no",1),
("cita","¿Ya tienes cita?","si_no",1),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Acta de matrimonio cuando corresponda","Documentación del pasaporte","Cita previa","Pago vigente"],
"originales":["Acta de matrimonio correspondiente","Documentos originales requeridos para el pasaporte"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","importante":["El apellido del cónyuge se incorpora en el apartado previsto para ello."]
},
"pasaporte_extemporanea":{
"titulo":"Pasaporte y registro de nacimiento extemporáneo","servicio":"cita","fuente":FUENTES["pasaporte"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("anio_nacimiento","¿En qué año naciste?","texto",1),
("registro_tardio","¿Tu registro de nacimiento fue realizado después del plazo correspondiente?","si_no",1),
("pruebas","¿Tienes documentación adicional que pueda acreditar tu identidad o nacimiento?","texto",0),("cita","¿Ya tienes cita?","si_no",1)],
"requisitos":["Documento de nacimiento y documentación de identidad correspondiente","Documentación complementaria cuando corresponda","Cita previa"],
"originales":["Documentos originales correspondientes al caso"],"personas":["La persona solicitante debe presentarse personalmente."],
"cita":["Debes contar con cita previa."],"pago":"Confirma la tarifa vigente.",
"importante":["En Miami existen periodos específicos para registros extemporáneos según el año de nacimiento.","Cuando se exceden esos periodos pueden requerirse pruebas complementarias.","La autoridad consular puede realizar verificaciones y esto puede retrasar el trámite."]
},
"matricula_primera_adulto":{
"titulo":"Primera matrícula consular para adulto","servicio":"cita","fuente":FUENTES["matricula"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("nacionalidad","¿Cómo acreditas tu nacionalidad mexicana?","texto",1),
("identidad","¿Qué identificación oficial con fotografía tienes?","texto",1),("direccion","¿Qué documento tienes para comprobar tu domicilio actual?","texto",1),
("cita","¿Ya tienes cita?","si_no",1),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Documento ORIGINAL de nacionalidad mexicana","Identificación ORIGINAL con fotografía","Comprobante ORIGINAL de domicilio con dirección completa","Cita previa","Pago vigente"],
"originales":["Documento ORIGINAL de nacionalidad","Identificación ORIGINAL con fotografía","Comprobante de domicilio"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","importante":["El comprobante de domicilio debe corresponder al domicilio actual.","Si el comprobante no está a nombre del solicitante existen alternativas según la situación."]
},
"matricula_renovacion":{
"titulo":"Renovación de matrícula consular","servicio":"cita","fuente":FUENTES["matricula"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("matricula_actual","¿Tienes tu matrícula consular actual?","si_no",1),
("cambio_domicilio","¿Cambiaste de domicilio desde la última matrícula?","si_no",1),("direccion","¿Tienes comprobante del nuevo domicilio?","texto",0),
("cita","¿Ya tienes cita?","si_no",1),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Matrícula consular actual","Comprobante de domicilio si cambió la residencia","Cita previa","Pago vigente"],
"originales":["Matrícula consular actual","Comprobante de domicilio si corresponde"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","importante":["El comprobante de domicilio se requiere cuando cambió la residencia."]
},
"matricula_perdida":{
"titulo":"Matrícula consular perdida o robada","servicio":"cita","fuente":FUENTES["matricula"],
"preguntas":[
("nombre","¿Cuál es tu nombre completo?","texto",1),("perdida","¿La matrícula fue perdida o robada?","texto",1),
("cita","¿Ya tienes cita?","si_no",1),("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Explicación de las circunstancias de pérdida o robo mediante el procedimiento del Consulado","Documentación de identidad y nacionalidad correspondiente","Cita previa","Pago vigente"],
"originales":["Documentos originales de nacionalidad e identidad que correspondan"],
"personas":["La persona solicitante debe presentarse personalmente."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","importante":["El Consulado requiere completar el formulario correspondiente explicando las circunstancias."]
},
"matricula_menor":{
"titulo":"Matrícula consular para un menor","servicio":"cita","fuente":FUENTES["matricula"],
"preguntas":[
("menor_nombre","¿Cuál es el nombre completo del menor?","texto",1),("menor_nacionalidad","¿Qué documento ORIGINAL tiene el menor para acreditar su nacionalidad mexicana?","texto",1),
("menor_identidad","¿Qué identificación ORIGINAL tiene el menor?","texto",1),("padre1","¿Cuál es el nombre del padre, madre o tutor que acompañará al menor?","texto",1),
("padre1_id","¿Qué identificación tiene esa persona?","texto",1),("padre2","¿Se presentará el otro padre, madre o tutor?","si_no",1),
("autorizacion","¿Ya está cubierta la autorización de quienes ejercen la patria potestad o tutela?","texto",1),("cita","¿Ya tienen cita?","si_no",1),
("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)],
"requisitos":["Menor de 18 años y no casado","Presencia del menor","Documento ORIGINAL de nacionalidad mexicana del menor","Identificación ORIGINAL del menor","Identificaciones correspondientes de los padres o tutores","Autorización de quienes ejercen la patria potestad o tutela","Cita previa","Pago vigente"],
"originales":["Documento ORIGINAL de nacionalidad del menor","Identificación ORIGINAL del menor","Identificaciones originales de padres o tutores"],
"personas":["El menor debe presentarse.","Deben presentarse los padres o tutores que correspondan."],"cita":["Debes contar con cita previa."],
"pago":"Confirma la tarifa vigente.","vigencia":"La matrícula consular tiene una vigencia de cinco años.",
"entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos; puede tomar alrededor de dos horas si no hay fallas del sistema.",
"importante":["La separación o divorcio no elimina por sí solo la patria potestad.","Cuando corresponda, deben cumplirse los procedimientos de autorización establecidos por la autoridad consular.","Revisa cuidadosamente los datos antes de que se imprima el documento."]
},
"acta_nacimiento_mexicana":{
"titulo":"Copia certificada del acta de nacimiento mexicana","servicio":"documento","fuente":FUENTES["acta"],
"preguntas":[
("nombre","¿Cuál es el nombre completo de la persona que aparece en el acta?","texto",1),("identidad","¿Qué identificación oficial tienes para acreditar que eres el titular del acta?","texto",1),
("curp","¿Tienes CURP?","texto",0),("registro","¿Sabes en qué estado de México fue registrada la persona?","texto",0),
("modalidad","¿Quieres obtenerla en el Consulado o prefieres consultar la opción en línea?","texto",1)],
"requisitos":["Identificación oficial que acredite que eres el titular del acta","Solicitud correspondiente cuando se realiza en Oficina Consular","Pago correspondiente"],
"opcionales":["CURP, si cuentas con ella"],
"originales":["Identificación oficial correspondiente"],
"personas":["Debe realizar el trámite la persona interesada/titular conforme a las condiciones aplicables."],
"cita":["Confirma directamente si el servicio que deseas realizar en el Consulado requiere cita antes de acudir."],
"copias":[],"pago":"La tarifa consular publicada para 2026 indica $20 USD por copia certificada de acta de nacimiento. Confirma el monto y forma de pago vigente antes de acudir.",
"importante":["También existe la opción de obtener la copia certificada en línea mediante gob.mx/ActaNacimiento.","Si eliges la opción en línea, no necesitas trasladarte al Consulado para obtener esa copia.","Si realizas el trámite en una Oficina Consular, debes llenar la solicitud correspondiente.","La disponibilidad de los datos del acta puede afectar la posibilidad de impresión."],
"en_linea":FUENTES["acta_online"]
},
"registro_nacimiento_extranjero":{
"titulo":"Registro de nacimiento de una persona nacida en el extranjero","servicio":"cita","fuente":FUENTES["registro_civil"],
"preguntas":[
("nombre","¿Cuál es el nombre completo de la persona que se registrará?","texto",1),("nacimiento","¿Tienes el acta o certificado de nacimiento extranjero?","si_no",1),
("padres","¿Tienes los documentos de identidad y nacionalidad de los padres?","si_no",1),("matrimonio","¿Los padres tienen acta de matrimonio si corresponde?","texto",0),
("cita","¿Ya tienes cita?","si_no",1)],
"requisitos":["Acta o certificado de nacimiento extranjero","Documentos de identidad y nacionalidad de los padres","Documentación adicional que corresponda","Cita previa"],
"originales":["Acta o certificado de nacimiento extranjero","Documentos originales de los padres"],
"personas":["La persona que se registra debe presentarse cuando corresponda.","Deben presentarse las personas que determine el procedimiento del Registro Civil."],
"cita":["El Registro Civil requiere cita previa según la información oficial."],"pago":"Confirma la tarifa vigente del servicio correspondiente.",
"importante":["La autoridad consular puede solicitar documentación adicional.","Los requisitos pueden depender de la situación familiar y de los documentos presentados."]
},
"poder_notarial":{
"titulo":"Poder notarial","servicio":"cita","fuente":FUENTES["citas"],
"preguntas":[
("nombre","¿Cuál es el nombre completo de quien otorgará el poder?","texto",1),("tipo_poder","¿Qué necesitas autorizar mediante el poder?","texto",1),
("beneficiario","¿Quién recibirá las facultades?","texto",1),("identidad","¿Tienes identificación oficial vigente?","texto",1),("cita","¿Ya tienes cita?","si_no",1)],
"requisitos":["Identificación oficial","Información clara sobre el poder que se desea otorgar","Datos completos de la persona que recibirá las facultades","Cita cuando corresponda"],
"originales":["Identificación oficial original","Documentos relacionados con el acto cuando correspondan"],
"personas":["La persona que otorgará el poder debe cumplir con la comparecencia que corresponda."],
"cita":["Confirma la cita y los requisitos específicos del poder."],"pago":"Confirma la tarifa vigente.",
"importante":["El contenido y los documentos adicionales dependen del tipo de poder."]
}
}

OPCIONES=[
("pasaporte_primera_vez","Pasaporte mexicano por primera vez","cita"),("pasaporte_renovacion","Renovar pasaporte","cita"),
("pasaporte_perdido","Pasaporte perdido, robado o dañado","cita"),("pasaporte_menor","Pasaporte para un menor","cita"),
("pasaporte_naturalizado","Pasaporte para mexicano por naturalización","cita"),("pasaporte_conyuge","Pasaporte y apellido del cónyuge","cita"),
("pasaporte_extemporanea","Pasaporte / nacimiento registrado fuera de plazo","cita"),("matricula_primera_adulto","Primera matrícula consular","cita"),
("matricula_renovacion","Renovar matrícula consular","cita"),("matricula_perdida","Matrícula perdida o robada","cita"),
("matricula_menor","Matrícula consular para un menor","cita"),("registro_nacimiento_extranjero","Registrar nacimiento de una persona nacida en el extranjero","cita"),
("acta_nacimiento_mexicana","Copia certificada del acta de nacimiento mexicana","documento"),("poder_notarial","Poder notarial","cita")
]

def normalizar(s):
 s=str(s or "").lower().strip()
 s=unicodedata.normalize("NFD",s)
 return "".join(c for c in s if unicodedata.category(c)!="Mn")

def vacio(v):
 return v is None or not str(v).strip()

def si(v):
 return normalizar(v) in ("si","yes","s","claro","correcto","tengo","ya","afirmativo","sí")

def no(v):
 return normalizar(v) in ("no","n","ninguno","ninguna","todavia no","aun no","aún no")

def extraer_perfil(texto):
 t=str(texto or "").strip();n=normalizar(t);p={}
 patrones={
  "nombre":[r"(?:me llamo|mi nombre es)\s+([^,.;\n]{2,100})"],
  "telefono":[r"(?:telefono|tel|celular|cel)\s*(?:es|:)?\s*([+()\d][\d ()-]{6,})"],
  "direccion":[r"(?:vivo en|mi direccion es|mi domicilio es|domicilio es)\s*:?\s*(.+?)(?=\s*,\s*(?:florida|texas|california|arizona|georgia|new york)\b|\s*,\s*\d{5}|$)"]
 }
 for k,rs in patrones.items():
  for x in rs:
   m=re.search(x,t,re.I)
   if m:p[k]=m.group(1).strip(" ,.")
 if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",t):
  p["email"]=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",t).group(0)
 m=re.search(r"\b\d{5}\b",t)
 if m:p["zip"]=m.group(0)
 estados={"alabama":"Alabama","arizona":"Arizona","california":"California","colorado":"Colorado","connecticut":"Connecticut","florida":"Florida","georgia":"Georgia","illinois":"Illinois","maryland":"Maryland","massachusetts":"Massachusetts","michigan":"Michigan","nevada":"Nevada","new jersey":"New Jersey","new york":"New York","north carolina":"North Carolina","pennsylvania":"Pennsylvania","south carolina":"South Carolina","texas":"Texas","virginia":"Virginia","washington":"Washington"}
 for k,v in estados.items():
  if k in n:p["estado"]=v;break
 if re.search(r"\b(?:mexicano|mexicana)\b",n):p["nacionalidad"]="Mexicana"
 if re.search(r"\bnaturalizad[oa]\b",n):p["naturalizado"]=True;p["nacionalidad"]="Mexicana por naturalización"
 if re.search(r"\b(?:menor|hijo|hija|niño|niña|nino|nina)\b",n):p["menor"]=True
 return p

def fusionar(a,b):
 r=dict(a or {})
 for k,v in (b or {}).items():
  if not vacio(v):r[k]=v
 return r

def guardar_respuesta(pid,v,p):
 if vacio(v):return p
 v=str(v).strip()
 campos={
  "nombre":"nombre","nacionalidad":"nacionalidad","identidad":"identidad","direccion":"direccion",
  "telefono":"telefono","tel":"telefono","celular":"telefono","email":"email","correo":"email",
  "zip":"zip","codigo_postal":"zip","estado":"estado"
 }
 if pid in campos:
  if pid in ("zip","codigo_postal"):
   m=re.search(r"\b\d{5}\b",v);p["zip"]=m.group(0) if m else v
  else:p[campos[pid]]=v
 return p

def enriquecer_respuesta(pid,v,r):
 r=dict(r or {})
 p=fusionar(r.get("_perfil",{}),extraer_perfil(v))
 p=guardar_respuesta(pid,v,p)
 r["_perfil"]=p
 if pid=="naturalizado" and si(v):p["naturalizado"]=True;p["nacionalidad"]="Mexicana por naturalización"
 if pid=="nacionalizacion" and si(v):p["naturalizado"]=True
 if pid=="modalidad":r["_modalidad"]=v
 if pid=="curp" and not no(v):p["curp"]=v
 if pid=="menor_nombre":p["menor_nombre"]=v
 if pid=="padre1":p["padre1"]=v
 if pid=="padre1_id":p["padre1_id"]=v
 return r

def buscar_caso(texto,servicio=None):
 n=normalizar(texto)
 if not n:return None
 reglas=[
 ("matricula_menor",["matricula","menor"],["hijo","hija","nino","nina"]),("pasaporte_menor",["pasaporte","menor"],["hijo","hija","nino","nina"]),
 ("pasaporte_perdido",["pasaporte"],["perdido","perdi","robado","robo","danado","mutilado"]),("pasaporte_renovacion",["pasaporte"],["renovar","renovacion","vencer","vencido"]),
 ("pasaporte_naturalizado",["pasaporte"],["naturalizado","naturalizada","naturalizacion"]),("pasaporte_conyuge",["pasaporte"],["esposo","esposa","conyuge","apellido"]),
 ("pasaporte_extemporanea",["pasaporte","nacimiento"],["extemporaneo","tardio","fuera de plazo"]),("pasaporte_primera_vez",["pasaporte"],["primera vez","nuevo"]),
 ("matricula_perdida",["matricula"],["perdida","perdi","robada","robo"]),("matricula_renovacion",["matricula"],["renovar","renovacion","vencida"]),
 ("matricula_primera_adulto",["matricula"],["primera","nueva"]),("acta_nacimiento_mexicana",["acta","nacimiento"],["copia","certificada","acta mexicana"]),
 ("registro_nacimiento_extranjero",["nacimiento"],["extranjero","nacido","nacida","registrar"]),("poder_notarial",["poder"],["notarial","notario","otorgar"])
 ]
 mejor=None;pm=0
 for cid,grupos,extras in reglas:
  s=sum(2 for x in grupos if x in n)+sum(1 for x in extras if x in n)
  if servicio:s+=2 if CASOS[cid]["servicio"]==servicio else -3
  if s>pm:pm=s;mejor=cid
 return mejor if pm>=2 else None

def catalogo(servicio=None):
 return [{"id":i,"nombre":n} for i,n,s in OPCIONES if not servicio or s==servicio]

def obtener_caso(caso):return CASOS.get(caso)

def iniciar(servicio,respuestas=None,_extra=None):
 r=dict(respuestas or {});r["_perfil"]=fusionar(r.get("_perfil",{}),extraer_perfil(_extra or ""))
 return {"tipo":"catalogo","estado":"seleccionar","servicio":servicio,"pregunta":"¿Qué trámite necesitas preparar?","opciones":catalogo(servicio),"respuestas":r,"perfil":r.get("_perfil",{})}

def pregunta_actual(caso,r):
 c=obtener_caso(caso)
 if not c:return None
 for pid,preg,tipo,ob in c.get("preguntas",[]):
  if not vacio(r.get(pid)):continue
  if pid=="naturalizado" and r.get("_perfil",{}).get("naturalizado") is True:continue
  if pid=="padre2" and no(r.get(pid)):continue
  if pid=="curp":continue
  return {"pregunta_id":pid,"pregunta":preg,"tipo":tipo,"obligatoria":bool(ob)}
 return None

def opciones_pregunta(p):
 return [{"id":"Sí","nombre":"Sí"},{"id":"No","nombre":"No"},{"id":"No estoy seguro","nombre":"No estoy seguro"}] if p["tipo"]=="si_no" else []

def documento_estado(caso,r):
 c=obtener_caso(caso);tiene=[];falta=[];revisar=[]
 mapa={
  "nacionalidad":["nacionalidad","menor_nacionalidad","naturalizacion"],"identificacion":["identidad","menor_identidad","padre1_id"],
  "domicilio":["direccion"],"cita":["cita"],"pago":["pago"],"pasaporte":["pasaporte_actual"],"matricula":["matricula_actual"],
  "reporte":["reporte"],"nacimiento":["nacimiento"],"padres":["padres"],"matrimonio":["matrimonio"],"solicitud":["modalidad"]
 }
 opc=set(normalizar(x) for x in c.get("opcionales",[]))
 for req in c.get("requisitos",[]):
  nr=normalizar(req);keys=[]
  for clave,ids in mapa.items():
   if clave in nr:keys+=ids
  found=False;bad=False
  for pid in keys:
   v=r.get(pid)
   if not vacio(v):
    if no(v) or normalizar(v)=="no estoy seguro":bad=True
    else:found=True
  if found:tiene.append(req)
  elif bad:falta.append(req)
  else:revisar.append(req)
 for x in c.get("opcionales",[]):revisar.append(x)
 if caso=="matricula_menor" and no(r.get("padre2")):falta.append("Debe resolverse la autorización del padre, madre o tutor que no se presenta.")
 if caso=="pasaporte_menor" and no(r.get("padre2")):falta.append("Debe resolverse el consentimiento o procedimiento aplicable del padre, madre o tutor que no se presenta.")
 return {"tiene":list(dict.fromkeys(tiene)),"falta":list(dict.fromkeys(falta)),"revisar":list(dict.fromkeys(revisar))}

def personas(caso,r):
 c=obtener_caso(caso)
 if caso in ("pasaporte_menor","matricula_menor"):
  p=r.get("_perfil",{});a=r.get("menor_nombre") or p.get("menor_nombre");b=r.get("padre1")
  out=["MENOR: "+a if a else "MENOR: PENDIENTE DE COMPLETAR","PADRE/MADRE/TUTOR: "+b if b else "PADRE/MADRE/TUTOR: PENDIENTE DE COMPLETAR"]
  if si(r.get("padre2")):out.append("También debe presentarse el otro padre, madre o tutor, según corresponda.")
  elif no(r.get("padre2")):out.append("Debe resolverse la autorización correspondiente del padre, madre o tutor que no se presenta.")
  return out
 return c.get("personas",["PENDIENTE DE COMPLETAR"])

def acciones(caso,r,docs):
 c=obtener_caso(caso);a=[]
 if docs["falta"]:a.append("Completa o consigue los elementos que aparecen en LO QUE TE FALTA.")
 if caso=="acta_nacimiento_mexicana":
  mod=normalizar(r.get("modalidad"))
  if "linea" in mod or "internet" in mod or "online" in mod:a.append("Obtén la copia certificada mediante la opción oficial en línea.")
  else:a.append("Si realizas el trámite en el Consulado, lleva tu identificación y completa la solicitud correspondiente.")
 else:
  if c.get("cita"):a.append(c["cita"][0])
  a.append("Lleva los documentos originales indicados y confirma la tarifa vigente antes de acudir.")
 if not a:a.append("Reúne los documentos indicados y confirma los puntos pendientes antes de acudir.")
 return list(dict.fromkeys(a))

def resultado(caso,r):
 c=obtener_caso(caso);r=dict(r or {})
 r["_perfil"]=fusionar(r.get("_perfil",{}),extraer_perfil(" ".join(str(v) for v in r.values() if isinstance(v,str))))
 docs=documento_estado(caso,r)
 pendientes=[pid for pid,_,_,ob in c.get("preguntas",[]) if ob and vacio(r.get(pid)) and pid!="curp"]
 nivel="rojo" if pendientes or docs["falta"] else "amarillo" if docs["revisar"] else "verde"
 estado="PARECES LISTO" if nivel=="verde" else "NO VAYAS TODAVÍA" if nivel=="rojo" else "TE FALTA ALGO"
 imp=list(dict.fromkeys(c.get("importante",[])))
 if c.get("en_linea"):imp.append("OPCIÓN EN LÍNEA: "+c["en_linea"])
 perfil=r.get("_perfil",{})
 if caso in ("pasaporte_menor","matricula_menor"):imp.append("Revisa por separado la documentación del menor y la documentación de los padres o tutores.")
 return {
  "tipo":"resultado","estado":"resuelto","nivel":nivel,"estado_texto":estado,"caso":caso,
  "tramite":c["titulo"],"titulo":c["titulo"],"perfil":perfil,
  "personas_obligatorias":personas(caso,r),"requisitos_obligatorios":c.get("requisitos",[]),
  "opcionales":c.get("opcionales",[]),
  "documentos":[*[{"nombre":x,"estado":"tiene"} for x in docs["tiene"]],*[{"nombre":x,"estado":"falta"} for x in docs["falta"]],*[{"nombre":x,"estado":"revisar"} for x in docs["revisar"]]],
  "tiene":docs["tiene"],"falta":docs["falta"],"revisar":docs["revisar"],
  "acciones":acciones(caso,r,docs),"cita":c.get("cita",[]),"originales":c.get("originales",[]),
  "copias":c.get("copias",[]),"pago":c.get("pago","Confirma la tarifa vigente."),
  "revision":"Revisa cuidadosamente nombres, fechas, datos personales y documentos antes de firmar o imprimir.",
  "vigencia":c.get("vigencia"),"entrega":c.get("entrega"),"importante":imp,"especiales":imp,
  "confirma":"La autoridad consular puede verificar los documentos y solicitar información adicional.",
  "fuente":c.get("fuente",FUENTES["tarifas"]),"pendientes":pendientes,"checklist":docs,"respuestas":r
 }

def continuar(caso,respuestas=None,pregunta_id="",texto=""):
 c=obtener_caso(caso)
 if not c:return {"estado":"error","mensaje":"Trámite no encontrado."}
 r=dict(respuestas or {});r["_caso"]=caso
 if pregunta_id and texto:r[pregunta_id]=texto
 r=enriquecer_respuesta(pregunta_id,texto,r)
 q=pregunta_actual(caso,r)
 if q:return {"tipo":"pregunta","estado":"pregunta","caso":caso,"titulo":c["titulo"],"pregunta_id":q["pregunta_id"],"pregunta":q["pregunta"],"tipo_pregunta":q["tipo"],"obligatoria":q["obligatoria"],"opciones":opciones_pregunta(q),"respuestas":r,"perfil":r.get("_perfil",{})}
 return resultado(caso,r)

def seleccionar_caso(caso,respuestas=None,texto_inicial=""):
 r=dict(respuestas or {});r["_caso"]=caso
 r["_perfil"]=fusionar(r.get("_perfil",{}),extraer_perfil(texto_inicial))
 if texto_inicial:
  r=enriquecer_respuesta("",texto_inicial,r)
 return continuar(caso,r,"","")

def interpretar(servicio,texto,respuestas=None,pregunta_id=""):
 r=dict(respuestas or {});r["_perfil"]=fusionar(r.get("_perfil",{}),extraer_perfil(texto))
 if r.get("_caso") and pregunta_id:
  return continuar(r["_caso"],r,pregunta_id,texto)
 caso=r.get("_caso") or buscar_caso(texto,servicio)
 if caso:return seleccionar_caso(caso,r,texto)
 return {"tipo":"catalogo","estado":"seleccionar","servicio":servicio,"pregunta":"¿Qué trámite necesitas preparar?","opciones":catalogo(servicio),"respuestas":r,"perfil":r.get("_perfil",{})}
