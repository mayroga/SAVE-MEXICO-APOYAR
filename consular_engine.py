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
    texto=re.sub(r"[áàäâ]","a",texto)
    texto=re.sub(r"[éèëê]","e",texto)
    texto=re.sub(r"[íìïî]","i",texto)
    texto=re.sub(r"[óòöô]","o",texto)
    texto=re.sub(r"[úùüû]","u",texto)
    texto=re.sub(r"ñ","n",texto)
    texto=re.sub(r"[^a-z0-9\s]"," ",texto)
    return re.sub(r"\s+"," ",texto)

def contiene(texto,palabras):
    return any(p in texto for p in palabras)

CASOS=[
 {
  "id":"pasaporte_perdido",
  "servicio":"cita",
  "titulo":"PASAPORTE PERDIDO, ROBADO O DESTRUIDO",
  "palabras":["pasaporte perdido","pasaporte robado","me robaron el pasaporte","perdi mi pasaporte","perdi el pasaporte","pasaporte extraviado","me robaron mi pasaporte"],
  "preguntas":[
   {
    "id":"reporte",
    "texto":"¿Ya tienes un reporte de la policía sobre la pérdida o robo?",
    "opciones":["Sí","No","No estoy seguro"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "Tu caso corresponde a reposición de pasaporte por pérdida o robo.",
    "Si fue perdido o robado, prepara el reporte de la autoridad competente cuando corresponda.",
    "Debes acudir personalmente a tu cita.",
    "La SRE indica que para estos casos se presentan los documentos como en una expedición por primera vez."
   ],
   "confirma":[
    "Confirma con el Consulado que te corresponde qué documentos aceptará específicamente en tu caso."
   ],
   "fuente":FUENTES["pasaporte"]
  }
 },
 {
  "id":"pasaporte_renovacion",
  "servicio":"cita",
  "titulo":"RENOVACIÓN DE PASAPORTE",
  "palabras":["renovar pasaporte","renovacion pasaporte","quiero renovar mi pasaporte","se me vence el pasaporte","pasaporte vencido","cambiar pasaporte"],
  "preguntas":[
   {
    "id":"tiene_pasaporte",
    "texto":"¿Tienes contigo el pasaporte que vas a renovar?",
    "opciones":["Sí","No"]
   },
   {
    "id":"menor",
    "texto":"¿La cita es para una persona menor de 18 años?",
    "opciones":["Sí","No"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "Lleva el pasaporte que vas a renovar.",
    "Debes acudir personalmente a la oficina consular.",
    "Debes cubrir el pago de derechos correspondiente.",
    "La SRE indica que se toman biométricos, como fotografía y huellas, en el trámite."
   ],
   "confirma":[
    "Si la cita es para un menor, revisa además las reglas de autorización y comparecencia de padres, tutores o quien ejerza la patria potestad."
   ],
   "fuente":FUENTES["pasaporte"]
  }
 },
 {
  "id":"pasaporte_primera_vez",
  "servicio":"cita",
  "titulo":"PASAPORTE POR PRIMERA VEZ",
  "palabras":["sacar pasaporte","nuevo pasaporte","primer pasaporte","pasaporte por primera vez","quiero mi pasaporte"],
  "preguntas":[
   {
    "id":"menor",
    "texto":"¿El pasaporte es para una persona menor de 18 años?",
    "opciones":["Sí","No"]
   },
   {
    "id":"nacionalidad",
    "texto":"¿Tienes un documento original que compruebe tu nacionalidad mexicana?",
    "opciones":["Sí","No","No estoy seguro"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "Debes acreditar tu nacionalidad mexicana con un documento aceptado por la SRE.",
    "También debes acreditar tu identidad con un documento oficial con fotografía.",
    "Debes acudir personalmente a la oficina consular.",
    "Debes cubrir el pago de derechos correspondiente."
   ],
   "confirma":[
    "Si no tienes documentos para acreditar nacionalidad o identidad, no adivinaremos cuál te aceptarán: confirma tu caso con el Consulado antes de acudir."
   ],
   "fuente":FUENTES["pasaporte"]
  }
 },
 {
  "id":"matricula",
  "servicio":"cita",
  "titulo":"MATRÍCULA CONSULAR",
  "palabras":["matricula","matricula consular","sacar matricula","renovar matricula","documento consular","identificacion consular"],
  "preguntas":[
   {
    "id":"primera",
    "texto":"¿Es la primera vez que solicitas tu Matrícula Consular?",
    "opciones":["Sí","No","No estoy seguro"]
   },
   {
    "id":"nacionalidad",
    "texto":"¿Tienes un documento original que compruebe tu nacionalidad mexicana?",
    "opciones":["Sí","No","No estoy seguro"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "La Matrícula Consular acredita nacionalidad e identidad y registra que eres mexicano en el exterior.",
    "Prepara un documento original que compruebe tu nacionalidad mexicana.",
    "Prepara una identificación oficial original con fotografía.",
    "Prepara un comprobante de domicilio dentro de la circunscripción consular.",
    "Debes completar la solicitud correspondiente y cubrir el pago del trámite."
   ],
   "confirma":[
    "El Consulado correspondiente puede pedir documentación adicional según tu situación."
   ],
   "fuente":FUENTES["matricula"]
  }
 },
 {
  "id":"registro_nacimiento_extranjero",
  "servicio":"documento",
  "titulo":"REGISTRO DE NACIMIENTO DE UNA PERSONA NACIDA EN EL EXTRANJERO",
  "palabras":["mi hijo nacio aqui","mi hija nacio aqui","mi hijo nacio en estados unidos","mi hija nacio en estados unidos","registrar a mi hijo","registrar a mi hija","hacer mexicano a mi hijo","hacer mexicana a mi hija","nacio en estados unidos y quiero registrarlo","nacio en usa"],
  "preguntas":[
   {
    "id":"padre_mexicano",
    "texto":"¿El papá, la mamá o ambos son mexicanos?",
    "opciones":["Sí","No","No estoy seguro"]
   },
   {
    "id":"acta_extranjera",
    "texto":"¿Tienes el acta de nacimiento extranjera de la persona que quieres registrar?",
    "opciones":["Sí","No"]
   },
   {
    "id":"acta_padre",
    "texto":"¿Tienes el acta de nacimiento mexicana del papá o de la mamá mexicana?",
    "opciones":["Sí","No","No estoy seguro"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "SRE contempla el registro consular de una persona nacida en el extranjero cuando al menos uno de sus padres es mexicano.",
    "Prepara el acta de nacimiento extranjera de la persona que será registrada.",
    "Prepara el acta de nacimiento mexicana del padre o madre que transmite la nacionalidad.",
    "Prepara identificaciones oficiales vigentes con fotografía de las personas que intervienen.",
    "La información oficial también contempla la comparecencia de los padres y de la persona registrada, con excepciones específicas."
   ],
   "confirma":[
    "Revisa con el Consulado correspondiente si tu acta extranjera, identificaciones y situación familiar requieren documentos adicionales.",
    "Los nombres de los documentos deben coincidir; las oficinas consulares pueden revisar la documentación antes de aprobar el registro."
   ],
   "fuente":FUENTES["nacimiento"]
  }
 },
 {
  "id":"poder_notarial",
  "servicio":"documento",
  "titulo":"PODER NOTARIAL",
  "palabras":["poder","poder notarial","dar poder","mandar un poder","poder para mexico","necesito un poder","quiero darle poder","representarme en mexico","que alguien haga un tramite por mi"],
  "preguntas":[
   {
    "id":"objetivo",
    "texto":"¿Para qué necesitas el poder?",
    "opciones":["Propiedad o inmueble","Banco o dinero","Trámite o documento","Herencia","Otro"]
   },
   {
    "id":"mexicano",
    "texto":"¿La persona que va a otorgar el poder es mexicana?",
    "opciones":["Sí","No","Tiene doble nacionalidad"]
   },
   {
    "id":"casado",
    "texto":"¿Está casada la persona que dará el poder?",
    "opciones":["Sí","No"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "El poder notarial permite autorizar a otra persona para actuar en nombre del otorgante en asuntos determinados.",
    "Prepara una identificación oficial vigente con fotografía.",
    "Prepara los datos completos de la persona que recibirá el poder.",
    "Prepara información y documentos relacionados con el asunto para el cual se utilizará el poder.",
    "El Consulado de México en Miami señala que la persona solicitante es responsable de proporcionar la información y documentación necesaria para elaborar correctamente el poder."
   ],
   "confirma":[
    "Si el poder se relaciona con propiedades, actos de dominio, administración u otros asuntos especiales, pueden existir requisitos adicionales.",
    "Si la persona está casada, determinadas operaciones pueden requerir la comparecencia y documentación del cónyuge."
   ],
   "fuente":FUENTES["poder"]
  }
 },
 {
  "id":"acta_nacimiento_mexicana",
  "servicio":"documento",
  "titulo":"COPIA CERTIFICADA DE ACTA DE NACIMIENTO MEXICANA",
  "palabras":["copia de acta","acta de nacimiento mexicana","sacar acta mexicana","copia certificada","necesito mi acta","acta mexicana"],
  "preguntas":[
   {
    "id":"registro",
    "texto":"¿Tu nacimiento ya está registrado en México o en una oficina consular mexicana?",
    "opciones":["Sí","No","No estoy seguro"]
   }
  ],
  "resolver":lambda r: {
   "prepara":[
    "Si tu nacimiento ya está registrado, puedes solicitar información sobre la expedición de una copia certificada.",
    "Debes tener los datos necesarios para localizar el acta.",
    "En el Consulado de Miami existen servicios de copias certificadas para determinados registros."
   ],
   "confirma":[
    "La disponibilidad depende del tipo de acta y del lugar donde fue registrada. Confirma con la representación correspondiente antes de acudir."
   ],
   "fuente":FUENTES["poder"]
  }
 }
]

def buscar_casos(texto,servicio):
    t=normalizar(texto)
    encontrados=[]
    for caso in CASOS:
        if caso["servicio"]!=servicio:
            continue
        score=0
        for palabra in caso["palabras"]:
            p=normalizar(palabra)
            if p in t:
                score+=3 if " " in p else 1
        if score:
            encontrados.append((score,caso))
    encontrados.sort(key=lambda x:x[0],reverse=True)
    return [x[1] for x in encontrados]

def siguiente_pregunta(caso,respuestas):
    for q in caso["preguntas"]:
        if q["id"] not in respuestas:
            return deepcopy(q)
    return None

def resolver(caso,respuestas):
    datos=caso["resolver"](respuestas)
    return {
        "estado":"resuelto",
        "caso":caso["id"],
        "titulo":caso["titulo"],
        "prepara":datos["prepara"],
        "confirma":datos["confirma"],
        "fuente":datos["fuente"]
    }

def iniciar(servicio,texto=""):
    casos=buscar_casos(texto,servicio) if texto else []

    if not casos:
        return {
            "estado":"necesita_descripcion",
            "pregunta":"Cuéntame con tus propias palabras qué necesitas resolver.",
            "opciones":[]
        }

    if len(casos)>1 and casos[0]["id"]!=casos[1]["id"]:
        return {
            "estado":"seleccionar",
            "pregunta":"¿Cuál de estas situaciones se parece más a la tuya?",
            "opciones":[x["titulo"] for x in casos[:4]],
            "casos":[x["id"] for x in casos[:4]]
        }

    caso=casos[0]
    q=siguiente_pregunta(caso,{})
    return {
        "estado":"pregunta" if q else "resuelto",
        "caso":caso["id"],
        "titulo":caso["titulo"],
        "pregunta":q["texto"] if q else "",
        "opciones":q["opciones"] if q else []
    }

def continuar(caso_id,respuestas):
    caso=next((x for x in CASOS if x["id"]==caso_id),None)

    if not caso:
        return {
            "estado":"error",
            "mensaje":"No encontramos ese caso."
        }

    q=siguiente_pregunta(caso,respuestas)

    if q:
        return {
            "estado":"pregunta",
            "caso":caso_id,
            "pregunta":q["texto"],
            "opciones":q["opciones"],
            "pregunta_id":q["id"]
        }

    return resolver(caso,respuestas)

def interpretar(servicio,texto,respuestas=None):
    respuestas=respuestas or {}

    if not texto.strip():
        return {
            "estado":"necesita_descripcion",
            "pregunta":"Cuéntame con tus propias palabras qué necesitas resolver.",
            "opciones":[]
        }

    casos=buscar_casos(texto,servicio)

    if not casos:
        return {
            "estado":"no_identificado",
            "pregunta":"No quiero adivinar. ¿Puedes explicarme un poco más qué necesitas hacer?",
            "opciones":[]
        }

    if len(casos)>1 and casos[0]["id"]!=casos[1]["id"] and casos[0]["id"] not in respuestas.get("_confirmado",[]):
        return {
            "estado":"seleccionar",
            "pregunta":"¿Cuál de estas opciones se parece más a lo que necesitas?",
            "opciones":[x["titulo"] for x in casos[:4]],
            "casos":[x["id"] for x in casos[:4]]
        }

    caso=casos[0]
    q=siguiente_pregunta(caso,respuestas)

    if q:
        return {
            "estado":"pregunta",
            "caso":caso["id"],
            "pregunta_id":q["id"],
            "pregunta":q["texto"],
            "opciones":q["opciones"]
        }

    return resolver(caso,respuestas)

def validar_resultado(resultado):
    obligatorios=("estado","titulo","prepara","confirma","fuente")
    return all(k in resultado for k in obligatorios)

def catalogo():
    return [
        {
            "id":c["id"],
            "servicio":c["servicio"],
            "titulo":c["titulo"],
            "fuente":c["resolver"]({}).get("fuente","")
        }
        for c in CASOS
    ]
