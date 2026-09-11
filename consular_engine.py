import re
from copy import deepcopy

FUENTES={
 "pasaporte":"https://www.gob.mx/sre/acciones-y-programas/tramite-de-pasaporte-8014",
 "matricula":"https://consulmex.sre.gob.mx/miami/index.php/matricula-consular",
 "nacimiento":"https://www.gob.mx/tramites/ficha/registro-de-nacimiento-en-el-extranjero/SRE92",
 "poder":"https://consulmex.sre.gob.mx/miami/index.php/poderes-notariales",
 "documentacion":"https://consulmex.sre.gob.mx/miami/index.php/avisos/4-documentos-de-identidad/dconsular"
}

def normalizar(texto):
 texto=(texto or "").lower().strip()
 tabla=str.maketrans("áàäâéèëêíìïîóòöôúùüûñ","aaaaeeeeiiiioooouuuun")
 texto=texto.translate(tabla)
 texto=re.sub(r"[^a-z0-9\s]"," ",texto)
 return re.sub(r"\s+"," ",texto).strip()

def palabras(texto):
 return set(normalizar(texto).split())

def coincide(texto,frases):
 t=normalizar(texto);w=palabras(t)
 for frase in frases:
  f=normalizar(frase)
  if f in t:return True
  fw=set(f.split())
  if len(fw)>=2 and len(fw&w)>=max(2,len(fw)-1):return True
 return False

CASOS=[
{
 "id":"pasaporte_primera_vez","servicio":"cita","titulo":"Sacar mi pasaporte",
 "grupos":[["pasaporte"],["sacar","obtener","tramitar","solicitar","hacer","nuevo","primera vez"]],
 "preguntas":[
  {"id":"menor","texto":"¿El pasaporte es para un menor de edad?","opciones":["Sí","No"]},
  {"id":"nacionalidad","texto":"¿Tienes un documento que compruebe que eres mexicano?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"identidad","texto":"¿Tienes una identificación oficial con fotografía?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienes tu cita?","opciones":["Sí","No"]}
 ],
 "documentos":[
  ("Acreditación de nacionalidad mexicana","nacionalidad"),
  ("Identificación oficial con fotografía","identidad"),
  ("Confirmación de cita","cita")
 ],
 "resultado":{
  "prepara":"Debes acreditar tu nacionalidad mexicana e identidad y acudir con tu cita. Si es para un menor, pueden existir requisitos adicionales para padres o tutores.",
  "confirma":"La autoridad consular confirma los documentos exactos de tu caso y la forma de pago vigente.",
  "pago":"Confirma la tarifa y las formas de pago aceptadas por el consulado antes de acudir.",
  "fuente":FUENTES["pasaporte"]
 }
},
{
 "id":"pasaporte_renovacion","servicio":"cita","titulo":"Renovar mi pasaporte",
 "grupos":[["pasaporte"],["renovar","renovacion","vencer","vencido","caducado","expirado"]],
 "preguntas":[
  {"id":"tiene_pasaporte","texto":"¿Todavía tienes tu pasaporte anterior?","opciones":["Sí","No"]},
  {"id":"menor","texto":"¿El pasaporte es para un menor de edad?","opciones":["Sí","No"]},
  {"id":"identidad","texto":"¿Tienes una identificación oficial con fotografía?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienes tu cita?","opciones":["Sí","No"]}
 ],
 "documentos":[
  ("Pasaporte mexicano anterior","tiene_pasaporte"),
  ("Identificación oficial con fotografía","identidad"),
  ("Confirmación de cita","cita")
 ],
 "resultado":{
  "prepara":"Para renovar debes presentar tu pasaporte anterior y cumplir con los requisitos de identidad, cita y pago.",
  "confirma":"Si el pasaporte fue perdido, robado o destruido, el procedimiento puede ser diferente. Si es para un menor, pueden existir requisitos adicionales.",
  "pago":"Confirma la tarifa y las formas de pago aceptadas por el consulado antes de acudir.",
  "fuente":FUENTES["pasaporte"]
 }
},
{
 "id":"pasaporte_perdido","servicio":"cita","titulo":"Perdí o me robaron mi pasaporte",
 "grupos":[["pasaporte"],["perdi","perdido","perdi mi","robaron","robo","robado","extraviado","destruido"]],
 "preguntas":[
  {"id":"reporte","texto":"¿Ya hiciste un reporte de la pérdida o robo ante una autoridad?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"nacionalidad","texto":"¿Tienes un documento que compruebe que eres mexicano?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"identidad","texto":"¿Tienes una identificación oficial con fotografía?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienes tu cita?","opciones":["Sí","No"]}
 ],
 "documentos":[
  ("Reporte de pérdida o robo, cuando corresponda","reporte"),
  ("Acreditación de nacionalidad mexicana","nacionalidad"),
  ("Identificación oficial con fotografía","identidad"),
  ("Confirmación de cita","cita")
 ],
 "resultado":{
  "prepara":"Un pasaporte perdido, robado o destruido no debe tratarse como una renovación normal. Debes acreditar tu identidad y nacionalidad y atender las indicaciones del consulado.",
  "confirma":"Confirma con el consulado qué reporte o documento debes presentar en tu situación antes de acudir.",
  "pago":"Confirma la tarifa y las formas de pago aceptadas por el consulado.",
  "fuente":FUENTES["pasaporte"]
 }
},
{
 "id":"matricula","servicio":"cita","titulo":"Sacar mi matrícula consular",
 "grupos":[["matricula","matrícula"],["consular","consulado","identificacion","identificación"]],
 "preguntas":[
  {"id":"primera","texto":"¿Es la primera vez que solicitas tu matrícula consular?","opciones":["Sí","No"]},
  {"id":"nacionalidad","texto":"¿Tienes un documento que compruebe que eres mexicano?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"identidad","texto":"¿Tienes una identificación con fotografía?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"domicilio","texto":"¿Tienes un comprobante de domicilio a tu nombre?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"cita","texto":"¿Ya tienes tu cita?","opciones":["Sí","No"]}
 ],
 "documentos":[
  ("Acreditación de nacionalidad mexicana","nacionalidad"),
  ("Identificación con fotografía","identidad"),
  ("Comprobante de domicilio","domicilio"),
  ("Confirmación de cita","cita")
 ],
 "resultado":{
  "prepara":"La matrícula consular requiere acreditar nacionalidad e identidad y, según el trámite, comprobar domicilio dentro de la circunscripción correspondiente.",
  "confirma":"El consulado puede revisar documentos adicionales según tu situación. Confirma los documentos aceptados antes de acudir.",
  "pago":"Confirma la tarifa y las formas de pago aceptadas por el consulado.",
  "fuente":FUENTES["matricula"]
 }
},
{
 "id":"registro_nacimiento_extranjero","servicio":"documento","titulo":"Registrar a mi hijo como mexicano",
 "grupos":[
  ["hijo","hija","nino","niño","nina","niña","bebe","bebé"],
  ["nacimiento","nacio","nació","nacido","nacida"],
  ["estados unidos","usa","eeuu","extranjero","america","américa"]
 ],
 "preguntas":[
  {"id":"padre_mexicano","texto":"¿El padre o la madre es mexicano?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"acta_extranjera","texto":"¿Tienes el acta de nacimiento extranjera de tu hijo?","opciones":["Sí","No"]},
  {"id":"acta_padre","texto":"¿Tienes el acta de nacimiento mexicana del padre o madre mexicano?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"identidad","texto":"¿Tienes identificaciones oficiales de los padres?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "documentos":[
  ("Acta de nacimiento extranjera del hijo","acta_extranjera"),
  ("Acta de nacimiento mexicana del padre o madre mexicano","acta_padre"),
  ("Identificaciones oficiales correspondientes","identidad")
 ],
 "resultado":{
  "prepara":"Para registrar el nacimiento de una persona nacida en el extranjero se debe comprobar el nacimiento y la nacionalidad mexicana del padre o madre.",
  "confirma":"La autoridad consular revisará los documentos originales y las condiciones del registro. Pueden existir requisitos adicionales según el caso.",
  "pago":"El registro de nacimiento en el extranjero se realiza sin costo cuando corresponde a este trámite de registro.",
  "fuente":FUENTES["nacimiento"]
 }
},
{
 "id":"poder_notarial","servicio":"documento","titulo":"Dar un poder a otra persona",
 "grupos":[["poder","poderes"],["notarial","notario","notaria"],["autorizar","autorice","representar","representarme","representacion"]],
 "preguntas":[
  {"id":"motivo","texto":"¿Para qué necesitas dar el poder?","opciones":["Casa o propiedad","Dinero o banco","Trámite legal","Otro"]},
  {"id":"mexicano","texto":"¿La persona que dará el poder es mexicana?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"matrimonio","texto":"¿La persona que dará el poder está casada?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"identidad","texto":"¿Tiene una identificación oficial vigente?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "documentos":[
  ("Identificación oficial vigente de quien otorga el poder","identidad"),
  ("Información y documentos relacionados con el poder","motivo")
 ],
 "resultado":{
  "prepara":"Los poderes notariales tienen requisitos que dependen de lo que se quiere autorizar y de la situación de la persona que otorga el poder.",
  "confirma":"No firmes documentos preparados por terceros sin confirmar primero con el consulado qué tipo de poder corresponde y qué documentos debes llevar.",
  "pago":"Confirma la tarifa y la forma de pago del poder con el consulado.",
  "fuente":FUENTES["poder"]
 }
},
{
 "id":"acta_nacimiento_mexicana","servicio":"documento","titulo":"Necesito mi acta de nacimiento",
 "grupos":[["acta"],["nacimiento","nacido","nacida"],["mexicana","mexicano","mexico","copia","certificada"]],
 "preguntas":[
  {"id":"registrada","texto":"¿Tu nacimiento ya está registrado en México?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "documentos":[
  ("Datos correctos de tu registro de nacimiento","registrada")
 ],
 "resultado":{
  "prepara":"Si tu nacimiento ya está registrado en México, puedes necesitar una copia certificada del acta.",
  "confirma":"Si nunca fuiste registrado en México, el procedimiento es diferente y no debes solicitar simplemente una copia.",
  "pago":"Confirma el costo y la forma de obtener la copia correspondiente.",
  "fuente":FUENTES["documentacion"]
 }
}
]

OPCIONES=[
 {"id":"pasaporte_primera_vez","texto":"Sacar mi pasaporte","servicio":"cita"},
 {"id":"pasaporte_renovacion","texto":"Renovar mi pasaporte","servicio":"cita"},
 {"id":"pasaporte_perdido","texto":"Perdí o me robaron mi pasaporte","servicio":"cita"},
 {"id":"matricula","texto":"Sacar mi matrícula consular","servicio":"cita"},
 {"id":"acta_nacimiento_mexicana","texto":"Necesito mi acta de nacimiento","servicio":"documento"},
 {"id":"registro_nacimiento_extranjero","texto":"Registrar a mi hijo como mexicano","servicio":"documento"},
 {"id":"poder_notarial","texto":"Dar un poder a otra persona","servicio":"documento"},
 {"id":"no_se","texto":"No sé qué necesito","servicio":"documento"}
]

def catalogo(servicio=None):
 return deepcopy([x for x in OPCIONES if not servicio or x["servicio"]==servicio])

def obtener_caso(caso_id):
 for caso in CASOS:
  if caso["id"]==caso_id:return deepcopy(caso)
 return None

def puntuar(caso,texto):
 t=normalizar(texto);w=palabras(t);score=0
 for grupo in caso["grupos"]:
  for x in grupo:
   x=normalizar(x)
   if x and (x in t or (" " not in x and x in w)):
    score+=2;break
 return score

def buscar_casos(texto,servicio):
 salida=[]
 for caso in CASOS:
  if caso["servicio"]!=servicio:continue
  s=puntuar(caso,texto)
  if s>=2:salida.append((s,caso))
 salida.sort(key=lambda x:x[0],reverse=True)
 return [x[1] for x in salida]

def identificar(servicio,texto):
 casos=buscar_casos(texto,servicio)
 if not casos:return None
 if len(casos)==1:return casos[0]
 a,b=casos[0],casos[1]
 return a if puntuar(a,texto)>=puntuar(b,texto)+2 else casos

def pregunta_actual(caso,respuestas):
 for q in caso.get("preguntas",[]):
  if q["id"] not in respuestas:return q
 return None

def respuesta_pregunta(caso,q):
 return {
  "estado":"pregunta","caso":caso["id"],"titulo":caso["titulo"],
  "pregunta":q["texto"],"pregunta_id":q["id"],
  "opciones":q.get("opciones",[])
 }

def afirmativo(valor):
 return normalizar(valor) in {"si","sí","yes","true","1"}

def negativo(valor):
 return normalizar(valor) in {"no","false","0"}

def checklist(caso,respuestas):
 tiene=[];falta=[];revisar=[]
 for nombre,campo in caso.get("documentos",[]):
  v=respuestas.get(campo)
  if afirmativo(v):tiene.append(nombre)
  elif negativo(v):falta.append(nombre)
  else:revisar.append(nombre)
 return {"tiene":tiene,"falta":falta,"revisar":revisar}

def documentos_base(caso):
 ids=[x[0] for x in caso.get("documentos",[])]
 return ids

def resultado(caso,respuestas=None):
 respuestas=dict(respuestas or {})
 r=caso["resultado"]
 c=checklist(caso,respuestas)
 return {
  "estado":"resuelto",
  "caso":caso["id"],
  "titulo":caso["titulo"],
  "prepara":r["prepara"],
  "confirma":r["confirma"],
  "pago":r.get("pago","Confirma el costo y la forma de pago vigente con tu consulado."),
  "fuente":r["fuente"],
  "respuestas":respuestas,
  "checklist":{
   "tiene":c["tiene"],
   "falta":c["falta"],
   "revisar":c["revisar"],
   "documentos":documentos_base(caso)
  },
  "ruta":{
   "tramite":caso["titulo"],
   "llevar_original":"Lleva los documentos originales que correspondan a tu caso.",
   "copias":"Lleva las copias que indique tu consulado para ese trámite.",
   "cita":"Lleva o conserva la confirmación de tu cita según las instrucciones de tu consulado.",
   "pago":r.get("pago","Confirma el costo y la forma de pago vigente.")
  },
  "aviso":"Esta aplicación es una guía. No es el Gobierno de México y el consulado puede pedir documentación adicional."
 }

def iniciar(servicio):
 if servicio not in ("cita","documento"):
  return {"estado":"error","mensaje":"Servicio no disponible."}
 opciones=catalogo(servicio)
 return {
  "estado":"necesita_descripcion",
  "pregunta":"¿Qué necesitas?",
  "opciones":opciones
 }

def seleccionar(caso_id):
 caso=obtener_caso(caso_id)
 if not caso:return {"estado":"no_identificado","mensaje":"No encontramos esa opción."}
 q=caso.get("preguntas",[])
 return respuesta_pregunta(caso,q[0]) if q else resultado(caso,{})

def continuar(caso_id,respuestas=None):
 respuestas=dict(respuestas or {})
 caso=obtener_caso(caso_id)
 if not caso:return {"estado":"no_identificado","mensaje":"No encontramos ese trámite."}
 q=pregunta_actual(caso,respuestas)
 if q:return respuesta_pregunta(caso,q)
 return resultado(caso,respuestas)

def interpretar(servicio,texto,respuestas=None):
 respuestas=dict(respuestas or {})
 texto=(texto or "").strip()
 caso_id=respuestas.get("_caso")
 if caso_id:return continuar(caso_id,respuestas)
 if not texto:return iniciar(servicio)

 directo=obtener_caso(texto)
 if directo and directo["servicio"]==servicio:
  respuestas["_caso"]=directo["id"]
  return continuar(directo["id"],respuestas)

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
   "pregunta":"¿Cuál de estas opciones se parece a lo que necesitas?",
   "opciones":[{"id":x["id"],"texto":x["titulo"]} for x in encontrados]
  }

 respuestas["_caso"]=encontrados["id"]
 return continuar(encontrados["id"],respuestas)
