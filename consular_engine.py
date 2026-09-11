import re
from copy import deepcopy

FUENTES={
"pasaporte":"https://consulmex.sre.gob.mx/miami/index.php/pasaporte",
"citas":"https://citas.sre.gob.mx",
"tarifas":"https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",
"matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
"nacimiento":"https://www.gob.mx/tramites/ficha/registro-de-nacimiento-en-el-extranjero/SRE92",
"poder":"https://consulmex.sre.gob.mx/miami/index.php/poderes-notariales",
"documentacion":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/dconsular"
}

def normalizar(x):
 x=str(x or "").lower().strip()
 x=x.translate(str.maketrans("áàäâéèëêíìïîóòöôúùüûñ","aaaaeeeeiiiioooouuuun"))
 return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9@._+\-/\s]"," ",x)).strip()

def afirmativo(x):
 n=normalizar(x)
 return n in {"si","s","yes","1","true","correcto","correcta"} or n.startswith("si ")

def negativo(x):
 n=normalizar(x)
 return n in {"no","n","0","false"} or n.startswith("no ")

def incierto(x):
 n=normalizar(x)
 return any(x in n for x in("no estoy seguro","no se","no lo se","no recuerdo","tal vez","quizas","quizá"))

def q(i,t,op=None):
 d={"id":i,"texto":t}
 if op:d["opciones"]=op
 return d

SI=["Sí","No","No estoy seguro"]

CASOS=[
{"id":"pasaporte_primera_vez","servicio":"cita","titulo":"Sacar mi pasaporte por primera vez","grupos":[["pasaporte"],["primera vez","primera","sacar","obtener","solicitar","nuevo"]],"preguntas":[
q("menor","¿El pasaporte es para una persona menor de 18 años?",["Sí","No"]),
q("nacionalidad","¿Tienes un documento ORIGINAL que compruebe la nacionalidad mexicana?",SI),
q("identidad","¿Tienes una identificación ORIGINAL con fotografía cuyos datos coincidan?",SI),
q("acta_extemporanea","¿Tu acta de nacimiento puede ser extemporánea?",["Sí","No","No estoy seguro"]),
q("naturalizado","¿Eres mexicano por naturalización?",["Sí","No"]),
q("conyuge","¿Quieres que aparezca el apellido de tu cónyuge en el pasaporte?",["Sí","No"]),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Documento ORIGINAL que compruebe nacionalidad mexicana","nacionalidad"),
("Identificación ORIGINAL con fotografía","identidad")],"resultado":{
"prepara":"Para la primera expedición debes acudir personalmente con cita, acreditar nacionalidad mexicana e identidad mediante documentos originales y cumplir con la tarifa vigente.",
"confirma":"Revisa cuidadosamente todos los datos antes de firmar.",
"pago":"Confirma el monto y la forma de pago de la tarifa consular vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_renovacion","servicio":"cita","titulo":"Renovar mi pasaporte","grupos":[["pasaporte"],["renovar","renovacion","renovarlo","vencido","vencer","expirado","caducado"]],"preguntas":[
q("menor","¿El pasaporte es para una persona menor de 18 años?",["Sí","No"]),
q("pasaporte_anterior","¿Tienes el pasaporte que vas a renovar?",SI),
q("naturalizado","¿Eres mexicano por naturalización?",["Sí","No"]),
q("antiguo","¿Fue expedido antes de 1995 en México o antes de 2007 en el extranjero?",["Sí","No","No estoy seguro"]),
q("emergencia","¿Fue expedido como pasaporte de emergencia o protección?",["Sí","No","No estoy seguro"]),
q("restriccion","¿Tiene alguna restricción o indicación de NO CANJEABLE?",["Sí","No","No estoy seguro"]),
q("un_ano","¿Tiene vigencia de un año?",["Sí","No","No estoy seguro"]),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Pasaporte que vas a renovar","pasaporte_anterior")],"resultado":{
"prepara":"Para una renovación normal debes acudir personalmente con cita y presentar el pasaporte que vas a renovar.",
"confirma":"Los pasaportes antiguos, de emergencia, con restricciones o de un año pueden requerir un procedimiento diferente.",
"pago":"Confirma la tarifa y forma de pago vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_perdido","servicio":"cita","titulo":"Perdí, me robaron, destruyeron o mutilaron mi pasaporte","grupos":[["pasaporte"],["perdi","perdido","perdida","robo","robado","robaron","extraviado","destruido","mutilado"]],"preguntas":[
q("menor","¿El pasaporte era de una persona menor de 18 años?",["Sí","No"]),
q("reporte","¿Tienes reporte o acta de la autoridad competente?",SI),
q("nacionalidad","¿Tienes ORIGINAL del documento que comprueba tu nacionalidad mexicana?",SI),
q("identidad","¿Tienes identificación ORIGINAL con fotografía?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Reporte o acta de la autoridad competente","reporte"),
("Documento ORIGINAL de nacionalidad mexicana","nacionalidad"),
("Identificación ORIGINAL con fotografía","identidad")],"resultado":{
"prepara":"Debes acreditar la pérdida, robo, destrucción o mutilación mediante el reporte correspondiente y preparar los requisitos de una primera expedición.",
"confirma":"Confirma con el Consulado cualquier indicación especial relacionada con el reporte.",
"pago":"Confirma la tarifa y forma de pago vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_menor","servicio":"cita","titulo":"Pasaporte para un menor","grupos":[["pasaporte"],["menor","hijo","hija","niño","niña","nino","nina","bebe"]],"preguntas":[
q("operacion","¿Es la primera vez o es una renovación?",["Primera vez","Renovación"]),
q("menor_nacionalidad","¿Tienes el ORIGINAL del documento que acredita la nacionalidad mexicana del menor?",SI),
q("menor_identidad","¿Tienes el ORIGINAL de una identificación aceptada del menor?",SI),
q("padres","¿Pueden presentarse ambos padres o quienes ejercen la patria potestad?",["Sí","No","No estoy seguro"]),
q("op7","Si falta un padre, ¿ya está gestionada la autorización OP-7?",["Sí","No","No aplica","No estoy seguro"]),
q("sentencia","¿Existe una resolución judicial aplicable?",["Sí","No","No estoy seguro","No aplica"]),
q("padres_id","¿Tienes las identificaciones correspondientes de los padres?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Documento ORIGINAL de nacionalidad del menor","menor_nacionalidad"),
("Identificación ORIGINAL del menor","menor_identidad"),
("Identificaciones correspondientes de los padres","padres_id")],"resultado":{
"prepara":"El menor debe acreditar nacionalidad e identidad y debe existir el consentimiento correspondiente de quienes ejercen la patria potestad o tutela.",
"confirma":"La separación o el divorcio por sí solos no eliminan la patria potestad. Cuando corresponda, revisa OP-7 o la resolución judicial.",
"pago":"Confirma la tarifa y forma de pago vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_extemporanea","servicio":"cita","titulo":"Mi acta puede ser extemporánea","grupos":[["acta","nacimiento"],["extemporanea","extemporáneo","registro tarde","registraron tarde"]],"preguntas":[
q("ano_nacimiento","¿En qué año naciste?"),
q("ano_registro","¿En qué año fue registrado tu nacimiento?"),
q("prueba","¿Ya tienes alguna prueba complementaria de tu nacimiento?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Prueba complementaria de nacimiento","prueba")],"resultado":{
"prepara":"Si el registro supera el período de extemporaneidad aplicable, el Consulado puede solicitar una prueba complementaria.",
"confirma":"El Consulado puede verificar la información con el Registro Civil y esto puede retrasar la expedición.",
"pago":"Confirma la tarifa vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_conyuge","servicio":"cita","titulo":"Apellido de mi cónyuge en el pasaporte","grupos":[["pasaporte"],["esposo","esposa","conyuge","apellido","casado","casada"]],"preguntas":[
q("acta_matrimonio","¿Tienes el acta de matrimonio ORIGINAL o documentación certificada?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Acta de matrimonio","acta_matrimonio")],"resultado":{
"prepara":"Debes acreditar el vínculo matrimonial para que el apellido del cónyuge pueda aparecer en el apartado correspondiente.",
"confirma":"El apellido del cónyuge se maneja en el apartado especial correspondiente del pasaporte.",
"pago":"Confirma la tarifa vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_naturalizado","servicio":"cita","titulo":"Pasaporte de una persona mexicana por naturalización","grupos":[["pasaporte"],["naturalizado","naturalizada","naturalizacion","naturalización","carta de naturalizacion","carta de naturalización"]],"preguntas":[
q("carta","¿Tienes la carta de naturalización ORIGINAL o copia certificada cuando corresponda?",SI),
q("identidad","¿Tienes una identificación ORIGINAL con fotografía?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Carta de naturalización ORIGINAL o copia certificada cuando corresponda","carta"),
("Identificación ORIGINAL con fotografía","identidad")],"resultado":{
"prepara":"Debes acreditar la nacionalidad por naturalización mediante la documentación correspondiente y acreditar tu identidad.",
"confirma":"Para renovación, revisa las indicaciones específicas para personas naturalizadas.",
"pago":"Confirma la tarifa y forma de pago vigente.","fuente":FUENTES["pasaporte"]}},

{"id":"pasaporte_validez","servicio":"documento","titulo":"Quiero saber qué vigencia puede tener mi pasaporte","grupos":[["pasaporte"],["vigencia","vigente","cuanto dura","cuánto dura","duracion","duración"]],"preguntas":[
q("edad","¿Qué edad tiene la persona que tendrá el pasaporte?"),
q("cita","¿Necesitas además preparar una cita para tramitarlo?",["Sí","No"])],"documentos":[],"resultado":{
"prepara":"La vigencia depende de la edad de la persona. Menores de 3 años pueden obtener pasaporte de 1 o 3 años; de 3 años y menores de 18, de 3 o 6 años; los adultos pueden obtenerlo por 3, 6 o 10 años.",
"confirma":"La opción disponible debe confirmarse conforme a la situación concreta y a la información oficial vigente.",
"pago":"Confirma la tarifa vigente según la vigencia solicitada.","fuente":FUENTES["pasaporte"]}},

{"id":"matricula_primera_adulto","servicio":"cita","titulo":"Sacar mi matrícula consular","grupos":[["matricula","matrícula"],["primera","sacar","obtener","solicitar"]],"preguntas":[
q("menor","¿La matrícula es para una persona menor de 18 años?",["Sí","No"]),
q("nacionalidad","¿Tienes ORIGINAL de un documento que compruebe tu nacionalidad mexicana?",SI),
q("identidad","¿Tienes ORIGINAL de una identificación con fotografía?",SI),
q("domicilio","¿Tienes ORIGINAL de un comprobante de domicilio a tu nombre con dirección completa?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Documento ORIGINAL de nacionalidad mexicana","nacionalidad"),
("Identificación ORIGINAL con fotografía","identidad"),
("Comprobante ORIGINAL de domicilio con dirección completa","domicilio")],"resultado":{
"prepara":"Debes comparecer personalmente con cita, acreditar nacionalidad e identidad y presentar comprobante de domicilio con dirección completa.",
"confirma":"Si el comprobante de domicilio no está a tu nombre, revisa la alternativa correspondiente a tu situación.",
"pago":"Confirma la tarifa vigente.","fuente":FUENTES["matricula"]}},

{"id":"matricula_renovacion","servicio":"cita","titulo":"Renovar mi matrícula consular","grupos":[["matricula","matrícula"],["renovar","renovacion","renovación","vencida","vencer"]],"preguntas":[
q("matricula_anterior","¿Tienes la matrícula consular que vas a renovar?",SI),
q("domicilio_cambio","¿Cambiaste de domicilio desde que obtuviste la matrícula?",["Sí","No","No estoy seguro"]),
q("domicilio","¿Tienes comprobante de tu domicilio actual?",["Sí","No","No estoy seguro","No aplica"]),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Matrícula consular que vas a renovar","matricula_anterior"),
("Comprobante de domicilio actual","domicilio")],"resultado":{
"prepara":"Debes comparecer personalmente con cita y presentar la matrícula que vas a renovar.",
"confirma":"Si cambiaste de residencia, debes revisar el requisito del comprobante de domicilio actual.",
"pago":"Confirma la tarifa vigente.","fuente":FUENTES["matricula"]}},

{"id":"matricula_perdida","servicio":"cita","titulo":"Perdí o me robaron mi matrícula","grupos":[["matricula","matrícula"],["perdi","perdí","perdido","robaron","robo","robada","extraviada"]],"preguntas":[
q("explicacion","¿Estás preparado para llenar el formulario donde explicas la pérdida o robo?",["Sí","No","No estoy seguro"]),
q("nacionalidad","¿Tienes ORIGINAL de tu documento de nacionalidad mexicana?",SI),
q("identidad","¿Tienes ORIGINAL de identificación con fotografía?",SI),
q("domicilio","¿Tienes ORIGINAL de comprobante de domicilio?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Formulario de pérdida o robo","explicacion"),
("Documento ORIGINAL de nacionalidad mexicana","nacionalidad"),
("Identificación ORIGINAL con fotografía","identidad"),
("Comprobante ORIGINAL de domicilio","domicilio")],"resultado":{
"prepara":"Para una matrícula perdida o robada debes explicar las circunstancias y cumplir los requisitos correspondientes.",
"confirma":"El Consulado indica que no puede emitirse una nueva matrícula sin el formulario correspondiente.",
"pago":"Confirma la tarifa vigente.","fuente":FUENTES["matricula"]}},

{"id":"matricula_menor","servicio":"cita","titulo":"Matrícula consular para un menor","grupos":[["matricula","matrícula"],["menor","hijo","hija","niño","niña","nino","nina"]],"preguntas":[
q("menor_nacionalidad","¿Tienes ORIGINAL del documento que acredita la nacionalidad mexicana del menor?",SI),
q("menor_identidad","¿Tienes ORIGINAL de una identificación aceptada del menor?",SI),
q("padres","¿Pueden presentarse ambos padres o tutores con el menor?",["Sí","No","No estoy seguro"]),
q("op7","Si falta uno de los padres, ¿ya existe la autorización correspondiente?",["Sí","No","No aplica","No estoy seguro"]),
q("padres_id","¿Tienes las identificaciones correspondientes de los padres?",SI),
q("cita","¿Ya tienes tu cita?",["Sí","No"])],"documentos":[
("Documento ORIGINAL de nacionalidad del menor","menor_nacionalidad"),
("Identificación ORIGINAL del menor","menor_identidad"),
("Identificaciones correspondientes de los padres","padres_id")],"resultado":{
"prepara":"Deben presentarse el menor y quienes ejercen la patria potestad o tutela y deben acreditarse nacionalidad, identidad y autorizaciones.",
"confirma":"La separación o divorcio no elimina por sí solo la patria potestad.",
"pago":"Confirma la tarifa vigente.","fuente":FUENTES["matricula"]}},

{"id":"registro_nacimiento_extranjero","servicio":"documento","titulo":"Registrar a mi hijo como mexicano","grupos":[["hijo","hija","nino","niño","nina","niña","bebe"],["nacimiento","nacio","nació"],["mexicano","mexicana"]],"preguntas":[
q("padre_mexicano","¿El padre o la madre es mexicano?",SI),
q("acta_extranjera","¿Tienes el acta de nacimiento extranjera ORIGINAL del hijo?",SI),
q("acta_padre","¿Tienes el acta de nacimiento mexicana del padre o madre mexicano?",SI),
q("identidad","¿Tienes las identificaciones correspondientes?",SI),
q("matrimonio","¿Los padres están casados entre sí?",["Sí","No","No estoy seguro"]),
q("cita","¿Ya tienes cita o información sobre dónde realizarás el registro?",["Sí","No","No estoy seguro"])],"documentos":[
("Acta de nacimiento extranjera ORIGINAL del hijo","acta_extranjera"),
("Acta de nacimiento mexicana del padre o madre mexicano","acta_padre"),
("Identificaciones correspondientes","identidad")],"resultado":{
"prepara":"El registro debe acreditar el nacimiento y la nacionalidad mexicana que corresponda.",
"confirma":"La autoridad puede solicitar documentación adicional según la situación familiar y los documentos presentados.",
"pago":"Confirma si existe algún costo aplicable a tu situación.","fuente":FUENTES["nacimiento"]}},

{"id":"acta_nacimiento_mexicana","servicio":"documento","titulo":"Necesito mi acta de nacimiento mexicana","grupos":[["acta"],["nacimiento","nacido","nacida"],["mexicana","mexicano","mexico","copia","certificada"]],"preguntas":[
q("registrada","¿Tu nacimiento ya está registrado en México?",["Sí","No","No estoy seguro"]),
q("estado_registro","¿Sabes en qué estado de México fue registrado?",["Sí","No","No estoy seguro"])],"documentos":[
("Información necesaria para obtener la copia certificada del acta","registrada")],"resultado":{
"prepara":"Si tu nacimiento ya está registrado en México, puedes necesitar una copia certificada del acta.",
"confirma":"Obtener una copia certificada es diferente de registrar un nacimiento que nunca fue registrado.",
"pago":"Confirma el costo y la forma de obtener la copia correspondiente.","fuente":FUENTES["documentacion"]}},

{"id":"poder_notarial","servicio":"documento","titulo":"Dar un poder a otra persona","grupos":[["poder","poderes"],["notarial","notario","notaria"],["autorizar","representar","representacion"]],"preguntas":[
q("motivo","¿Para qué necesitas el poder?",["Casa o propiedad","Dinero o banco","Trámite legal","Otro"]),
q("mexicano","¿La persona que dará el poder es mexicana?",SI),
q("identidad","¿Tiene identificación oficial vigente?",SI),
q("cita","¿Ya tienes cita o información sobre el servicio notarial?",["Sí","No","No estoy seguro"])],"documentos":[
("Identificación oficial vigente","identidad")],"resultado":{
"prepara":"Los requisitos de un poder dependen de lo que deseas autorizar y de la situación de quien lo otorga.",
"confirma":"Confirma primero qué tipo de instrumento notarial corresponde a tu situación.",
"pago":"Confirma la tarifa y forma de pago con el Consulado.","fuente":FUENTES["poder"]}},

{"id":"documento_identidad","servicio":"documento","titulo":"No sé qué identificación puedo presentar","grupos":[["identificacion","identificación","identidad"],["documento","documentos"],["id","foto"]],"preguntas":[
q("tipo_id","¿Qué identificación tienes actualmente?",["Matrícula consular","INE","Licencia mexicana","Licencia de conducir de EE.UU.","Identificación de EE.UU.","Tarjeta de Residente Permanente","Otra","No tengo identificación"])],"documentos":[],"resultado":{
"prepara":"La aceptación de una identificación depende del trámite y de las características del documento presentado.",
"confirma":"Revisa la lista oficial correspondiente al trámite antes de acudir.",
"pago":"Confirma la tarifa si el trámite que necesitas realizar tiene costo.","fuente":FUENTES["documentacion"]}},

{"id":"no_se","servicio":"documento","titulo":"No sé qué trámite necesito","grupos":[["no se","no sé","no estoy seguro","ayuda","necesito ayuda","que necesito","qué necesito"]],"preguntas":[
q("descripcion","Cuéntame con tus propias palabras qué necesitas hacer o qué problema tienes.")],"documentos":[],"resultado":{
"prepara":"Con la información proporcionada se puede identificar el trámite que más se aproxima a tu situación, pero debes confirmar los requisitos oficiales.",
"confirma":"Si tu situación no coincide exactamente con un trámite disponible, consulta directamente al Consulado.",
"pago":"No se puede determinar un pago sin identificar el trámite concreto.","fuente":FUENTES["pasaporte"]}}
]

OPCIONES=[
{"id":"pasaporte_primera_vez","texto":"Sacar mi pasaporte","servicio":"cita"},
{"id":"pasaporte_renovacion","texto":"Renovar mi pasaporte","servicio":"cita"},
{"id":"pasaporte_perdido","texto":"Perdí o me robaron mi pasaporte","servicio":"cita"},
{"id":"pasaporte_menor","texto":"Pasaporte para un menor","servicio":"cita"},
{"id":"pasaporte_extemporanea","texto":"Mi acta puede ser extemporánea","servicio":"cita"},
{"id":"pasaporte_conyuge","texto":"Apellido de mi cónyuge en el pasaporte","servicio":"cita"},
{"id":"pasaporte_naturalizado","texto":"Pasaporte de una persona naturalizada","servicio":"cita"},
{"id":"pasaporte_validez","texto":"Quiero saber la vigencia del pasaporte","servicio":"documento"},
{"id":"matricula_primera_adulto","texto":"Sacar mi matrícula consular","servicio":"cita"},
{"id":"matricula_renovacion","texto":"Renovar mi matrícula consular","servicio":"cita"},
{"id":"matricula_perdida","texto":"Perdí o me robaron mi matrícula","servicio":"cita"},
{"id":"matricula_menor","texto":"Matrícula consular para un menor","servicio":"cita"},
{"id":"acta_nacimiento_mexicana","texto":"Necesito mi acta de nacimiento","servicio":"documento"},
{"id":"registro_nacimiento_extranjero","texto":"Registrar a mi hijo como mexicano","servicio":"documento"},
{"id":"poder_notarial","texto":"Dar un poder a otra persona","servicio":"documento"},
{"id":"documento_identidad","texto":"No sé qué identificación puedo presentar","servicio":"documento"},
{"id":"no_se","texto":"No sé qué trámite necesito","servicio":"documento"}
]

def catalogo(servicio=None):
 return deepcopy([x for x in OPCIONES if not servicio or x["servicio"]==servicio])

def obtener_caso(cid):
 for c in CASOS:
  if c["id"]==cid:return deepcopy(c)
 return None

def puntuar(caso,texto):
 t=normalizar(texto);score=0
 for grupo in caso.get("grupos",[]):
  if any(normalizar(x) in t for x in grupo):score+=2
 return score

def buscar_casos(texto,servicio):
 out=[]
 for c in CASOS:
  if c["servicio"]!=servicio:continue
  s=puntuar(c,texto)
  if s>=2:out.append((s,c))
 return sorted(out,key=lambda x:x[0],reverse=True)

def identificar(servicio,texto):
 a=buscar_casos(texto,servicio)
 if not a:return None
 if len(a)==1:return a[0][1]
 if a[0][0]>=a[1][0]+2:return a[0][1]
 return [x[1] for x in a[:5]]

def extraer_perfil(texto,perfil=None):
 p=dict(perfil or {})
 raw=str(texto or "")
 if not raw:return p
 n=normalizar(raw)

 m=re.search(r"(?:nombre|me llamo)\s*[:\-]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){1,6})(?:[,.]|$)",raw,re.I)
 if m:p["nombre"]=m.group(1).strip()

 m=re.search(r"(?:telefono|tel|celular|cel)\s*[:\-]?\s*(\+?[\d\s().-]{7,20})",normalizar(raw),re.I)
 if m:p["telefono"]=m.group(1).strip()

 m=re.search(r"(?:correo|email|e-mail)\s*[:\-]?\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",raw,re.I)
 if m:p["email"]=p["correo"]=m.group(1).strip()

 m=re.search(r"(?:direccion|domicilio|vivo en|resido en)\s*[:\-]?\s*([^.;\n]+)",normalizar(raw),re.I)
 if m:p["direccion"]=m.group(1).strip()

 estados="Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming"
 m=re.search(r"\b("+estados+r")\b",raw,re.I)
 if m:p["estado"]=m.group(1).title()

 m=re.search(r"\b(\d{5})(?:-\d{4})?\b",raw)
 if m:p["zip"]=p["codigo_postal"]=m.group(1)

 if re.search(r"\bmexican[oa]?\b",n):p["nacionalidad"]="Mexicana"
 if re.search(r"\bnaturalizad[oa]\b|\bcarta de naturalizacion\b",n):p["naturalizacion"]="Sí"
 if re.search(r"\bmenor\b|\bmi hijo\b|\bmi hija\b|\bniño\b|\bniña\b|\bbebe\b",n):p["menor"]="Sí"
 return p

def fusionar_contexto(res,texto,pregunta_id=""):
 r=dict(res or {})
 r["_perfil"]=extraer_perfil(texto,r.get("_perfil"))
 if pregunta_id and str(texto).strip():r[pregunta_id]=str(texto).strip()
 return r

def inferir(caso,res,texto=""):
 r=dict(res or {})
 n=normalizar(texto)
 p=r.get("_perfil") or {}

 if p.get("menor")=="Sí" and any(x["id"]=="menor" for x in caso.get("preguntas",[])):
  r.setdefault("menor","Sí")
 if p.get("naturalizacion")=="Sí" and any(x["id"]=="naturalizado" for x in caso.get("preguntas",[])):
  r.setdefault("naturalizado","Sí")
 if re.search(r"\bya tengo cita\b|\btengo cita\b|\bcita confirmada\b",n):
  r.setdefault("cita","Sí")
 if re.search(r"\bno tengo cita\b|\bsin cita\b",n):
  r.setdefault("cita","No")
 if re.search(r"\btengo mi pasaporte\b|\btengo el pasaporte\b",n):
  r.setdefault("pasaporte_anterior","Sí")
 if re.search(r"\btengo la matricula\b|\btengo mi matricula\b|\btengo mi matrícula\b",n):
  r.setdefault("matricula_anterior","Sí")
 return r

def debe_preguntar(caso,x,res):
 cid=caso["id"];i=x["id"]
 if cid in ("pasaporte_menor","matricula_menor") and i=="op7" and afirmativo(res.get("padres")):
  return False
 if cid=="pasaporte_menor" and i=="sentencia" and afirmativo(res.get("padres")):
  return False
 if cid=="pasaporte_primera_vez" and i=="naturalizado" and res.get("_perfil",{}).get("naturalizacion")=="Sí":
  return False
 if cid=="pasaporte_primera_vez" and i=="menor" and res.get("_perfil",{}).get("menor")=="Sí":
  return False
 return True

def pregunta_actual(caso,res):
 for x in caso.get("preguntas",[]):
  if not debe_preguntar(caso,x,res):continue
  v=res.get(x["id"])
  if v is None or not str(v).strip():
   return x
 return None

def respuesta_pregunta(caso,x,res):
 return {
  "estado":"pregunta","tipo":"pregunta","catalogo":False,
  "caso":caso["id"],"titulo":caso["titulo"],
  "pregunta":x["texto"],"pregunta_id":x["id"],
  "opciones":x.get("opciones",[]),
  "respuestas":res,
  "perfil":dict(res.get("_perfil") or {})
 }

def requisitos_dinamicos(caso,res):
 cid=caso["id"];a=[]

 if cid=="pasaporte_primera_vez":
  if afirmativo(res.get("acta_extemporanea")):
   a.append("Revisa si necesitas prueba complementaria por posible acta extemporánea.")
  if afirmativo(res.get("conyuge")):
   a.append("Puede corresponder presentar acta de matrimonio.")

 if cid=="pasaporte_renovacion":
  if any(afirmativo(res.get(x)) for x in("antiguo","emergencia","restriccion","un_ano")):
   a.append("ATENCIÓN: tu pasaporte puede requerir un procedimiento diferente a una renovación normal.")
  if afirmativo(res.get("naturalizado")):
   a.append("Revisa el requisito de la carta de naturalización.")

 if cid=="pasaporte_perdido":
  a.append("Debes contar con el reporte o acta de la autoridad competente.")
  a.append("El procedimiento parte de los requisitos de una primera expedición.")

 if cid=="pasaporte_menor":
  a.append("Deben revisarse nacionalidad, identidad y autorización de quienes ejercen la patria potestad o tutela.")
  if negativo(res.get("padres")):
   a.append("ATENCIÓN: si falta un padre, revisa el procedimiento OP-7 correspondiente.")
  if afirmativo(res.get("sentencia")):
   a.append("Debes revisar y presentar la resolución judicial correspondiente.")

 if cid=="pasaporte_extemporanea":
  try:
   n=int(re.search(r"\d{4}",str(res.get("ano_nacimiento",""))).group())
   rr=int(re.search(r"\d{4}",str(res.get("ano_registro",""))).group())
   edad=rr-n
   limite=50 if n<1931 else 30 if n<=1940 else 10 if n<=1950 else 5 if n<=1976 else 1
   if edad>limite:
    a.append("NO VAYAS TODAVÍA: el registro puede ser extemporáneo y requerir prueba complementaria.")
  except:
   pass

 if cid=="pasaporte_conyuge" and afirmativo(res.get("acta_matrimonio")):
  a.append("Lleva el acta de matrimonio correspondiente.")

 if cid=="pasaporte_naturalizado":
  a.append("Lleva la carta de naturalización ORIGINAL o copia certificada cuando corresponda.")

 if cid=="pasaporte_validez":
  a.append("La vigencia depende de la edad de la persona.")

 if cid=="matricula_primera_adulto":
  a.append("Debes acreditar nacionalidad, identidad y domicilio.")
  if negativo(res.get("domicilio")):
   a.append("ATENCIÓN: necesitas revisar una alternativa aceptada si el comprobante no está disponible.")

 if cid=="matricula_renovacion" and afirmativo(res.get("domicilio_cambio")):
  a.append("Si cambiaste de residencia, lleva comprobante del domicilio actual.")

 if cid=="matricula_perdida":
  a.append("Debes llenar el formulario donde explicas la pérdida o robo.")

 if cid=="matricula_menor":
  a.append("Deben revisarse nacionalidad, identidad, padres o tutores y autorizaciones.")

 if cid=="registro_nacimiento_extranjero":
  a.append("La autoridad puede revisar la documentación familiar y solicitar documentación adicional.")

 if cid=="poder_notarial":
  a.append("El tipo de poder debe corresponder exactamente a lo que deseas autorizar.")

 return list(dict.fromkeys(a))

def documentos(caso,res):
 out=[]
 for nombre,campo in caso.get("documentos",[]):
  v=res.get(campo)
  estado="tiene" if afirmativo(v) else "falta" if negativo(v) else "revisar"
  out.append({"nombre":nombre,"campo":campo,"estado":estado})
 return out

def personas_obligatorias(caso,res):
 cid=caso["id"]
 if cid=="pasaporte_menor":
  return ["El menor debe presentarse.","Deben presentarse los padres o quienes ejerzan la patria potestad o tutela, según corresponda."]
 if cid=="matricula_menor":
  return ["El menor debe presentarse.","Deben presentarse los padres o tutores, según corresponda."]
 return []

def estado_preparacion(caso,res):
 e=requisitos_dinamicos(caso,res)
 d=documentos(caso,res)
 if any(x.startswith("NO VAYAS") or x.startswith("ATENCIÓN") for x in e):
  return "rojo"
 if any(x["estado"]=="falta" for x in d):
  return "amarillo"
 return "verde"

def resultado(caso,res):
 ds=documentos(caso,res)
 nivel=estado_preparacion(caso,res)
 esp=requisitos_dinamicos(caso,res)
 estado="ATENCIÓN / NO VAYAS TODAVÍA" if nivel=="rojo" else "TE FALTA ALGO" if nivel=="amarillo" else "PARECES LISTO"

 r=caso["resultado"]
 cid=caso["id"]
 pas=cid.startswith("pasaporte")
 mat=cid.startswith("matricula")

 tiene=[x["nombre"] for x in ds if x["estado"]=="tiene"]
 falta=[x["nombre"] for x in ds if x["estado"]=="falta"]
 revisar=[x["nombre"] for x in ds if x["estado"]=="revisar"]

 return {
  "estado":"resuelto","tipo":"resultado","caso":cid,
  "titulo":caso["titulo"],"tramite":caso["titulo"],
  "prepara":r["prepara"],"confirma":r["confirma"],"pago":r["pago"],
  "fuente":r["fuente"],"fuente_oficial":r["fuente"],
  "respuestas":res,"perfil":dict(res.get("_perfil") or {}),
  "nivel":nivel,"estado_texto":estado,
  "checklist":{"tiene":tiene,"falta":falta,"revisar":revisar,"documentos":[x["nombre"] for x in ds]},
  "documentos":ds,
  "especiales":esp,
  "personas_obligatorias":personas_obligatorias(caso,res),
  "requisitos_obligatorios":[x["nombre"] for x in ds],
  "cita":["Confirma y conserva tu cita antes de acudir."] if any(x["id"]=="cita" for x in caso["preguntas"]) else [],
  "originales":tiene or ["Presenta los documentos ORIGINALES que correspondan a tu caso."],
  "copias":[],
  "revision":"Revisa cuidadosamente todos los datos antes de firmar o imprimir.",
  "vigencia":"Menores de 3 años: 1 o 3 años. De 3 años y menores de 18: 3 o 6 años. Adultos: 3, 6 o 10 años." if pas and cid!="pasaporte_extemporanea" else "La matrícula consular tiene una vigencia de cinco años." if mat else "",
  "entrega":"La información oficial indica entrega el mismo día una vez cumplidos los requisitos; puede tomar alrededor de dos horas si no hay fallas del sistema." if pas or mat else "",
  "importante":[
   "Esta aplicación es independiente. No es el Gobierno de México ni representa a ningún Consulado.",
   "La autoridad consular puede verificar los documentos y solicitar información adicional."
  ],
  "aviso":"Esta Hoja de Ruta se basa en la información proporcionada durante la consulta y no sustituye la revisión de la autoridad consular."
 }

def iniciar(servicio,caso_id=None,respuestas=None):
 if servicio not in("cita","documento"):
  return {"estado":"error","mensaje":"Servicio no disponible.","opciones":[]}
 if caso_id:
  return seleccionar_caso(caso_id,respuestas)
 return {
  "estado":"seleccionar","tipo":"catalogo","catalogo":True,
  "servicio":servicio,
  "pregunta":"¿Qué trámite necesitas preparar?",
  "pregunta_id":"tramite",
  "opciones":catalogo(servicio),
  "respuestas":dict(respuestas or {})
 }

def seleccionar(caso_id,respuestas=None):
 return seleccionar_caso(caso_id,respuestas)

def seleccionar_caso(caso_id,respuestas=None):
 caso=obtener_caso(caso_id)
 if not caso:
  return {"estado":"error","tipo":"error","mensaje":"Trámite no encontrado.","opciones":catalogo()}
 res=dict(respuestas or {})
 res["_caso"]=caso_id
 x=pregunta_actual(caso,res)
 return respuesta_pregunta(caso,x,res) if x else resultado(caso,res)

def continuar(caso_id,respuestas=None,pregunta_id="",texto=""):
 caso=obtener_caso(caso_id)
 if not caso:
  return {"estado":"error","tipo":"error","mensaje":"Trámite no encontrado."}

 res=dict(respuestas or {})
 res["_caso"]=caso_id

 if pregunta_id and str(texto).strip():
  res[pregunta_id]=str(texto).strip()

 res=fusionar_contexto(res,texto,pregunta_id)
 res=inferir(caso,res,texto)

 x=pregunta_actual(caso,res)
 return respuesta_pregunta(caso,x,res) if x else resultado(caso,res)

def interpretar(servicio,texto,respuestas=None,pregunta_id=""):
 texto=str(texto or "").strip()
 res=fusionar_contexto(respuestas,texto,pregunta_id)
 cid=res.get("_caso")

 if cid:
  return continuar(cid,res,pregunta_id,texto)

 if not texto:
  return iniciar(servicio,None,res)

 encontrados=identificar(servicio,texto)

 if not encontrados:
  r=iniciar(servicio,None,res)
  r["mensaje"]="No pudimos identificar todavía el trámite. Elige la opción que más se parezca a tu situación."
  return r

 if isinstance(encontrados,list):
  return {
   "estado":"seleccionar","tipo":"seleccionar_caso","catalogo":True,
   "servicio":servicio,
   "pregunta":"¿Cuál de estas opciones se parece más a lo que necesitas?",
   "pregunta_id":"tramite",
   "opciones":[{"id":x["id"],"texto":x["titulo"],"servicio":x["servicio"]} for x in encontrados],
   "respuestas":res
  }

 caso=encontrados
 res["_caso"]=caso["id"]
 res=inferir(caso,res,texto)
 return continuar(caso["id"],res)

def caso_por_texto(servicio,texto):
 c=identificar(servicio,texto)
 if isinstance(c,list):
  return [{"id":x["id"],"texto":x["titulo"]} for x in c]
 if c:
  return {"id":c["id"],"texto":c["titulo"]}
 return None
