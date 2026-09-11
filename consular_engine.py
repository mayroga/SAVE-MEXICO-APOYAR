import re
from copy import deepcopy

FUENTES={
 "pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/pasaporte",
 "pasaporte_gob":"https://www.gob.mx/sre/acciones-y-programas/tramite-de-pasaporte-8014",
 "citas":"https://citas.sre.gob.mx",
 "tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
 "nacimiento":"https://www.gob.mx/tramites/ficha/registro-de-nacimiento-en-el-extranjero/SRE92",
 "poder":"https://consulmex.sre.gob.mx/miami/index.php/poderes-notariales",
 "documentacion":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/dconsular"
}

def normalizar(t):
 t=(t or "").lower().strip()
 t=t.translate(str.maketrans("áàäâéèëêíìïîóòöôúùüûñ","aaaaeeeeiiiioooouuuun"))
 return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9\s]"," ",t)).strip()

def palabras(t): return set(normalizar(t).split())

def afirmativo(v): return normalizar(v) in {"si","sí","s","yes","true","1"}
def negativo(v): return normalizar(v) in {"no","n","false","0"}
def incierto(v): return not afirmativo(v) and not negativo(v)

def coincide(t,frases):
 t=normalizar(t);w=palabras(t)
 for f in frases:
  f=normalizar(f)
  if f in t:return True
  z=set(f.split())
  if len(z)>=2 and len(z&w)>=max(2,len(z)-1):return True
 return False

def q(i,t,o=None):
 d={"id":i,"texto":t}
 if o:d["opciones"]=o
 return d

SI=["Sí","No","No estoy seguro"]
CASOS=[
{
"id":"pasaporte_primera_vez","servicio":"cita","titulo":"Sacar mi pasaporte por primera vez",
"grupos":[["pasaporte"],["primera vez","sacar","obtener","solicitar","nuevo"]],
"preguntas":[
 q("menor","¿El pasaporte es para una persona menor de 18 años?",["Sí","No"]),
 q("nacionalidad","¿Tienes un documento ORIGINAL que compruebe la nacionalidad mexicana?",SI),
 q("identidad","¿Tienes una identificación ORIGINAL con fotografía cuyos datos coincidan con tu documento de nacionalidad?",SI),
 q("sin_identidad","Si no tienes identificación con fotografía, ¿necesitas revisar la alternativa de Constancia de Identidad?",["Sí","No","No estoy seguro"]),
 q("acta_extemporanea","¿Tu acta de nacimiento fue registrada después del período permitido?",["Sí","No","No estoy seguro"]),
 q("nacionalizado","¿Eres mexicano por naturalización?",["Sí","No"]),
 q("conyuge","¿Tu identificación tiene el apellido de tu cónyuge o quieres que aparezca en tu pasaporte?",["Sí","No"]),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para la primera expedición debes acudir personalmente con cita, acreditar nacionalidad mexicana e identidad mediante documentos originales y pagar la tarifa vigente.",
"pago":"Debes pagar la tarifa consular vigente. Confirma el monto y la forma de pago antes de acudir.",
"confirma":"Los datos de nacionalidad e identidad deben coincidir. El personal consular prepara la solicitud OP5; tú debes revisar cuidadosamente los datos antes de firmar.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"pasaporte_renovacion","servicio":"cita","titulo":"Renovar mi pasaporte",
"grupos":[["pasaporte"],["renovar","renovacion","renovación","vencer","vencido","expirado","caducado","canjear"]],
"preguntas":[
 q("menor","¿El pasaporte es para una persona menor de 18 años?",["Sí","No"]),
 q("pasaporte_anterior","¿Tienes el pasaporte que quieres renovar?",["Sí","No"]),
 q("naturalizado","¿Eres mexicano por naturalización?",["Sí","No"]),
 q("antiguo","¿El pasaporte fue expedido antes de 1995 en México o antes de 2007 en el extranjero?",["Sí","No","No estoy seguro"]),
 q("emergencia","¿El pasaporte anterior fue expedido como caso de emergencia o protección consular?",["Sí","No","No estoy seguro"]),
 q("restriccion","¿Tiene alguna restricción, observación o indicación de NO CANJEABLE?",["Sí","No","No estoy seguro"]),
 q("un_ano","¿El pasaporte anterior tiene vigencia de un año?",["Sí","No","No estoy seguro"]),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para una renovación normal debes acudir personalmente con cita y presentar el pasaporte que deseas renovar. Algunos pasaportes antiguos, de emergencia, con restricciones o de un año pueden requerir un procedimiento diferente.",
"pago":"Confirma la tarifa consular vigente y la forma de pago antes de acudir.",
"confirma":"Si el pasaporte debe tramitarse como primera vez, tendrás que presentar nuevamente la documentación de nacionalidad e identidad correspondiente.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"pasaporte_perdido","servicio":"cita","titulo":"Perdí, me robaron, destruyeron o mutilaron mi pasaporte",
"grupos":[["pasaporte"],["perdi","perdido","perdí","robo","robado","robaron","extraviado","destruido","mutilado","mutilacion","mutilación"]],
"preguntas":[
 q("menor","¿El pasaporte era de una persona menor de 18 años?",["Sí","No"]),
 q("reporte","¿Tienes un reporte o acta de la autoridad competente sobre la pérdida, robo, destrucción o mutilación?",SI),
 q("nacionalidad","¿Tienes un documento ORIGINAL que compruebe la nacionalidad mexicana?",SI),
 q("identidad","¿Tienes una identificación ORIGINAL con fotografía?",SI),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para reposición por robo, pérdida, destrucción o mutilación debes acreditar el hecho mediante el reporte correspondiente y presentar los documentos como si fuera una primera expedición.",
"pago":"Confirma la tarifa y la forma de pago vigente.",
"confirma":"Por protección consular, el reporte puede tener modalidades especiales. Confirma con el Consulado si tu situación requiere una indicación particular.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"pasaporte_menor","servicio":"cita","titulo":"Sacar o renovar el pasaporte de un menor",
"grupos":[["pasaporte"],["menor","hijo","hija","niño","niña","nino","nina","bebe","bebé"]],
"preguntas":[
 q("operacion","¿Es la primera vez o es una renovación?",["Primera vez","Renovación"]),
 q("edad","¿El menor tiene menos de 3 años?",["Sí","No"]),
 q("menor_nacionalidad","¿Tienes el ORIGINAL del documento que acredita la nacionalidad mexicana del menor?",SI),
 q("menor_identidad","¿Tienes el ORIGINAL de una identificación aceptada del menor?",SI),
 q("ambos_padres","¿Pueden presentarse ambos padres o quienes ejercen la patria potestad?",["Sí","No","No estoy seguro"]),
 q("op7","Si falta un padre, ¿ya está gestionada la autorización OP-7?",["Sí","No","No aplica","No estoy seguro"]),
 q("divorcio","¿Los padres están separados o divorciados?",["Sí","No","No estoy seguro"]),
 q("sentencia","¿Existe una sentencia que quite la patria potestad o permita a uno de los padres tramitar el pasaporte sin el otro?",["Sí","No","No estoy seguro","No aplica"]),
 q("padres_id","¿Tienes identificación oficial vigente con fotografía y firma de los padres que correspondan?",SI),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para un menor deben acreditarse nacionalidad e identidad y debe existir el consentimiento correspondiente de quienes ejercen la patria potestad o tutela. El menor debe acudir según las instrucciones del Consulado.",
"pago":"Confirma la tarifa y forma de pago vigente.",
"confirma":"La OP-7 es la autorización de los padres. Si los padres están separados o divorciados, el divorcio por sí solo no elimina la patria potestad. Sin una resolución judicial que permita hacerlo sin el otro progenitor, ambos deben autorizar.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"pasaporte_extemporanea","servicio":"cita","titulo":"Mi acta de nacimiento puede ser extemporánea",
"grupos":[["acta","nacimiento"],["extemporanea","extemporánea","registro tarde","registraron tarde"]],
"preguntas":[
 q("ano_nacimiento","¿En qué año naciste?",None),
 q("ano_registro","¿En qué año fue registrado tu nacimiento?",None),
 q("prueba","¿Ya tienes alguna prueba complementaria de tu nacimiento?",["Sí","No","No estoy seguro"]),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Si el registro de nacimiento supera el período de extemporaneidad aplicable, el Consulado puede solicitar una prueba complementaria antes de expedir el pasaporte.",
"pago":"Confirma la tarifa vigente.",
"confirma":"La Oficina Consular puede verificar electrónicamente o por escrito la validez del acta con el Registro Civil, lo que puede retrasar la expedición.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"pasaporte_conyuge","servicio":"cita","titulo":"Quiero usar el apellido de mi cónyuge en el pasaporte",
"grupos":[["pasaporte"],["esposo","esposa","conyuge","cónyuge","apellido","casado","casada"]],
"preguntas":[
 q("acta_matrimonio","¿Tienes el acta de matrimonio ORIGINAL o la documentación certificada que corresponda?",SI),
 q("identificacion_apellido","¿Tu identificación actual muestra solamente el apellido de tu cónyuge?",["Sí","No"]),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"El nombre del solicitante conserva sus nombres y apellidos de acuerdo con las reglas del pasaporte; el apellido del cónyuge se incorpora en el apartado especial correspondiente.",
"pago":"Confirma la tarifa vigente.",
"confirma":"Si tu identificación muestra el apellido del cónyuge, debes presentar el documento de matrimonio que permita vincular ese apellido con tu identidad.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"pasaporte_naturalizado","servicio":"cita","titulo":"Pasaporte para una persona mexicana por naturalización",
"grupos":[["pasaporte"],["naturalizado","naturalización","naturalizacion","carta de naturalizacion","carta de naturalización"]],
"preguntas":[
 q("carta","¿Tienes la carta de naturalización ORIGINAL o copia certificada cuando corresponda?",SI),
 q("identidad","¿Tienes una identificación ORIGINAL con fotografía?",SI),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"La persona mexicana por naturalización debe acreditar su nacionalidad mediante la documentación de naturalización correspondiente y acreditar su identidad.",
"pago":"Confirma la tarifa consular vigente.",
"confirma":"Para renovación de una persona naturalizada, la información del Consulado de Miami indica que debe presentarse la carta de naturalización original o copia certificada expedida por la SRE.",
"fuente":FUENTES["pasaporte"]
}
},
{
"id":"matricula_primera_adulto","servicio":"cita","titulo":"Sacar mi matrícula consular por primera vez",
"grupos":[["matricula","matrícula"],["primera","sacar","obtener","solicitar"]],
"preguntas":[
 q("menor","¿La matrícula es para una persona menor de 18 años?",["Sí","No"]),
 q("nacionalidad","¿Tienes ORIGINAL de un documento que compruebe tu nacionalidad mexicana?",SI),
 q("identidad","¿Tienes ORIGINAL de una identificación con fotografía?",SI),
 q("domicilio","¿Tienes ORIGINAL de un comprobante de domicilio a tu nombre con dirección completa?",SI),
 q("sin_domicilio","Si no está a tu nombre, ¿vives con un familiar que pueda acreditar el parentesco?",["Sí","No","No estoy seguro","No aplica"]),
 q("conyuge","¿Tu identificación tiene el apellido de tu cónyuge o quieres usarlo en la matrícula?",["Sí","No"]),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para la primera matrícula debes comparecer personalmente con cita, acreditar nacionalidad e identidad con documentos originales y presentar comprobante de domicilio en tu nombre con dirección completa.",
"pago":"La tarifa indicada para la matrícula debe confirmarse antes de acudir. Revisa la tarifa vigente del Consulado.",
"confirma":"Si no tienes comprobante de domicilio a tu nombre, existen alternativas específicas. Si tu identificación usa apellido de cónyuge, puede requerirse el acta de matrimonio original.",
"fuente":FUENTES["matricula"]
}
},
{
"id":"matricula_renovacion","servicio":"cita","titulo":"Renovar mi matrícula consular",
"grupos":[["matricula","matrícula"],["renovar","renovacion","renovación","vigente","vencida"]],
"preguntas":[
 q("matricula_anterior","¿Tienes la matrícula consular que vas a renovar?",SI),
 q("domicilio_cambio","¿Cambiaste de domicilio desde que obtuviste la matrícula anterior?",["Sí","No","No estoy seguro"]),
 q("domicilio","¿Tienes ORIGINAL de comprobante de tu domicilio actual?",["Sí","No","No estoy seguro","No aplica"]),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para renovar debes comparecer personalmente con cita y presentar la matrícula que vas a renovar. El comprobante de domicilio se requiere cuando cambió tu residencia y el domicilio anterior ya no es actual.",
"pago":"Confirma la tarifa vigente.",
"confirma":"La matrícula consular tiene una vigencia de cinco años.",
"fuente":FUENTES["matricula"]
}
},
{
"id":"matricula_perdida","servicio":"cita","titulo":"Perdí o me robaron mi matrícula consular",
"grupos":[["matricula","matrícula"],["perdi","perdí","perdido","robaron","robo","robada","extraviada"]],
"preguntas":[
 q("explicacion","¿Estás preparado para llenar en el Consulado el formato donde explicas la pérdida o robo?",["Sí","No","No estoy seguro"]),
 q("nacionalidad","¿Tienes ORIGINAL de tu documento de nacionalidad mexicana?",SI),
 q("identidad","¿Tienes ORIGINAL de identificación con fotografía?",SI),
 q("domicilio","¿Tienes ORIGINAL de comprobante de domicilio?",SI),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para una matrícula perdida o robada, el Consulado requiere un formulario donde se expliquen las circunstancias. Además, debes cumplir los requisitos que correspondan para expedir una nueva matrícula.",
"pago":"Confirma la tarifa vigente.",
"confirma":"El sistema no permite emitir una nueva matrícula sin el formulario correspondiente.",
"fuente":FUENTES["matricula"]
}
},
{
"id":"matricula_menor","servicio":"cita","titulo":"Sacar la matrícula consular de un menor",
"grupos":[["matricula","matrícula"],["menor","hijo","hija","niño","niña","nino","nina"]],
"preguntas":[
 q("nacionalidad","¿Tienes ORIGINAL del documento que acredita la nacionalidad mexicana del menor?",SI),
 q("identidad","¿Tienes ORIGINAL de una identificación aceptada del menor?",SI),
 q("menor7","¿El menor tiene menos de 7 años?",["Sí","No"]),
 q("padres","¿Pueden presentarse ambos padres o tutores con el menor?",["Sí","No","No estoy seguro"]),
 q("op7","Si falta uno de los padres, ¿ya existe la autorización correspondiente?",["Sí","No","No aplica","No estoy seguro"]),
 q("divorcio","¿Los padres están separados o divorciados?",["Sí","No","No estoy seguro"]),
 q("sentencia","¿Existe una sentencia que permita a uno de los padres realizar el trámite sin el consentimiento del otro?",["Sí","No","No estoy seguro","No aplica"]),
 q("padres_id","¿Tienes identificación vigente con fotografía y firma de ambos padres?",SI),
 q("cita","¿Ya tienes tu cita?",["Sí","No"])
],
"resultado":{
"prepara":"Para la matrícula de un menor deben presentarse el menor y quienes ejercen la patria potestad o tutela, acreditar nacionalidad e identidad y otorgar las autorizaciones correspondientes.",
"pago":"Confirma la tarifa vigente.",
"confirma":"Si un padre no puede acudir, existen procedimientos de autorización. La separación o el divorcio por sí solos no eliminan la patria potestad. Sin una resolución judicial aplicable, ambos padres deben autorizar.",
"fuente":FUENTES["matricula"]
},
},
{
"id":"registro_nacimiento_extranjero","servicio":"documento","titulo":"Registrar a mi hijo como mexicano",
"grupos":[["hijo","hija","nino","niño","nina","niña","bebe","bebé"],["nacimiento","nacio","nació"],["mexicano","mexicana"]],
"preguntas":[
 q("padre_mexicano","¿El padre o la madre es mexicano?",SI),
 q("acta_extranjera","¿Tienes el acta de nacimiento extranjera ORIGINAL del hijo?",SI),
 q("acta_padre","¿Tienes el acta de nacimiento mexicana del padre o madre mexicano?",SI),
 q("identidad","¿Tienes las identificaciones correspondientes de los padres?",SI)
],
"resultado":{
"prepara":"El registro debe acreditar el nacimiento y la nacionalidad mexicana que corresponda.",
"pago":"El registro de nacimiento en el extranjero es gratuito cuando corresponde a este trámite.",
"confirma":"El Consulado puede solicitar documentación adicional según la situación familiar y los documentos presentados.",
"fuente":FUENTES["nacimiento"]
}
},
{
"id":"acta_nacimiento_mexicana","servicio":"documento","titulo":"Necesito mi acta de nacimiento mexicana",
"grupos":[["acta"],["nacimiento","nacido","nacida"],["mexicana","mexicano","mexico","copia","certificada"]],
"preguntas":[
 q("registrada","¿Tu nacimiento ya está registrado en México?",["Sí","No","No estoy seguro"])
],
"resultado":{
"prepara":"Si tu nacimiento ya está registrado en México, puedes necesitar una copia certificada del acta. Si nunca fue registrado, el procedimiento es diferente.",
"pago":"Confirma el costo y la forma de obtener la copia correspondiente.",
"confirma":"No confundas obtener una copia certificada con registrar un nacimiento que nunca fue registrado.",
"fuente":FUENTES["documentacion"]
}
},
{
"id":"poder_notarial","servicio":"documento","titulo":"Dar un poder a otra persona",
"grupos":[["poder","poderes"],["notarial","notario","notaria"],["autorizar","representar","representacion"]],
"preguntas":[
 q("motivo","¿Para qué necesitas el poder?",["Casa o propiedad","Dinero o banco","Trámite legal","Otro"]),
 q("mexicano","¿La persona que dará el poder es mexicana?",SI),
 q("matrimonio","¿Está casada?",SI),
 q("identidad","¿Tiene identificación oficial vigente?",SI)
],
"resultado":{
"prepara":"Los requisitos de un poder dependen de lo que deseas autorizar y de la situación de quien otorga el poder.",
"pago":"Confirma la tarifa y forma de pago con el Consulado.",
"confirma":"No firmes un poder preparado por terceros sin confirmar primero qué tipo de instrumento corresponde.",
"fuente":FUENTES["poder"]
}
}
]

OPCIONES=[
{"id":"pasaporte_primera_vez","texto":"Sacar mi pasaporte","servicio":"cita"},
{"id":"pasaporte_renovacion","texto":"Renovar mi pasaporte","servicio":"cita"},
{"id":"pasaporte_perdido","texto":"Perdí o me robaron mi pasaporte","servicio":"cita"},
{"id":"pasaporte_menor","texto":"Pasaporte para un menor","servicio":"cita"},
{"id":"pasaporte_extemporanea","texto":"Mi acta puede ser extemporánea","servicio":"cita"},
{"id":"pasaporte_conyuge","texto":"Apellido de mi cónyuge en el pasaporte","servicio":"cita"},
{"id":"matricula_primera_adulto","texto":"Sacar mi matrícula consular","servicio":"cita"},
{"id":"matricula_renovacion","texto":"Renovar mi matrícula consular","servicio":"cita"},
{"id":"matricula_perdida","texto":"Perdí o me robaron mi matrícula","servicio":"cita"},
{"id":"matricula_menor","texto":"Matrícula consular para un menor","servicio":"cita"},
{"id":"acta_nacimiento_mexicana","texto":"Necesito mi acta de nacimiento","servicio":"documento"},
{"id":"registro_nacimiento_extranjero","texto":"Registrar a mi hijo como mexicano","servicio":"documento"},
{"id":"poder_notarial","texto":"Dar un poder a otra persona","servicio":"documento"},
{"id":"no_se","texto":"No sé qué necesito","servicio":"documento"}
]

def catalogo(servicio=None):
 return deepcopy([x for x in OPCIONES if not servicio or x["servicio"]==servicio])

def obtener_caso(cid):
 for c in CASOS:
  if c["id"]==cid:return deepcopy(c)
 return None

def puntuar(caso,texto):
 t=normalizar(texto);w=palabras(t);s=0
 for grupo in caso.get("grupos",[]):
  for x in grupo:
   x=normalizar(x)
   if x and (x in t or (" " not in x and x in w)):
    s+=2;break
 return s

def buscar_casos(texto,servicio):
 a=[]
 for c in CASOS:
  if c["servicio"]!=servicio:continue
  s=puntuar(c,texto)
  if s>=2:a.append((s,c))
 a.sort(key=lambda x:x[0],reverse=True)
 return [x[1] for x in a]

def identificar(servicio,texto):
 a=buscar_casos(texto,servicio)
 if not a:return None
 if len(a)==1:return a[0]
 return a[0] if puntuar(a[0],texto)>=puntuar(a[1],texto)+2 else a

def pregunta_actual(caso,res):
 for x in caso.get("preguntas",[]):
  if x["id"] not in res:return x
 return None

def respuesta_pregunta(caso,qx):
 return {
  "estado":"pregunta","caso":caso["id"],"titulo":caso["titulo"],
  "pregunta":qx["texto"],"pregunta_id":qx["id"],
  "opciones":qx.get("opciones",[])
 }

def edad_ano(v):
 try:return int(re.search(r"\d{4}",str(v)).group())
 except:return None

def extemporanea(res):
 nacimiento=edad_ano(res.get("ano_nacimiento"))
 registro=edad_ano(res.get("ano_registro"))
 if not nacimiento or not registro:return None
 edad=registro-nacimiento
 if nacimiento<1931:limite=50
 elif nacimiento<=1940:limite=30
 elif nacimiento<=1950:limite=10
 elif nacimiento<=1976:limite=5
 else:limite=1
 return edad>limite

def documentos(caso,res):
 d=[]
 for nombre,campo in caso.get("documentos",[]):
  v=res.get(campo)
  if afirmativo(v):estado="tiene"
  elif negativo(v):estado="falta"
  else:estado="revisar"
  d.append((nombre,campo,estado))
 return d

def requisitos_dinamicos(caso,res):
 cid=caso["id"]
 out=[]

 if cid=="pasaporte_primera_vez":
  if afirmativo(res.get("sin_identidad")):
   out.append("Constancia de Identidad: revisa el procedimiento oficial antes de acudir.")
  if afirmativo(res.get("acta_extemporanea")) or extemporanea(res) is True:
   out.append("PRUEBA COMPLEMENTARIA por posible acta extemporánea.")
  if afirmativo(res.get("conyuge")):
   out.append("Acta de matrimonio ORIGINAL cuando corresponda.")
  if afirmativo(res.get("menor")):
   out.append("Requisitos adicionales de menor y autorización de padres/tutores.")

 if cid=="pasaporte_renovacion":
  if afirmativo(res.get("antiguo")) or afirmativo(res.get("emergencia")) or afirmativo(res.get("restriccion")) or afirmativo(res.get("un_ano")):
   out.append("ATENCIÓN: este pasaporte puede no ser canjeable mediante renovación normal. Confirma si debes presentar requisitos como primera vez.")
  if afirmativo(res.get("naturalizado")):
   out.append("Carta de naturalización ORIGINAL o copia certificada expedida por la SRE, según corresponda.")

 if cid=="pasaporte_perdido":
  out.append("Reporte o acta de la autoridad competente sobre la pérdida, robo, destrucción o mutilación.")
  out.append("Después del reporte, prepara los requisitos de una primera expedición.")

 if cid=="pasaporte_menor":
  out += [
   "Documento ORIGINAL de nacionalidad del menor.",
   "Documento ORIGINAL de identidad del menor.",
   "OP-7 y consentimiento de quienes ejercen la patria potestad o tutela.",
   "Identificación vigente de los padres o tutores que deban autorizar."
  ]
  if negativo(res.get("ambos_padres")):
   out.append("Si un padre no está disponible, revisa el procedimiento OP-7 antes de acudir.")
  if afirmativo(res.get("divorcio")) and not afirmativo(res.get("sentencia")):
   out.append("El divorcio por sí solo no elimina la patria potestad: se requiere autorización de ambos salvo resolución judicial aplicable.")
  if afirmativo(res.get("sentencia")):
   out.append("Lleva la resolución judicial correspondiente.")
  if afirmativo(res.get("edad")):
   out.append("Para menores de 3 años existen opciones específicas de vigencia.")

 if cid=="pasaporte_extemporanea":
  ex=extemporanea(res)
  if ex is True:
   out.append("TU ACTA PUEDE SER EXTEMPORÁNEA: necesitas revisar una PRUEBA COMPLEMENTARIA antes de acudir.")
  elif ex is False:
   out.append("Con los años indicados, el registro queda dentro del período señalado por la fuente.")
  else:
   out.append("No fue posible determinar la extemporaneidad. Confirma las fechas exactas.")

 if cid=="pasaporte_conyuge" and (afirmativo(res.get("acta_matrimonio")) or afirmativo(res.get("identificacion_apellido"))):
  out.append("Acta de matrimonio para acreditar el apellido del cónyuge.")

 if cid=="matricula_primera_adulto":
  out += [
   "Nacionalidad mexicana: ORIGINAL.",
   "Identidad con fotografía: ORIGINAL.",
   "Comprobante de domicilio: ORIGINAL y con dirección completa."
  ]
  if afirmativo(res.get("sin_domicilio")):
   out.append("Si vives con un familiar, revisa la alternativa de acreditar el parentesco.")
  if afirmativo(res.get("conyuge")):
   out.append("Acta de matrimonio ORIGINAL si corresponde al apellido del cónyuge.")

 if cid=="matricula_renovacion" and afirmativo(res.get("domicilio_cambio")):
  out.append("Comprobante ORIGINAL del domicilio actual.")

 if cid=="matricula_perdida":
  out.append("Formulario del Consulado explicando la pérdida o robo.")

 if cid=="matricula_menor":
  out += [
   "Nacionalidad del menor: ORIGINAL.",
   "Identidad del menor: ORIGINAL.",
   "Autorización de ambos padres/tutores según corresponda.",
   "Identificaciones vigentes de los padres."
  ]
  if negativo(res.get("padres")):
   out.append("Si un padre no puede acudir, debe gestionarse la autorización correspondiente.")
  if afirmativo(res.get("divorcio")) and not afirmativo(res.get("sentencia")):
   out.append("La separación o divorcio no elimina por sí solo la patria potestad.")
  if afirmativo(res.get("sentencia")):
   out.append("Lleva la resolución judicial correspondiente.")
  if afirmativo(res.get("menor7")):
   out.append("Para menores de 7 años existe una alternativa de constancia médica con fotografía y sello cuando no se cuenta con otra identificación aceptada.")

 return out

def estado_preparacion(caso,res):
 cid=caso["id"]
 crit=[]

 for x in requisitos_dinamicos(caso,res):
  if x.startswith(("ATENCIÓN","TU ACTA","NO VAYAS","PRUEBA COMPLEMENTARIA")):
   crit.append(x)

 faltan=[]
 for k,v in res.items():
  if k.startswith("_") or k in {"ano_nacimiento","ano_registro"}:continue
  if v in ("No","No estoy seguro","No aplica") and k in {
   "nacionalidad","identidad","menor_nacionalidad","menor_identidad",
   "domicilio","cita","pasaporte_anterior","reporte","carta",
   "acta_matrimonio","menor_identidad","padres_id","op7"
  }:
   faltan.append(k)

 if crit:return "rojo"
 if faltan:return "amarillo"
 return "verde"

def resultado(caso,respuestas=None):
 res=dict(respuestas or {})
 cid=caso["id"]
 ds=documentos(caso,res)
 tiene=[x[0] for x in ds if x[2]=="tiene"]
 falta=[x[0] for x in ds if x[2]=="falta"]
 revisar=[x[0] for x in ds if x[2]=="revisar"]
 dinamicos=requisitos_dinamicos(caso,res)
 estado=estado_preparacion(caso,res)

 if cid.startswith("pasaporte"):
  entrega="En las oficinas consulares de México en Estados Unidos, la información proporcionada indica entrega el mismo día una vez cumplidos los requisitos; puede tomar alrededor de dos horas si el sistema no presenta fallas."
  vigencia="La vigencia depende de la edad: menores de 3 años, 1 o 3 años; de 3 a menores de 18, 3 o 6 años; mayores de 18, 3, 6 o 10 años."
 else:
  entrega="Según la información del Consulado de México en Miami, la matrícula puede entregarse el mismo día y el proceso puede tomar alrededor de dos horas si no hay fallas del sistema."
  vigencia="La matrícula consular tiene una vigencia de cinco años."

 if estado=="verde":
  estado_txt="PARECES LISTO: no aparece un requisito crítico pendiente en tus respuestas."
 elif estado=="amarillo":
  estado_txt="TE FALTA ALGO: revisa los documentos o respuestas marcados antes de acudir."
 else:
  estado_txt="ATENCIÓN: hay una situación especial que debes resolver o confirmar antes de acudir."

 if cid=="pasaporte_extemporanea" and extemporanea(res) is True:
  estado_txt="NO VAYAS TODAVÍA: tu acta puede ser extemporánea y puede requerir una prueba complementaria."

 return {
  "estado":"resuelto","caso":cid,"titulo":caso["titulo"],
  "prepara":caso["resultado"]["prepara"],
  "confirma":caso["resultado"]["confirma"],
  "pago":caso["resultado"]["pago"],
  "fuente":caso["resultado"]["fuente"],
  "respuestas":res,
  "nivel":estado,
  "estado_texto":estado_txt,
  "checklist":{
   "tiene":tiene,
   "falta":falta,
   "revisar":revisar,
   "documentos":[x[0] for x in ds]
  },
  "ruta":{
   "tramite":caso["titulo"],
   "llevar_original":"Presenta los documentos ORIGINALES que correspondan a tu caso.",
   "copias":"No se debe asumir que las copias sustituyen los originales. Lleva copias únicamente cuando la fuente oficial de tu trámite las indique.",
   "cita":"Confirma y conserva tu cita. Para información de citas: "+FUENTES["citas"],
   "pago":caso["resultado"]["pago"]
  },
  "especiales":dinamicos,
  "entrega":entrega,
  "vigencia":vigencia,
  "revision":"Revisa cuidadosamente todos los datos que el personal consular capture antes de firmar o antes de que el documento sea impreso. Si detectas un error antes de imprimir, solicita que lo corrijan.",
  "aviso":"Esta aplicación es una guía independiente. No es el Gobierno de México ni representa a ningún Consulado. La autoridad consular puede verificar documentos y solicitar documentación adicional."
 }

def iniciar(servicio):
 if servicio not in ("cita","documento"):
  return {"estado":"error","mensaje":"Servicio no disponible."}
 return {"estado":"necesita_descripcion","pregunta":"¿Qué necesitas?", "opciones":catalogo(servicio)}

def seleccionar(caso_id):
 caso=obtener_caso(caso_id)
 if not caso:return {"estado":"no_identificado","mensaje":"No encontramos esa opción."}
 qs=caso.get("preguntas",[])
 return respuesta_pregunta(caso,qs[0]) if qs else resultado(caso,{})

def continuar(caso_id,respuestas=None):
 res=dict(respuestas or {})
 caso=obtener_caso(caso_id)
 if not caso:return {"estado":"no_identificado","mensaje":"No encontramos ese trámite."}

 qx=pregunta_actual(caso,res)
 if qx:return respuesta_pregunta(caso,qx)
 return resultado(caso,res)

def interpretar(servicio,texto,respuestas=None):
 res=dict(respuestas or {})
 texto=(texto or "").strip()

 cid=res.get("_caso")
 if cid:return continuar(cid,res)

 if not texto:return iniciar(servicio)

 directo=obtener_caso(texto)
 if directo and directo["servicio"]==servicio:
  res["_caso"]=directo["id"]
  return continuar(directo["id"],res)

 encontrados=identificar(servicio,texto)

 if not encontrados:
  return {
   "estado":"necesita_descripcion",
   "pregunta":"No quiero adivinar. Dime con tus propias palabras qué necesitas.",
   "opciones":catalogo(servicio)
  }

 if isinstance(encontrados,list):
  return {
   "estado":"seleccionar",
   "pregunta":"¿Cuál de estas opciones se parece más a lo que necesitas?",
   "opciones":[{"id":x["id"],"texto":x["titulo"]} for x in encontrados]
  }

 res["_caso"]=encontrados["id"]
 return continuar(encontrados["id"],res)
