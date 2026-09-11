import re,unicodedata

FUENTES={
 "pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/pasaportes",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "citas":"https://citas.sre.gob.mx"
}

CASOS={
"pasaporte_primera_vez":{
 "titulo":"Pasaporte mexicano por primera vez","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("nacionalidad","¿Cómo acreditas tu nacionalidad mexicana?","texto",1),
  ("identidad","¿Qué identificación oficial tienes?","texto",1),
  ("cita","¿Ya tienes cita para el trámite?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Documento ORIGINAL que acredite nacionalidad mexicana","Identificación ORIGINAL con fotografía","Cita previa","Pago de la tarifa vigente"],
 "originales":["Documento ORIGINAL de nacionalidad","Identificación ORIGINAL con fotografía"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa y forma de pago vigente antes de acudir.",
 "importante":["La persona solicitante debe presentarse personalmente."],
 "entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos; el tiempo puede variar."
},
"pasaporte_renovacion":{
 "titulo":"Renovación de pasaporte mexicano","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("nacionalidad","¿Cómo acreditas tu nacionalidad mexicana?","texto",0),
  ("pasaporte_actual","¿Tienes el pasaporte que vas a renovar?","si_no",1),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("naturalizado","¿Eres mexicano por naturalización?","si_no",0),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Presentación personal","Pasaporte que se desea renovar","Cita previa","Pago de la tarifa vigente"],
 "originales":["Pasaporte que se desea renovar"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa y forma de pago vigente.",
 "importante":["Pasaportes antiguos o casos especiales pueden requerir documentación adicional.","Un pasaporte de un año no puede renovarse como renovación ordinaria."],
 "entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos."
},
"pasaporte_perdido":{
 "titulo":"Pasaporte perdido, robado, destruido o mutilado","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("reporte","¿Ya tienes el reporte de la autoridad correspondiente?","si_no",1),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Reporte ante la autoridad competente","Documentación correspondiente al trámite de primera vez","Cita previa","Pago vigente"],
 "originales":["Reporte correspondiente","Documentos originales de nacionalidad e identidad que correspondan"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["La pérdida, robo, destrucción o mutilación puede requerir documentación de primera vez.","La autoridad consular puede solicitar información adicional."]
},
"pasaporte_menor":{
 "titulo":"Pasaporte mexicano para un menor","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("menor_nombre","¿Cuál es el nombre completo del menor?","texto",1),
  ("menor_nacionalidad","¿Cómo se acredita la nacionalidad mexicana del menor?","texto",1),
  ("menor_identidad","¿Qué identificación tiene el menor?","texto",1),
  ("padre1","¿Cuál es el nombre del padre, madre o tutor que acompañará al menor?","texto",1),
  ("padre1_id","¿Qué identificación tiene esa persona?","texto",1),
  ("padre2","¿Se presentará el otro padre, madre o tutor?","si_no",1),
  ("op7","¿La autorización OP-7 ya está preparada o corresponde realizarla?","texto",1),
  ("cita","¿Ya tienen cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Menor de 18 años y no casado","Presencia del menor","Documentación ORIGINAL de nacionalidad del menor","Identificación ORIGINAL del menor","Identificaciones de los padres o tutores","Consentimiento de quienes ejercen la patria potestad mediante el procedimiento correspondiente","Cita previa","Pago vigente"],
 "originales":["Documento ORIGINAL de nacionalidad del menor","Identificación ORIGINAL del menor","Identificaciones originales de padres o tutores"],
 "personas":["El menor debe presentarse.","Deben presentarse los padres o tutores que correspondan."],
 "cita":["Debe existir cita para el trámite."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["La separación o el divorcio por sí solos no eliminan la patria potestad.","Cuando un padre no puede acudir pueden existir procedimientos OP-7 mediante SRE o Consulado.","La autoridad consular prepara los formatos correspondientes y deben revisarse antes de firmar."]
},
"pasaporte_naturalizado":{
 "titulo":"Pasaporte para mexicano por naturalización","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("naturalizacion","¿Tienes el original de tu carta de naturalización o copia certificada correspondiente?","si_no",1),
  ("identidad","¿Qué identificación oficial tienes?","texto",1),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Original de la carta de naturalización o copia certificada correspondiente","Identificación oficial","Cita previa","Pago vigente"],
 "originales":["Carta de naturalización original o copia certificada correspondiente","Identificación original"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["La documentación puede variar en casos especiales o cuando el pasaporte anterior no permite una renovación ordinaria."]
},
"pasaporte_conyuge":{
 "titulo":"Pasaporte y apellido del cónyuge","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("matrimonio","¿Tienes el acta de matrimonio correspondiente?","si_no",1),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Acta de matrimonio cuando corresponda","Documentación del pasaporte","Cita previa","Pago vigente"],
 "originales":["Acta de matrimonio correspondiente","Documentos originales requeridos para el pasaporte"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["El pasaporte conserva los nombres y apellidos correspondientes y el apellido del cónyuge se incorpora en el apartado previsto para ello."]
},
"pasaporte_extemporanea":{
 "titulo":"Pasaporte y registro de nacimiento extemporáneo","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("anio_nacimiento","¿En qué año naciste?","texto",1),
  ("registro_tardio","¿Tu registro de nacimiento fue realizado después del plazo correspondiente?","si_no",1),
  ("pruebas","¿Tienes documentación adicional que pueda acreditar tu identidad o nacimiento?","texto",0),
  ("cita","¿Ya tienes cita?","si_no",1)
 ],
 "requisitos":["Documento de nacimiento y documentación de identidad correspondiente","Documentación complementaria cuando corresponda","Cita previa"],
 "originales":["Documentos originales correspondientes al caso"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["En Miami existen periodos específicos para registros extemporáneos según el año de nacimiento.","Cuando se exceden esos periodos pueden requerirse pruebas complementarias.","La autoridad consular puede realizar verificaciones electrónicas o por escrito y esto puede retrasar el trámite."]
},
"matricula_primera_adulto":{
 "titulo":"Primera matrícula consular para adulto","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("nacionalidad","¿Cómo acreditas tu nacionalidad mexicana?","texto",1),
  ("identidad","¿Qué identificación oficial con fotografía tienes?","texto",1),
  ("direccion","¿Qué documento tienes para comprobar tu domicilio actual?","texto",1),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Documento ORIGINAL de nacionalidad mexicana","Identificación ORIGINAL con fotografía","Comprobante ORIGINAL de domicilio con dirección completa","Cita previa","Pago vigente"],
 "originales":["Documento ORIGINAL de nacionalidad","Identificación ORIGINAL con fotografía","Comprobante de domicilio"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["El comprobante de domicilio debe corresponder al domicilio actual.","Si el comprobante no está a nombre del solicitante existen alternativas según la relación con la persona titular del domicilio."]
},
"matricula_renovacion":{
 "titulo":"Renovación de matrícula consular","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("matricula_actual","¿Tienes tu matrícula consular actual?","si_no",1),
  ("cambio_domicilio","¿Cambiaste de domicilio desde la última matrícula?","si_no",1),
  ("direccion","¿Tienes comprobante del nuevo domicilio?","texto",0),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Matrícula consular actual","Comprobante de domicilio si cambió la residencia","Cita previa","Pago vigente"],
 "originales":["Matrícula consular actual","Comprobante de domicilio si corresponde"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["El comprobante de domicilio se requiere cuando cambió la residencia."]
},
"matricula_perdida":{
 "titulo":"Matrícula consular perdida o robada","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  ("nombre","¿Cuál es tu nombre completo?","texto",1),
  ("perdida","¿La matrícula fue perdida o robada?","texto",1),
  ("cita","¿Ya tienes cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Explicación de las circunstancias de pérdida o robo mediante el procedimiento del Consulado","Documentación de identidad y nacionalidad correspondiente","Cita previa","Pago vigente"],
 "originales":["Documentos originales de nacionalidad e identidad que correspondan"],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["El Consulado requiere completar el formulario correspondiente explicando las circunstancias.","El sistema puede impedir la expedición de una nueva matrícula si el formulario requerido no ha sido completado."]
},
"matricula_menor":{
 "titulo":"Matrícula consular para un menor","servicio":"cita","fuente":FUENTES["matricula"],
 "preguntas":[
  ("menor_nombre","¿Cuál es el nombre completo del menor?","texto",1),
  ("menor_nacionalidad","¿Qué documento ORIGINAL tiene el menor para acreditar su nacionalidad mexicana?","texto",1),
  ("menor_identidad","¿Qué identificación ORIGINAL tiene el menor?","texto",1),
  ("padre1","¿Cuál es el nombre del padre, madre o tutor que acompañará al menor?","texto",1),
  ("padre1_id","¿Qué identificación tiene esa persona?","texto",1),
  ("padre2","¿Se presentará el otro padre, madre o tutor?","si_no",1),
  ("autorizacion","¿Ya está cubierta la autorización de quienes ejercen la patria potestad o tutela?","texto",1),
  ("cita","¿Ya tienen cita?","si_no",1),
  ("pago","¿Ya confirmaste la tarifa vigente?","si_no",0)
 ],
 "requisitos":["Menor de 18 años y no casado","Presencia del menor","Documento ORIGINAL de nacionalidad mexicana del menor","Identificación ORIGINAL del menor","Identificaciones correspondientes de los padres o tutores","Autorización de quienes ejercen la patria potestad o tutela","Cita previa","Pago vigente"],
 "originales":["Documento ORIGINAL de nacionalidad del menor","Identificación ORIGINAL del menor","Identificaciones originales de padres o tutores"],
 "personas":["El menor debe presentarse.","Deben presentarse los padres o tutores, según corresponda."],
 "cita":["Debes contar con cita previa."],
 "pago":"Confirma la tarifa vigente.",
 "vigencia":"La matrícula consular tiene una vigencia de cinco años.",
 "entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos; puede tomar alrededor de dos horas si no hay fallas del sistema.",
 "importante":["La separación o divorcio no elimina por sí solo la patria potestad.","Cuando corresponda, deben cumplirse los procedimientos de autorización establecidos por la autoridad consular.","Revisa cuidadosamente los datos antes de que se imprima el documento."]
},
"registro_nacimiento_extranjero":{
 "titulo":"Registro de nacimiento de una persona nacida en el extranjero","servicio":"cita","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es el nombre completo de la persona que se registrará?","texto",1),
  ("nacimiento","¿Tienes el acta o certificado de nacimiento extranjero?","si_no",1),
  ("padres","¿Tienes los documentos de identidad y nacionalidad de los padres?","si_no",1),
  ("matrimonio","¿Los padres tienen acta de matrimonio si corresponde?","texto",0),
  ("cita","¿Ya tienes cita?","si_no",1)
 ],
 "requisitos":["Acta o certificado de nacimiento extranjero","Documentos de identidad y nacionalidad de los padres","Documentación adicional que corresponda","Cita previa"],
 "originales":["Acta o certificado de nacimiento extranjero","Documentos originales de los padres"],
 "cita":["Confirma la cita y conserva la confirmación."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["Dependiendo del lugar de expedición pueden requerirse legalización o apostilla y traducción.","La autoridad consular puede solicitar documentación adicional."]
},
"acta_nacimiento_mexicana":{
 "titulo":"Acta de nacimiento mexicana","servicio":"documento","fuente":FUENTES["pasaporte"],
 "preguntas":[
  ("nombre","¿Cuál es el nombre completo de la persona?","texto",1),
  ("curp","¿Tienes CURP o datos suficientes para localizar el registro?","texto",0),
  ("registro","¿Sabes en qué estado de México fue registrada la persona?","texto",1)
 ],
 "requisitos":["Datos suficientes para localizar el registro de nacimiento"],
 "originales":["Datos o documentos disponibles que permitan identificar correctamente el registro"],
 "cita":["Confirma si el servicio que necesitas requiere cita."],
 "pago":"Confirma el costo vigente del servicio correspondiente.",
 "importante":["La información necesaria depende del tipo de acta o copia que se solicite."]
},
"poder_notarial":{
 "titulo":"Poder notarial","servicio":"cita","fuente":FUENTES["citas"],
 "preguntas":[
  ("nombre","¿Cuál es el nombre completo de quien otorgará el poder?","texto",1),
  ("tipo_poder","¿Qué necesitas autorizar mediante el poder?","texto",1),
  ("beneficiario","¿Quién recibirá las facultades?","texto",1),
  ("identidad","¿Tienes identificación oficial vigente?","texto",1),
  ("cita","¿Ya tienes cita?","si_no",1)
 ],
 "requisitos":["Identificación oficial","Información clara sobre el poder que se desea otorgar","Datos completos de la persona que recibirá las facultades","Cita cuando corresponda"],
 "originales":["Identificación oficial original","Documentos relacionados con el acto cuando correspondan"],
 "cita":["Confirma la cita y los requisitos específicos del poder."],
 "pago":"Confirma la tarifa vigente.",
 "importante":["El contenido y los documentos adicionales dependen del tipo de poder."]
}
}

OPCIONES=[
 {"id":"pasaporte_primera_vez","nombre":"Pasaporte mexicano por primera vez","servicio":"cita"},
 {"id":"pasaporte_renovacion","nombre":"Renovar pasaporte","servicio":"cita"},
 {"id":"pasaporte_perdido","nombre":"Pasaporte perdido, robado o dañado","servicio":"cita"},
 {"id":"pasaporte_menor","nombre":"Pasaporte para un menor","servicio":"cita"},
 {"id":"pasaporte_naturalizado","nombre":"Pasaporte para mexicano por naturalización","servicio":"cita"},
 {"id":"pasaporte_conyuge","nombre":"Pasaporte y apellido del cónyuge","servicio":"cita"},
 {"id":"pasaporte_extemporanea","nombre":"Pasaporte / nacimiento registrado fuera de plazo","servicio":"cita"},
 {"id":"matricula_primera_adulto","nombre":"Primera matrícula consular","servicio":"cita"},
 {"id":"matricula_renovacion","nombre":"Renovar matrícula consular","servicio":"cita"},
 {"id":"matricula_perdida","nombre":"Matrícula perdida o robada","servicio":"cita"},
 {"id":"matricula_menor","nombre":"Matrícula consular para un menor","servicio":"cita"},
 {"id":"registro_nacimiento_extranjero","nombre":"Registrar nacimiento de una persona nacida en el extranjero","servicio":"cita"},
 {"id":"acta_nacimiento_mexicana","nombre":"Acta de nacimiento mexicana","servicio":"documento"},
 {"id":"poder_notarial","nombre":"Poder notarial","servicio":"cita"}
]

def normalizar(s):
 s=str(s or "").lower().strip()
 s=unicodedata.normalize("NFD",s)
 return "".join(c for c in s if unicodedata.category(c)!="Mn")

def vacio(v):
 return v is None or not str(v).strip()

def texto_si(v):
 return normalizar(v) in ("si","sí","yes","s","claro","correcto","tengo","ya","afirmativo")

def texto_no(v):
 return normalizar(v) in ("no","n","ninguno","ninguna","todavia no","aun no","aún no")

def extraer_perfil(texto):
 t=str(texto or "")
 n=normalizar(t)
 p={}
 m=re.search(r"(?:me llamo|mi nombre es|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{3,80})(?=,|\.|;| y |$)",t,re.I)
 if m:p["nombre"]=m.group(1).strip()
 m=re.search(r"(?:telefono|tel|celular|cel)\s*(?:es|:)?\s*([+()\d][\d ()-]{6,})",t,re.I)
 if m:p["telefono"]=m.group(1).strip()
 m=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",t)
 if m:p["email"]=m.group(0)
 m=re.search(r"\b(\d{5})\b",t)
 if m:p["zip"]=m.group(1)
 estados=["Alabama","Arizona","California","Florida","Georgia","Illinois","Nevada","New Jersey","New York","North Carolina","South Carolina","Texas","Virginia","Washington","Colorado","Connecticut","Maryland","Massachusetts","Michigan","Pennsylvania"]
 for e in estados:
  if normalizar(e) in n:
   p["estado"]=e
   break
 m=re.search(r"(?:vivo en|vivo|direccion|dirección|domicilio)\s+(?:en\s+)?(.+?)(?=,?\s+(?:florida|texas|california|new york|arizona|georgia)\b|,\s*\d{5}|$)",t,re.I)
 if m:p["direccion"]=m.group(1).strip(" ,.")
 if re.search(r"\b(mexicano|mexicana|mexico|mexicana naturalizada|naturalizado|naturalizada)\b",n):
  p["nacionalidad"]="Mexicana"
 if "naturaliz" in n:
  p["naturalizado"]=True
 if re.search(r"\b(menor|hijo|hija|nino|nina|niño|niña)\b",n):
  p["menor"]=True
 return p

def fusionar(a,b):
 r=dict(a or {})
 for k,v in (b or {}).items():
  if not vacio(v):
   r[k]=v
 return r

def buscar_caso(texto,servicio=None):
 n=normalizar(texto)
 if not n:return None
 reglas=[
  ("matricula_menor",["matricula","menor"],["hijo","hija","nino","nina"]),
  ("pasaporte_menor",["pasaporte","menor"],["hijo","hija","nino","nina"]),
  ("pasaporte_perdido",["pasaporte"],["perdido","perdi","robado","robo","danado","dañado","mutilado"]),
  ("pasaporte_renovacion",["pasaporte"],["renovar","renovacion","renovación","vencer","vencido"]),
  ("pasaporte_naturalizado",["pasaporte"],["naturalizado","naturalizada","naturalizacion","naturalización"]),
  ("pasaporte_conyuge",["pasaporte"],["esposo","esposa","conyuge","cónyuge","apellido"]),
  ("pasaporte_extemporanea",["pasaporte","nacimiento"],["extemporaneo","extemporánea","tardio","tardío","fuera de plazo"]),
  ("pasaporte_primera_vez",["pasaporte"],["primera vez","nuevo"]),
  ("matricula_perdida",["matricula"],["perdida","perdí","perdi","robada","robo"]),
  ("matricula_renovacion",["matricula"],["renovar","renovacion","renovación","vencida"]),
  ("matricula_primera_adulto",["matricula"],["primera","nueva"]),
  ("registro_nacimiento_extranjero",["nacimiento"],["extranjero","nacido","nacida","registrar"]),
  ("acta_nacimiento_mexicana",["acta","nacimiento"],["acta","copia"]),
  ("poder_notarial",["poder"],["notarial","notario","otorgar"])
 ]
 mejor=None;puntaje=0
 for cid,grupos,extras in reglas:
  score=sum(2 for x in grupos if x in n)+sum(1 for x in extras if x in n)
  if servicio:
   if CASOS[cid]["servicio"]==servicio:score+=2
   else:score-=3
  if score>puntaje:
   puntaje=score;mejor=cid
 return mejor if puntaje>=2 else None

def catalogo(servicio=None):
 return [
  {"id":x["id"],"nombre":x["nombre"]}
  for x in OPCIONES if not servicio or x["servicio"]==servicio
 ]

def obtener_caso(caso):
 return CASOS.get(caso)

def iniciar(servicio,respuestas=None,_extra=None):
 opciones=catalogo(servicio)
 return {"tipo":"catalogo","estado":"seleccionar","servicio":servicio,"pregunta":"¿Qué trámite necesitas preparar?","opciones":opciones,"respuestas":respuestas or {}}

def seleccionar_caso(caso,respuestas=None):
 c=obtener_caso(caso)
 if not c:return {"estado":"error","mensaje":"Trámite no encontrado."}
 r=dict(respuestas or {})
 p=extraer_perfil(" ".join(str(v) for v in r.values() if isinstance(v,str)))
 r["_perfil"]=fusionar(r.get("_perfil",{}),p)
 return continuar(caso,r,"","")

def pregunta_actual(caso,respuestas):
 c=obtener_caso(caso)
 if not c:return None
 r=respuestas or {}
 for pid,pregunta,tipo,obligatoria in c.get("preguntas",[]):
  if pid in r and not vacio(r.get(pid)):continue
  if pid=="naturalizado" and r.get("_perfil",{}).get("naturalizado") is True:continue
  if pid=="menor_nombre" and not r.get("_perfil",{}).get("menor") and caso not in ("pasaporte_menor","matricula_menor"):continue
  if pid=="padre2" and texto_no(r.get("padre2")):continue
  return {"pregunta_id":pid,"pregunta":pregunta,"tipo":tipo,"obligatoria":bool(obligatoria)}
 return None

def opciones_pregunta(p):
 if p["tipo"]=="si_no":
  return [{"id":"Sí","nombre":"Sí"},{"id":"No","nombre":"No"},{"id":"No estoy seguro","nombre":"No estoy seguro"}]
 return []

def documento_estado(caso,respuestas):
 c=obtener_caso(caso)
 tiene=[];falta=[];revisar=[]
 for req in c.get("requisitos",[]):
  n=normalizar(req)
  encontrado=False
  for k,v in respuestas.items():
   if k.startswith("_"):continue
   if vacio(v):continue
   vv=normalizar(v)
   if any(z in vv for z in ["si","tengo","ya","presento","original"]):
    if ("nacionalidad" in n and k in ("nacionalidad","menor_nacionalidad")) or ("identificacion" in n and k in ("identidad","menor_identidad","padre1_id")) or ("domicilio" in n and k=="direccion"):
     encontrado=True
  if encontrado:tiene.append(req)
  else:
   if any(k in n for k in ["cita","pago"]) and any(normalizar(str(v)) in ("no","no estoy seguro") for v in respuestas.values()):
    falta.append(req)
   else:revisar.append(req)
 if caso=="matricula_menor":
  if texto_no(respuestas.get("padre2")):
   falta.append("Debe resolverse la autorización del padre, madre o tutor que no se presenta.")
 return {"tiene":tiene,"falta":falta,"revisar":revisar}

def personas(caso,r):
 p=[]
 perfil=r.get("_perfil",{})
 if caso in ("pasaporte_menor","matricula_menor"):
  mn=r.get("menor_nombre") or perfil.get("nombre")
  pa=r.get("padre1")
  pb=r.get("padre2")
  if mn:p.append("MENOR: "+mn)
  else:p.append("MENOR: nombre pendiente de completar.")
  if pa:p.append("PADRE/MADRE/TUTOR: "+pa)
  else:p.append("PADRE/MADRE/TUTOR: nombre pendiente de completar.")
  if texto_si(pb):p.append("También debe presentarse el otro padre, madre o tutor, según corresponda.")
  elif texto_no(pb):p.append("Debe resolverse la autorización correspondiente del padre, madre o tutor que no se presenta.")
 return p

def resultado(caso,respuestas):
 c=obtener_caso(caso)
 perfil=fusionar(respuestas.get("_perfil",{}),extraer_perfil(" ".join(str(v) for v in respuestas.values() if isinstance(v,str))))
 docs=documento_estado(caso,respuestas)
 pendientes=[]
 for pid,_,_,oblig in c.get("preguntas",[]):
  if oblig and vacio(respuestas.get(pid)):pendientes.append(pid)
 nivel="verde"
 if pendientes or docs["falta"]:nivel="rojo"
 elif docs["revisar"]:nivel="amarillo"
 estado="PARECES LISTO" if nivel=="verde" else "NO VAYAS TODAVÍA" if nivel=="rojo" else "TE FALTA ALGO"
 especiales=list(c.get("importante",[]))
 if caso in ("matricula_menor","pasaporte_menor"):
  especiales.append("Revisa por separado la documentación del menor y la documentación de los padres o tutores.")
 if caso=="matricula_menor" and texto_no(respuestas.get("padre2")):
  especiales.append("Si un padre, madre o tutor no se presenta, confirma el procedimiento de autorización aplicable antes de acudir.")
 p=personas(caso,respuestas)
 return {
  "tipo":"resultado","estado":"resuelto","nivel":nivel,"estado_texto":estado,
  "caso":caso,"tramite":c["titulo"],"titulo":c["titulo"],
  "perfil":perfil,"personas_obligatorias":p,
  "requisitos_obligatorios":c.get("requisitos",[]),
  "documentos":[
   *[{"nombre":x,"estado":"tiene"} for x in docs["tiene"]],
   *[{"nombre":x,"estado":"falta"} for x in docs["falta"]],
   *[{"nombre":x,"estado":"revisar"} for x in docs["revisar"]]
  ],
  "prepara":" ".join(c.get("importante",[])) or "Reúne los documentos indicados y confirma cualquier punto pendiente antes de acudir.",
  "cita":c.get("cita",[]),"originales":c.get("originales",[]),
  "copias":c.get("copias",[]),"pago":c.get("pago","Confirma la tarifa vigente."),
  "revision":"Revisa cuidadosamente nombres, fechas, datos personales y documentos antes de firmar o imprimir.",
  "vigencia":c.get("vigencia"),"entrega":c.get("entrega"),
  "importante":especiales,"especiales":especiales,
  "confirma":"La autoridad consular puede verificar los documentos y solicitar información adicional.",
  "fuente":c.get("fuente",FUENTES["tarifas"]),
  "pendientes":pendientes,"checklist":docs
 }

def continuar(caso,respuestas=None,pregunta_id="",texto=""):
 c=obtener_caso(caso)
 if not c:return {"estado":"error","mensaje":"Trámite no encontrado."}
 r=dict(respuestas or {})
 if pregunta_id and texto:r[pregunta_id]=texto
 perfil=fusionar(r.get("_perfil",{}),extraer_perfil(texto))
 r["_perfil"]=fusionar(r.get("_perfil",{}),perfil)
 q=pregunta_actual(caso,r)
 if q:
  return {
   "tipo":"pregunta","estado":"pregunta","caso":caso,
   "titulo":c["titulo"],"pregunta_id":q["pregunta_id"],
   "pregunta":q["pregunta"],"tipo_pregunta":q["tipo"],
   "obligatoria":q["obligatoria"],"opciones":opciones_pregunta(q),
   "respuestas":r,"perfil":r.get("_perfil",{})
  }
 return {**resultado(caso,r),"respuestas":r}

def interpretar(servicio,texto,respuestas=None,pregunta_id=""):
 r=dict(respuestas or {})
 perfil=fusionar(r.get("_perfil",{}),extraer_perfil(texto))
 r["_perfil"]=perfil
 if pregunta_id and texto and r.get("_caso"):
  return continuar(r["_caso"],r,pregunta_id,texto)
 caso=r.get("_caso") or buscar_caso(texto,servicio)
 if caso:
  r["_caso"]=caso
  return continuar(caso,r,"","")
 return {
  "tipo":"catalogo","estado":"seleccionar","servicio":servicio,
  "pregunta":"¿Qué trámite necesitas preparar?","opciones":catalogo(servicio),
  "respuestas":r,"perfil":perfil
 }
