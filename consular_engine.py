# consular_engine.py
import re,unicodedata
from copy import deepcopy
from datetime import date,datetime

APP="MEXICANO APOYA MEXICANO"
VERSION="6.0.0"

CONSULADO={
 "nombre":"Consulado de México","ciudad":"Miami",
 "direccion":"2555 Ponce de Leon Blvd., 4th Floor, Coral Gables, FL 33134",
 "telefono":"786-268-4900","citas":"1-424-309-0009","emergencia":"305-979-1534"
}

FUENTES={
 "pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/documentos-de-identidad/pasaporte",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
 "acta":"https://consulmex.sre.gob.mx/miami/index.php/registro-civil-y-poderes-notariales/acta-de-nacimient0",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "citas":"https://citas.sre.gob.mx"
}

CONTACTO={
 "telefono":"786-268-4900","citas":"1-424-309-0009",
 "emergencia":"305-979-1534","direccion":CONSULADO["direccion"]
}

TARIFAS={
 "pasaporte_1":44,"pasaporte_3":101,"pasaporte_6":137,
 "pasaporte_10":209,"matricula":41,"acta":20
}

ESTADOS_USA=[
 "alabama","alaska","arizona","arkansas","california","carolina del norte",
 "carolina del sur","colorado","connecticut","dakota del norte","dakota del sur",
 "delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa",
 "kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan",
 "minnesota","mississippi","missouri","montana","nebraska","nevada",
 "new hampshire","new jersey","nuevo mexico","new mexico","nueva york","new york",
 "north carolina","ohio","oklahoma","oregon","pennsylvania","rhode island",
 "tennessee","texas","utah","vermont","virginia","washington","west virginia",
 "wisconsin","wyoming"
]

ESTADOS_NOMBRE={
 "california":"California","texas":"Texas","florida":"Florida",
 "new mexico":"New Mexico","nuevo mexico":"New Mexico",
 "arizona":"Arizona","nevada":"Nevada",
 "carolina del norte":"North Carolina","north carolina":"North Carolina",
 "carolina del sur":"South Carolina","south carolina":"South Carolina",
 "new york":"New York","nueva york":"New York"
}

def normalizar(v):
 v=str(v or "").strip().lower()
 v=unicodedata.normalize("NFD",v)
 return "".join(c for c in v if unicodedata.category(c)!="Mn")

def texto(v):
 return str(v or "").strip()

def vacio(v):
 return not texto(v)

def si(v):
 return normalizar(v) in {"si","s","yes","y","verdadero","true","1"}

def no(v):
 return normalizar(v) in {"no","n","false","0"}

def no_se(v):
 return normalizar(v) in {"no se","nose","no sé","desconozco","no estoy seguro","no estoy segura"}

def unicos(xs):
 r=[]
 for x in xs or []:
  x=texto(x)
  if x and x not in r:r.append(x)
 return r

def fusionar(a,b):
 r=dict(a or {})
 r.update({k:v for k,v in (b or {}).items() if v not in ("",None,[])})
 return r

def perfil_vacio():
 return {
  "nombre":"","apellidos":"","nombre_completo":"",
  "fecha_nacimiento":"","edad":"","ano_nacimiento":"",
  "direccion":"","ciudad":"","estado":"","codigo_postal":"",
  "telefono":"","email":"","trabajo":"","ocupacion":"",
  "nacionalidad":"mexicana"
 }

def entero(v):
 try:return int(re.search(r"\d{1,3}",texto(v)).group())
 except:return None

def extraer_email(t):
 m=re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",t or "")
 return m.group(0) if m else ""

def extraer_telefono(t):
 m=re.search(r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}",t or "")
 return m.group(0) if m else ""

def extraer_zip(t):
 m=re.search(r"\b\d{5}(?:-\d{4})?\b",t or "")
 return m.group(0) if m else ""

def extraer_edad(t):
 m=re.search(r"(?:tengo|edad(?: de)?|años?|anos?)\s*[:\-]?\s*(\d{1,3})",normalizar(t))
 return int(m.group(1)) if m else None

def extraer_ano(t):
 m=re.search(r"\b(19\d{2}|20\d{2})\b",t or "")
 return m.group(1) if m else ""

def extraer_estado(t):
 n=normalizar(t)
 for k,v in ESTADOS_NOMBRE.items():
  if k in n:return v
 return ""

def extraer_nombre(t):
 patterns=[
  r"(?:me llamo|mi nombre es|nombre completo es)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]{3,})",
  r"(?:nombre)\s*[:\-]\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]{3,})"
 ]
 for p in patterns:
  m=re.search(p,t or "",re.I)
  if m:
   x=re.split(r"\b(?:nací|naci|vivo|tengo|trabajo|teléfono|telefono|email|correo|código|codigo)\b",
              m.group(1),flags=re.I)[0]
   return texto(x)
 return ""

def extraer_direccion(t):
 m=re.search(r"(?:vivo en|dirección|direccion|domicilio)\s*[:\-]?\s*(.+)",t or "",re.I)
 if not m:return ""
 x=re.split(r"\b(?:mi teléfono|mi telefono|teléfono|telefono|mi correo|correo|email|trabajo|tengo \d+ años?)\b",
            m.group(1),flags=re.I)[0]
 return texto(x).strip(" ,.")

def extraer_perfil(t,perfil=None):
 t=texto(t);p=fusionar(perfil_vacio(),perfil)
 if not t:return p
 nombre=extraer_nombre(t)
 if nombre and not p["nombre_completo"]:p["nombre_completo"]=nombre
 e=extraer_edad(t)
 if e is not None:p["edad"]=e
 z=extraer_zip(t)
 if z:p["codigo_postal"]=z
 tel=extraer_telefono(t)
 if tel:p["telefono"]=tel
 em=extraer_email(t)
 if em:p["email"]=em
 est=extraer_estado(t)
 if est:p["estado"]=est
 ano=extraer_ano(t)
 if ano:p["ano_nacimiento"]=ano
 dire=extraer_direccion(t)
 if dire:p["direccion"]=dire
 m=re.search(r"(?:trabajo|ocupación|ocupacion|soy)\s*[:\-]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ,.-]{2,})",t,re.I)
 if m:p["trabajo"]=texto(m.group(1))
 if p["nombre_completo"] and not p["nombre"] and not p["apellidos"]:
  partes=p["nombre_completo"].split()
  if len(partes)>=2:
   p["nombre"]=" ".join(partes[:-2]) if len(partes)>3 else partes[0]
   p["apellidos"]=" ".join(partes[-2:]) if len(partes)>2 else partes[1]
 return p

def validar_edad_fecha(p):
 edad=entero(p.get("edad"))
 f=texto(p.get("fecha_nacimiento"))
 if edad is None or not f:return []
 nums=re.findall(r"\d{1,4}",f)
 if len(nums)!=3:return []
 try:
  a,b,c=map(int,nums)
  if a>1900:
   ano,mes,dia=a,b,c
  else:
   dia,mes,ano=a,b,c
  nacimiento=date(ano,mes,dia)
  hoy=date.today()
  real=hoy.year-nacimiento.year-((hoy.month,hoy.day)<(nacimiento.month,nacimiento.day))
  if real!=edad:
   return [f"La fecha de nacimiento ({f}) y la edad ({edad}) no coinciden. Edad calculada: {real}."]
 except:pass
 return []

def P(id,texto_,**kw):
 d={"id":id,"pregunta":texto_}
 d.update(kw)
 return d

TRAMITES={}

def registrar(caso,nombre,descripcion,edad,questions,**info):
 TRAMITES[caso]={
  "caso":caso,"nombre":nombre,"descripcion":descripcion,
  "edad":edad,"preguntas":questions,**info
 }

IDENTIFICACION=[
 P("nombre_completo","¿Cuál es tu nombre y apellidos completos?",tipo="texto",required=True,grupo="identificacion"),
 P("fecha_nacimiento","¿Cuál es tu fecha de nacimiento?",tipo="texto",required=True,grupo="identificacion",placeholder="Día / mes / año"),
 P("edad","¿Qué edad tienes?",tipo="texto",required=True,grupo="identificacion",placeholder="Escribe tu edad"),
 P("direccion","¿Cuál es tu dirección donde vives?",tipo="texto",required=True,grupo="identificacion"),
 P("estado","¿En qué estado de Estados Unidos vives?",tipo="opciones",
   opciones=["California","New Mexico","Texas","Florida","Otro"],required=True,grupo="identificacion"),
 P("codigo_postal","¿Cuál es tu código postal?",tipo="texto",required=True,grupo="identificacion"),
 P("telefono","¿Cuál es tu número de teléfono?",tipo="texto",required=True,grupo="identificacion"),
 P("trabajo","¿Cuál es tu trabajo u ocupación?",tipo="texto",required=False,grupo="identificacion")
]

PASAPORTE_1=[
 P("nacionalidad","¿Tienes un documento original que pruebe tu nacionalidad mexicana?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("identificacion","¿Tienes una identificación original con fotografía?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("vigencia_pasaporte","¿Qué vigencia necesitas?",tipo="opciones",
   opciones=["1 año","3 años","6 años","10 años"],required=True,grupo="requisitos",
   aplica=lambda r:(entero(r.get("_edad")) or 18)>=18 or (entero(r.get("_edad")) or 0)>=3),
 P("cita","¿Ya tienes cita?",tipo="opciones",opciones=["Sí","No"],required=True,grupo="requisitos")
]

PASAPORTE_RENOVACION=[
 P("pasaporte_actual","¿Tienes tu pasaporte mexicano anterior?",tipo="opciones",
   opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("nacionalidad","¿Tienes tus documentos de nacionalidad disponibles si fueran necesarios?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("identificacion","¿Tienes una identificación original con fotografía?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("vigencia_pasaporte","¿Qué vigencia necesitas?",tipo="opciones",
   opciones=["1 año","3 años","6 años","10 años"],required=True,grupo="requisitos",
   aplica=lambda r:(entero(r.get("_edad")) or 18)>=18 or (entero(r.get("_edad")) or 0)>=3),
 P("cita","¿Ya tienes cita?",tipo="opciones",opciones=["Sí","No"],required=True,grupo="requisitos")
]

PASAPORTE_PERDIDO=[
 P("reporte","¿Tienes el reporte de la autoridad competente sobre la pérdida, robo o daño?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("nacionalidad","¿Tienes un documento original que pruebe tu nacionalidad mexicana?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("identificacion","¿Tienes una identificación original con fotografía?",
   tipo="opciones",opciones=["Sí","No","No sé"],required=True,grupo="requisitos"),
 P("vigencia_pasaporte","¿Qué vigencia necesitas?",tipo="opciones",
   opciones=["1 año","3 años","6 años","10 años"],required=True,grupo="requisitos",
   aplica=lambda r:(entero(r.get("_edad")) or 18)>=18 or (entero(r.get("_edad")) or 0)>=3),
 P("cita","¿Ya tienes cita?",tipo="opciones",opciones=["Sí","No"],required=True,grupo="requisitos")
]

registrar(
 "pasaporte_primera_vez","Pasaporte mexicano — primera vez",
 "Preparación personalizada para solicitar el pasaporte mexicano por primera vez.",
 "Todas las edades",PASAPORTE_1,
 documentos=["Prueba original de nacionalidad mexicana","Identificación original con fotografía","Comprobante de pago"],
 originales=["Documento original que pruebe nacionalidad mexicana","Identificación original con fotografía"],
 copias=[],
 pago="Tarifa según edad y vigencia. Confirma la tarifa oficial vigente.",
 cita="Se requiere cita y comparecencia personal.",
 vigencia="Menores de 3 años: 1 o 3 años. De 3 a 17 años: 3 o 6 años. Adultos: 3, 6 o 10 años.",
 entrega="La información oficial del Consulado de Miami indica entrega el mismo día, aproximadamente 2 horas, cuando no existe falla del sistema.",
 fuente=FUENTES["pasaporte"]
)

registrar(
 "pasaporte_renovacion","Pasaporte mexicano — renovación",
 "Preparación personalizada para renovar el pasaporte mexicano.",
 "Todas las edades",PASAPORTE_RENOVACION,
 documentos=["Pasaporte anterior","Comprobante de pago"],
 originales=["Pasaporte anterior"],
 copias=[],
 pago="Tarifa según edad y vigencia. Confirma la tarifa oficial vigente.",
 cita="Se requiere cita y comparecencia personal.",
 vigencia="Menores de 3 años: 1 o 3 años. De 3 a 17 años: 3 o 6 años. Adultos: 3, 6 o 10 años.",
 entrega="La información oficial del Consulado de Miami indica entrega el mismo día, aproximadamente 2 horas, cuando no existe falla del sistema.",
 fuente=FUENTES["pasaporte"]
)

registrar(
 "pasaporte_perdido_robo_mutilado","Pasaporte mexicano — perdido, robado o dañado",
 "Preparación personalizada cuando el pasaporte se perdió, fue robado o está dañado.",
 "Todas las edades",PASAPORTE_PERDIDO,
 documentos=["Reporte de la autoridad competente","Documento de nacionalidad","Identificación con fotografía","Comprobante de pago"],
 originales=["Reporte correspondiente","Documento original de nacionalidad","Identificación original con fotografía"],
 copias=[],
 pago="Tarifa según edad y vigencia. Confirma la tarifa oficial vigente.",
 cita="Se requiere cita y comparecencia personal.",
 vigencia="Depende de la edad.",
 entrega="La información oficial debe confirmarse para el caso particular.",
 fuente=FUENTES["pasaporte"]
)

registrar(
 "matricula_primera_vez","Matrícula consular — primera vez",
 "Preparación personalizada para obtener la matrícula consular por primera vez.",
 "Mexicanos que viven en Estados Unidos",
 [
  P("nacionalidad","¿Tienes un documento original que pruebe tu nacionalidad mexicana?",
    tipo="opciones",opciones=["Sí","No","No sé"],required=True),
  P("identificacion","¿Tienes una identificación original con fotografía?",
    tipo="opciones",opciones=["Sí","No","No sé"],required=True),
  P("domicilio","¿Tienes un comprobante de domicilio con tu nombre y dirección completa?",
    tipo="opciones",opciones=["Sí","No","Está a nombre de otra persona","No sé"],required=True),
  P("cita","¿Ya tienes cita?",tipo="opciones",opciones=["Sí","No"],required=True)
 ],
 documentos=["Documento original de nacionalidad mexicana","Identificación original con fotografía","Comprobante de domicilio","Comprobante de pago"],
 originales=["Documento de nacionalidad","Identificación con fotografía","Comprobante de domicilio"],
 copias=[],
 pago=f"${TARIFAS['matricula']} según tarifa publicada para Miami. Confirma tarifa vigente.",
 cita="Se requiere cita y comparecencia personal.",
 vigencia="5 años.",
 entrega="La información oficial del Consulado de Miami indica entrega el mismo día, aproximadamente 2 horas, cuando no existe falla del sistema.",
 fuente=FUENTES["matricula"]
)

registrar(
 "matricula_renovacion","Matrícula consular — renovación",
 "Preparación personalizada para renovar la matrícula consular.",
 "Mexicanos que viven en Estados Unidos",
 [
  P("matricula_actual","¿Tienes tu matrícula consular anterior?",
    tipo="opciones",opciones=["Sí","No","No sé"],required=True),
  P("cambio_domicilio","¿Cambiaste de domicilio desde tu última matrícula?",
    tipo="opciones",opciones=["Sí","No","No sé"],required=True),
  P("domicilio","¿Tienes comprobante de tu nuevo domicilio?",
    tipo="opciones",opciones=["Sí","No","No sé"],required=True,
    aplica=lambda r:si(r.get("cambio_domicilio"))),
  P("cita","¿Ya tienes cita?",tipo="opciones",opciones=["Sí","No"],required=True)
 ],
 documentos=["Matrícula consular anterior","Comprobante de domicilio si cambió la residencia","Comprobante de pago"],
 originales=["Matrícula consular anterior","Comprobante de domicilio si corresponde"],
 copias=[],
 pago=f"${TARIFAS['matricula']} según tarifa publicada para Miami. Confirma tarifa vigente.",
 cita="Se requiere cita y comparecencia personal.",
 vigencia="5 años.",
 entrega="La información oficial del Consulado de Miami indica entrega el mismo día, aproximadamente 2 horas, cuando no existe falla del sistema.",
 fuente=FUENTES["matricula"]
)

registrar(
 "acta_nacimiento_certificada","Acta de nacimiento mexicana — copia certificada",
 "Preparación personalizada para obtener una copia certificada del acta de nacimiento mexicana.",
 "Mexicanos de cualquier edad",
 [
  P("titular","¿El acta es para ti?",tipo="opciones",opciones=["Sí","No"],required=True),
  P("identificacion","¿Tienes una identificación oficial?",tipo="opciones",opciones=["Sí","No","No sé"],required=True),
  P("curp","¿Tienes tu CURP?",tipo="opciones",opciones=["Sí","No","No sé"],required=False),
  P("modalidad","¿Quieres hacerlo en línea o en el Consulado?",
    tipo="opciones",opciones=["En línea","En el Consulado"],required=True)
 ],
 documentos=["Identificación oficial","CURP si está disponible","Datos del acta","Comprobante de pago si corresponde"],
 originales=["Identificación oficial"],
 copias=[],
 pago=f"${TARIFAS['acta']} según tarifa publicada para Miami. Confirma tarifa vigente.",
 cita="Si acudes al Consulado, verifica el procedimiento y cita vigente. También existe opción oficial en línea.",
 vigencia="Copia certificada.",
 entrega="En línea: descarga e impresión desde el portal oficial. En Consulado: según procedimiento oficial vigente.",
 fuente=FUENTES["acta"],
 online="https://www.gob.mx/ActaNacimiento/"
)

PALABRAS={
 "pasaporte_primera_vez":["pasaporte primera vez","sacar pasaporte","nuevo pasaporte"],
 "pasaporte_renovacion":["renovar pasaporte","renovación pasaporte","renovacion pasaporte","pasaporte vencido"],
 "pasaporte_perdido_robo_mutilado":["pasaporte perdido","pasaporte robado","pasaporte dañado","pasaporte roto","perdi mi pasaporte","me robaron el pasaporte"],
 "matricula_primera_vez":["matrícula primera vez","matricula primera vez","sacar matrícula","sacar matricula"],
 "matricula_renovacion":["renovar matrícula","renovar matricula","renovación matrícula","renovacion matricula"],
 "acta_nacimiento_certificada":["acta de nacimiento","copia certificada","acta certificada"]
}

def puntuar_caso(t):
 n=normalizar(t);scores={k:0 for k in TRAMITES}
 for caso,pals in PALABRAS.items():
  scores[caso]=sum(1 for x in pals if normalizar(x) in n)
 if "pasaporte" in n:
  if any(x in n for x in ["perdido","robo","robado","dañado","roto"]):
   scores["pasaporte_perdido_robo_mutilado"]+=5
  elif any(x in n for x in ["renovar","renovacion","vencido"]):
   scores["pasaporte_renovacion"]+=5
  else:scores["pasaporte_primera_vez"]+=2
 if "matricula" in n:
  if any(x in n for x in ["renovar","renovacion"]):scores["matricula_renovacion"]+=5
  else:scores["matricula_primera_vez"]+=2
 return scores

def identificar_caso(t):
 s=puntuar_caso(t)
 return max(s,key=s.get) if s and max(s.values())>0 else ""

def normalizar_servicio(v):
 return identificar_caso(v) or texto(v)

def obtener_caso(caso):
 return TRAMITES.get(caso)

def pregunta_por_id(caso,pid):
 c=obtener_caso(caso)
 if not c:return None
 return next((q for q in c["preguntas"] if q["id"]==pid),None)

def _aplica(q,res):
 f=q.get("aplica")
 try:return bool(f(res)) if callable(f) else True
 except:return False

def perfil_completo(p):
 return all(texto(p.get(x)) for x in
  ["nombre_completo","fecha_nacimiento","edad","direccion","estado","codigo_postal","telefono"])

def preguntas_activas(caso,res):
 c=obtener_caso(caso)
 if not c:return []
 rr=dict(res or {})
 return [q for q in c["preguntas"] if _aplica(q,rr)]

def siguiente_pregunta(caso,respuestas):
 for q in preguntas_activas(caso,respuestas):
  if not texto(respuestas.get(q["id"])):
   return q
 return None

def pregunta_json(q,numero=0,total=0):
 if not q:return None
 d={k:v for k,v in q.items() if k!="aplica"}
 d["paso"]=numero
 d["total"]=total
 d["progreso"]=round((numero-1)/total*100,1) if total else 0
 return d

def interpretar_respuesta(q,v):
 v=texto(v)
 if not v:return v
 n=normalizar(v)
 if q.get("tipo")=="opciones":
  for o in q.get("opciones",[]):
   if n==normalizar(o):return o
  if n in {"si","s","yes","y"}:return "Sí"
  if n in {"no","n"}:return "No"
  if n in {"no se","nose"}:return "No sé"
 return v

def _perfil_desde(respuestas,perfil=None):
 p=fusionar(perfil_vacio(),perfil)
 for k in p:
  if texto(respuestas.get(k)):p[k]=respuestas[k]
 return p

def datos_personales(perfil):
 p=fusionar(perfil_vacio(),perfil)
 return [
  f"Nombre: {p['nombre_completo'] or 'Pendiente'}",
  f"Fecha de nacimiento: {p['fecha_nacimiento'] or 'Pendiente'}",
  f"Edad: {p['edad'] or 'Pendiente'}",
  f"Dirección: {p['direccion'] or 'Pendiente'}",
  f"Estado: {p['estado'] or 'Pendiente'}",
  f"Código postal: {p['codigo_postal'] or 'Pendiente'}",
  f"Teléfono: {p['telefono'] or 'Pendiente'}",
  f"Trabajo: {p['trabajo'] or 'No indicado'}"
 ]

def personas_del_caso(caso,p):
 edad=entero(p.get("edad"))
 if caso.startswith("pasaporte"):
  if edad is not None and edad<18:
   return ["La persona solicitante debe presentarse personalmente.","El adulto responsable debe confirmar los requisitos aplicables al menor."]
  return ["La persona solicitante debe presentarse personalmente."]
 if caso.startswith("matricula"):
  return ["La persona solicitante debe presentarse personalmente."]
 return ["La persona titular debe contar con la identificación o información necesaria para realizar el trámite."]

def documentos_del_caso(c):
 return list(c.get("documentos",[]))

def originales_del_caso(c):
 return list(c.get("originales",[]))

def copias_del_caso(c):
 return list(c.get("copias",[]))

def estado_requisito(v,negativo="ME FALTA"):
 n=normalizar(v)
 if not n:return "NO SÉ"
 if n in {"si","s","yes","y"}:return "TENGO"
 if n in {"no","n"}:return negativo
 if n in {"no se","nose"}:return "NO SÉ"
 if "otra persona" in n:return "DEBO REVISAR"
 return "DEBO REVISAR"

def requisitos_estado(caso,res,p):
 c=obtener_caso(caso)
 out=[]
 mapa={
  "nacionalidad":"Prueba de nacionalidad mexicana",
  "identificacion":"Identificación oficial/original con fotografía",
  "pasaporte_actual":"Pasaporte mexicano anterior",
  "reporte":"Reporte de la autoridad competente",
  "matricula_actual":"Matrícula consular anterior",
  "domicilio":"Comprobante de domicilio",
  "cita":"Cita",
  "curp":"CURP"
 }
 for q in preguntas_activas(caso,res):
  pid=q["id"]
  if pid not in mapa:continue
  v=res.get(pid)
  estado=estado_requisito(v)
  if pid=="curp" and normalizar(v)=="no":estado="DEBO REVISAR"
  out.append({
   "id":pid,"requisito":mapa[pid],"estado":estado,
   "respuesta":texto(v) or "Sin respuesta"
  })
 if caso=="matricula_primera_vez" and res.get("domicilio")=="Está a nombre de otra persona":
  for x in out:
   if x["id"]=="domicilio":x["estado"]="DEBO REVISAR"
 return out

def evaluar_requisitos(caso,res,p):
 falt=[]
 revisar=[]
 c=obtener_caso(caso)
 if not c:return ["Trámite no disponible."]
 for q in preguntas_activas(caso,res):
  v=res.get(q["id"])
  if q.get("required") and not texto(v):
   falt.append(q["pregunta"])
  elif q.get("required") and no(v):
   if q["id"]=="cita":falt.append("Debes solicitar o confirmar una cita.")
   elif q["id"]=="nacionalidad":falt.append("Te falta la prueba de nacionalidad mexicana.")
   elif q["id"]=="identificacion":falt.append("Te falta una identificación oficial/original con fotografía.")
   elif q["id"]=="pasaporte_actual":falt.append("Te falta el pasaporte mexicano anterior o debes confirmar si aplica otra vía.")
   elif q["id"]=="matricula_actual":falt.append("Te falta la matrícula consular anterior o debes confirmar la vía aplicable.")
   elif q["id"]=="domicilio":falt.append("Te falta el comprobante de domicilio.")
   elif q["id"]=="reporte":falt.append("Te falta el reporte de la autoridad competente.")
  elif q.get("required") and no_se(v):
   revisar.append(q["pregunta"])
 if caso=="matricula_primera_vez" and res.get("domicilio")=="Está a nombre de otra persona":
  revisar.append("Confirma qué comprobantes acepta el Consulado cuando el domicilio está a nombre de otra persona.")
 if caso=="matricula_renovacion" and si(res.get("cambio_domicilio")) and no(res.get("domicilio")):
  falt.append("Te falta el comprobante del nuevo domicilio.")
 if caso.startswith("pasaporte"):
  falt.extend(validar_edad_fecha(p))
 return unicos(falt),unicos(revisar)

def calcular_estado(caso,res,p):
 falt,revisar=evaluar_requisitos(caso,res,p)
 if falt:return "INCOMPLETO"
 if revisar:return "DEBO REVISAR"
 return "PREPARADO PARA REVISIÓN"

def informacion_cita(caso,c,res):
 return c.get("cita","Confirma el procedimiento oficial de cita.")

def informacion_pago(caso,c,res,p):
 edad=entero(p.get("edad"))
 if caso.startswith("pasaporte"):
  vig=normalizar(res.get("vigencia_pasaporte"))
  if edad is not None and edad<3:
   return "Tarifa según vigencia de 1 o 3 años. Confirma tarifa oficial vigente."
  if edad is not None and edad<18:
   if "6" in vig:return f"${TARIFAS['pasaporte_6']} para 6 años, según tarifa publicada para Miami. Confirma tarifa vigente."
   if "3" in vig:return f"${TARIFAS['pasaporte_3']} para 3 años, según tarifa publicada para Miami. Confirma tarifa vigente."
  if "10" in vig:return f"${TARIFAS['pasaporte_10']} para 10 años, según tarifa publicada para Miami. Confirma tarifa vigente."
  if "6" in vig:return f"${TARIFAS['pasaporte_6']} para 6 años, según tarifa publicada para Miami. Confirma tarifa vigente."
  if "3" in vig:return f"${TARIFAS['pasaporte_3']} para 3 años, según tarifa publicada para Miami. Confirma tarifa vigente."
  return "Tarifa según la vigencia elegida. Confirma la tarifa oficial vigente."
 return c.get("pago","Confirma la tarifa oficial vigente.")

def vigencia_del_caso(caso,c,p):
 return c.get("vigencia","Confirma la vigencia oficial.")

def entrega_del_caso(caso,c):
 return c.get("entrega","Confirma la entrega oficial.")

def situaciones_especiales(caso,res,p):
 s=[]
 edad=entero(p.get("edad"))
 if caso.startswith("pasaporte"):
  if edad is not None and edad<3:s.append("Para menores de 3 años existen vigencias específicas.")
  elif edad is not None and edad<18:s.append("Para menores de edad existen requisitos adicionales que deben confirmarse con el Consulado.")
  if caso=="pasaporte_renovacion" and no(res.get("pasaporte_actual")):
   s.append("Si no tienes el pasaporte anterior, confirma los requisitos aplicables antes de acudir.")
  if caso=="pasaporte_perdido_robo_mutilado":
   s.append("La pérdida, robo o daño requiere reporte de la autoridad competente y confirmación del procedimiento aplicable.")
 if caso=="matricula_primera_vez" and res.get("domicilio")=="Está a nombre de otra persona":
  s.append("Confirma las alternativas aceptadas cuando el comprobante de domicilio no está a tu nombre.")
 if caso=="acta_nacimiento_certificada" and res.get("modalidad")=="En línea":
  s.append("Puedes consultar la opción oficial en gob.mx/ActaNacimiento.")
 return unicos(s)

def acciones_del_caso(caso,res,p,falt,revisar):
 acciones=[]
 if falt:acciones.append("Completa o corrige lo que aparece como pendiente.")
 if revisar:acciones.append("Revisa los puntos marcados como DEBO REVISAR.")
 if not si(res.get("cita")) and caso!="acta_nacimiento_certificada":
  acciones.append("Solicita o confirma tu cita.")
 if caso=="acta_nacimiento_certificada" and res.get("modalidad")=="En línea":
  acciones.append("Consulta el portal oficial para realizar el trámite en línea.")
 acciones.append("Revisa tus datos antes de confirmar.")
 acciones.append("Revisa tu Hoja de Ruta antes de acudir.")
 acciones.append("Confirma la información oficial vigente.")
 return unicos(acciones)

def pantalla_resultado(caso,res,p):
 c=obtener_caso(caso)
 falt,revisar=evaluar_requisitos(caso,res,p)
 estados=requisitos_estado(caso,res,p)
 estado=calcular_estado(caso,res,p)
 return {
  "caso":caso,
  "nombre_tramite":c["nombre"],
  "estado":estado,
  "mensaje_estado":{
   "INCOMPLETO":"Hay cosas que todavía te faltan.",
   "DEBO REVISAR":"Hay información que debes revisar antes de confirmar.",
   "PREPARADO PARA REVISIÓN":"Tu preparación está lista para que la revises."
  }.get(estado,"Revisa tu preparación."),
  "datos":datos_personales(p),
  "personas":personas_del_caso(caso,p),
  "requisitos":documentos_del_caso(c),
  "originales":originales_del_caso(c),
  "copias":copias_del_caso(c),
  "requisitos_estado":estados,
  "faltantes":falt,
  "por_revisar":revisar,
  "confirmar":["Confirma la información oficial del Consulado correspondiente a tu lugar de residencia."],
  "pago":informacion_pago(caso,c,res,p),
  "cita":informacion_cita(caso,c,res),
  "vigencia":vigencia_del_caso(caso,c,p),
  "entrega":entrega_del_caso(caso,c),
  "especial":situaciones_especiales(caso,res,p),
  "acciones":acciones_del_caso(caso,res,p,falt,revisar),
  "fuentes":[{"nombre":"Información oficial","url":c.get("fuente","")}],
  "fuente":c.get("fuente",""),
  "online":c.get("online",""),
  "contacto":CONTACTO,
  "perfil":p,
  "borrador":True,
  "confirmado":False
 }

def resultado(caso,respuestas=None,perfil=None):
 respuestas=dict(respuestas or {})
 p=_perfil_desde(respuestas,perfil)
 respuestas["_edad"]=p.get("edad","")
 return pantalla_resultado(caso,respuestas,p)

def iniciar(texto_inicial="",perfil=None):
 p=extraer_perfil(texto_inicial,perfil)
 caso=identificar_caso(texto_inicial)
 if not caso:
  return {
   "ok":True,"pantalla":"inicio","perfil":p,
   "mensaje":"Primero identifica tus datos y después elige qué necesitas.",
   "tramites":catalogo()
  }
 return seleccionar_caso(caso,p)

def seleccionar_caso(caso,perfil=None,respuestas=None):
 if caso not in TRAMITES:raise ValueError("Trámite no disponible.")
 res=dict(respuestas or {})
 p=_perfil_desde(res,perfil)
 res["_edad"]=p.get("edad","")
 q=siguiente_pregunta(caso,res)
 if q:
  activos=preguntas_activas(caso,res)
  return {
   "ok":True,"caso":caso,"servicio":TRAMITES[caso]["nombre"],
   "perfil":p,"respuestas":res,
   "pregunta":pregunta_json(q,activos.index(q)+1,len(activos))
  }
 return {"ok":True,"caso":caso,"perfil":p,"respuestas":res,"resultado":resultado(caso,res,p)}

def continuar(caso,respuestas=None,perfil=None,pregunta_id="",respuesta=""):
 res=dict(respuestas or {})
 if pregunta_id:
  q=pregunta_por_id(caso,pregunta_id)
  if q:res[pregunta_id]=interpretar_respuesta(q,respuesta)
 p=extraer_perfil(res.get("texto",""),perfil)
 p=_perfil_desde(res,p)
 res["_edad"]=p.get("edad","")
 q=siguiente_pregunta(caso,res)
 if q:
  activos=preguntas_activas(caso,res)
  return {
   "ok":True,"caso":caso,"servicio":TRAMITES[caso]["nombre"],
   "perfil":p,"respuestas":res,
   "pregunta":pregunta_json(q,activos.index(q)+1,len(activos))
  }
 return {
  "ok":True,"caso":caso,"perfil":p,"respuestas":res,
  "resultado":resultado(caso,res,p)
 }

def interpretar(caso,texto_usuario="",respuestas=None,perfil=None):
 t=texto(texto_usuario)
 res=dict(respuestas or {})
 p=extraer_perfil(t,perfil)
 if not caso:caso=identificar_caso(t)
 if not caso:
  return {"ok":True,"pantalla":"seleccion","perfil":p,
          "mensaje":"Elige el trámite que necesitas.","tramites":catalogo()}
 q=siguiente_pregunta(caso,res)
 if q:
  val=interpretar_respuesta(q,t)
  res[q["id"]]=val
  res["texto"]=t
  p=extraer_perfil(t,p)
  return continuar(caso,res,p,q["id"],val)
 return resultado(caso,res,p)

def catalogo():
 return [
  {"caso":"pasaporte_primera_vez","nombre":"Pasaporte mexicano — primera vez","descripcion":"Para mexicanos de cualquier edad."},
  {"caso":"pasaporte_renovacion","nombre":"Pasaporte mexicano — renovación","descripcion":"Para renovar un pasaporte."},
  {"caso":"pasaporte_perdido_robo_mutilado","nombre":"Pasaporte mexicano — perdido, robado o dañado","descripcion":"Para estos casos especiales."},
  {"caso":"matricula_primera_vez","nombre":"Matrícula consular — primera vez","descripcion":"Para obtenerla por primera vez."},
  {"caso":"matricula_renovacion","nombre":"Matrícula consular — renovación","descripcion":"Para renovar la matrícula."},
  {"caso":"acta_nacimiento_certificada","nombre":"Acta de nacimiento mexicana — copia certificada","descripcion":"Para obtener una copia certificada."}
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
 return {
  "app":APP,"version":VERSION,
  "proposito":"Preparar al cliente contra los requisitos oficiales: identificar, comparar, detectar faltantes, revisar, corregir y confirmar antes del trámite.",
  "privacidad":"Los datos personales pueden mantenerse únicamente en el dispositivo del usuario mediante almacenamiento local del navegador; este motor no necesita una base de datos personal.",
  "tramites":catalogo(),
  "estados_requisito":["TENGO","ME FALTA","DEBO REVISAR","NO SÉ"],
  "fuentes":FUENTES,
  "regla":"No inventar requisitos. Confirmar siempre la información oficial vigente.",
  "flujo":["IDENTIFICAR","ELEGIR TRÁMITE","REUNIR INFORMACIÓN","COMPARAR REQUISITOS","REVISAR","CORREGIR","BORRADOR","CONFIRMAR","PDF FINAL"],
  "fuera_de_alcance":[
   "Naturalización","Apellido por matrimonio","Acta extemporánea",
   "Doble nacionalidad","OP-7","Poderes notariales","Cartilla militar",
   "Credencial para votar","Otros trámites jurídicamente complejos no incluidos"
  ]
 }

def caso_info(caso):
 return obtener_caso(caso)

def tramite_oficial(caso):
 c=obtener_caso(caso)
 return c.get("fuente","") if c else ""

def procesar(caso,respuestas=None,perfil=None):
 return resultado(caso,respuestas,perfil)

def validar_manual():
 errores=[]
 if len(TRAMITES)!=6:
  errores.append("El catálogo debe contener exactamente 6 trámites.")
 for caso,c in TRAMITES.items():
  if not c.get("preguntas"):errores.append(f"{caso}: sin preguntas.")
  if not c.get("fuente"):errores.append(f"{caso}: sin fuente oficial.")
 if "requisitos_estado" not in pantalla_resultado("acta_nacimiento_certificada",{},perfil_vacio()):
  errores.append("Falta motor de estados de requisitos.")
 return {"ok":not errores,"errores":errores}

MANUAL_VALIDACION=validar_manual()
MANUAL_RESUMEN={
 "version":VERSION,"tramites":len(TRAMITES),
 "validacion":MANUAL_VALIDACION["ok"]
}

def resumen_manual():
 return MANUAL_RESUMEN

__all__=[
 "APP","VERSION","CONSULADO","FUENTES","CONTACTO","TARIFAS","TRAMITES",
 "IDENTIFICACION","catalogo","obtener_catalogo","obtener_fuentes",
 "obtener_contacto","obtener_tarifas","obtener_manual","iniciar",
 "seleccionar_caso","continuar","interpretar","resultado","caso_info",
 "tramite_oficial","procesar","validar_manual","resumen_manual",
 "extraer_perfil","perfil_vacio","perfil_completo","pregunta_por_id",
 "siguiente_pregunta","pregunta_json","evaluar_requisitos",
 "requisitos_estado","validar_edad_fecha"
]
