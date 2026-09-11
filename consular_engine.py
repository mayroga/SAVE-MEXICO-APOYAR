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
    t=normalizar(texto)
    w=palabras(t)
    for frase in frases:
        f=normalizar(frase)
        if f in t:
            return True
        fw=set(f.split())
        if len(fw)>=2 and len(fw&w)>=max(2,len(fw)-1):
            return True
    return False

# ---------------------------------------------------------
# CASOS REALES PRINCIPALES
# ---------------------------------------------------------

CASOS=[
{
 "id":"pasaporte_primera_vez","servicio":"cita",
 "titulo":"Sacar mi pasaporte",
 "grupos":[
  ["pasaporte"],
  ["sacar","obtener","tramitar","solicitar","hacer","nuevo","primera vez"]
 ],
 "preguntas":[
  {"id":"menor","texto":"¿El pasaporte es para un menor de edad?","opciones":["Sí","No"]},
  {"id":"nacionalidad","texto":"¿Tienes un documento que compruebe que eres mexicano?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "resultado":{
  "prepara":"Para un pasaporte por primera vez debes preparar la documentación que compruebe tu nacionalidad mexicana y tu identidad. También debes tener tu cita y considerar el pago correspondiente.",
  "confirma":"Si es para un menor, pueden existir requisitos adicionales para sus padres o tutores. Confirma los documentos exactos antes de acudir.",
  "fuente":FUENTES["pasaporte"]
 }
},
{
 "id":"pasaporte_renovacion","servicio":"cita",
 "titulo":"Renovar mi pasaporte",
 "grupos":[
  ["pasaporte"],
  ["renovar","renovacion","vencer","vencido","caducado","expirado"]
 ],
 "preguntas":[
  {"id":"tiene_pasaporte","texto":"¿Todavía tienes tu pasaporte anterior?","opciones":["Sí","No"]},
  {"id":"menor","texto":"¿El pasaporte es para un menor de edad?","opciones":["Sí","No"]}
 ],
 "resultado":{
  "prepara":"Para renovar, normalmente debes llevar tu pasaporte anterior y cumplir con los requisitos de identidad, cita y pago.",
  "confirma":"Si lo perdiste, te lo robaron o está destruido, no debes tratarlo como una renovación normal. El procedimiento puede cambiar.",
  "fuente":FUENTES["pasaporte"]
 }
},
{
 "id":"pasaporte_perdido","servicio":"cita",
 "titulo":"Perdí o me robaron mi pasaporte",
 "grupos":[
  ["pasaporte"],
  ["perdi","perdido","perdi mi","robaron","robo","robado","extraviado","destruido"]
 ],
 "preguntas":[
  {"id":"reporte","texto":"¿Ya hiciste un reporte de la pérdida o robo ante una autoridad?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "resultado":{
  "prepara":"Si tu pasaporte fue perdido, robado o destruido, el trámite no debe tratarse como una renovación normal.",
  "confirma":"La autoridad consular puede pedir un reporte y documentos de identidad y nacionalidad. Confirma exactamente qué debes presentar antes de acudir.",
  "fuente":FUENTES["pasaporte"]
 }
},
{
 "id":"matricula","servicio":"cita",
 "titulo":"Sacar mi matrícula consular",
 "grupos":[
  ["matricula","matrícula"],
  ["consular","consulado","identificacion","identificación"]
 ],
 "preguntas":[
  {"id":"primera","texto":"¿Es la primera vez que solicitas tu matrícula consular?","opciones":["Sí","No"]},
  {"id":"nacionalidad","texto":"¿Tienes un documento que compruebe que eres mexicano?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "resultado":{
  "prepara":"La matrícula consular requiere comprobar tu nacionalidad mexicana y tu identidad, además de cumplir con los requisitos del consulado donde harás el trámite.",
  "confirma":"Los documentos aceptados pueden depender de tu situación. Revisa la información oficial antes de acudir.",
  "fuente":FUENTES["matricula"]
 }
},
{
 "id":"registro_nacimiento_extranjero","servicio":"documento",
 "titulo":"Registrar a mi hijo como mexicano",
 "grupos":[
  ["hijo","hija","nino","niño","nina","niña","bebe","bebé"],
  ["nacimiento","nacio","nació","nacido","nacida"],
  ["estados unidos","usa","eeuu","extranjero","america","américa"]
 ],
 "preguntas":[
  {"id":"padre_mexicano","texto":"¿El padre o la madre es mexicano?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"acta_extranjera","texto":"¿Tienes el acta de nacimiento extranjera de tu hijo?","opciones":["Sí","No"]},
  {"id":"acta_padre","texto":"¿Tienes el acta de nacimiento mexicana del padre o madre mexicano?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "resultado":{
  "prepara":"Para registrar en México el nacimiento de una persona nacida en el extranjero, normalmente se debe comprobar el nacimiento y la nacionalidad mexicana del padre o madre.",
  "confirma":"La autoridad consular revisará los documentos originales y las condiciones del registro. El registro de nacimiento en el extranjero es un trámite específico y debe confirmarse con el consulado.",
  "fuente":FUENTES["nacimiento"]
 }
},
{
 "id":"poder_notarial","servicio":"documento",
 "titulo":"Dar un poder a otra persona",
 "grupos":[
  ["poder","poderes"],
  ["notarial","notario","notaria","notaría"],
  ["autorizar","autorice","representar","representarme","representacion","representación"]
 ],
 "preguntas":[
  {"id":"motivo","texto":"¿Para qué necesitas dar el poder?","opciones":["Casa o propiedad","Dinero o banco","Trámite legal","Otro"]},
  {"id":"mexicano","texto":"¿La persona que dará el poder es mexicana?","opciones":["Sí","No","No estoy seguro"]},
  {"id":"matrimonio","texto":"¿La persona que dará el poder está casada?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "resultado":{
  "prepara":"Los poderes notariales tienen requisitos que dependen de lo que se quiere autorizar y de la situación de la persona que otorga el poder.",
  "confirma":"No firmes documentos preparados por terceros sin confirmar primero con el consulado qué tipo de poder corresponde y qué documentos debes llevar.",
  "fuente":FUENTES["poder"]
 }
},
{
 "id":"acta_nacimiento_mexicana","servicio":"documento",
 "titulo":"Necesito mi acta de nacimiento",
 "grupos":[
  ["acta"],
  ["nacimiento","nacido","nacida"],
  ["mexicana","mexicano","mexico","méxico","copia","certificada"]
 ],
 "preguntas":[
  {"id":"registrada","texto":"¿Tu nacimiento ya está registrado en México?","opciones":["Sí","No","No estoy seguro"]}
 ],
 "resultado":{
  "prepara":"Si tu nacimiento ya está registrado en México, el documento que necesitas puede ser una copia certificada del acta.",
  "confirma":"Si nunca fuiste registrado en México, el procedimiento es diferente. No debes solicitar simplemente una copia.",
  "fuente":FUENTES["documentacion"]
 }
}
]

# ---------------------------------------------------------
# OPCIONES DIRECTAS PARA LA PANTALLA
# ---------------------------------------------------------

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

def catalogo():
    return deepcopy(OPCIONES)

def obtener_caso(caso_id):
    for caso in CASOS:
        if caso["id"]==caso_id:
            return deepcopy(caso)
    return None

def puntuar(caso,texto):
    t=normalizar(texto)
    w=palabras(t)
    score=0
    for grupo in caso["grupos"]:
        encontrado=False
        for x in grupo:
            x=normalizar(x)
            if not x:
                continue
            if x in t:
                score+=2
                encontrado=True
                break
            if " " not in x and x in w:
                score+=1
                encontrado=True
                break
        if not encontrado:
            continue
    return score

def buscar_casos(texto,servicio):
    salida=[]
    for caso in CASOS:
        if caso["servicio"]!=servicio:
            continue
        s=puntuar(caso,texto)
        if s>=2:
            salida.append((s,caso))
    salida.sort(key=lambda x:x[0],reverse=True)
    return [x[1] for x in salida]

def identificar(servicio,texto):
    casos=buscar_casos(texto,servicio)
    if not casos:
        return None
    if len(casos)==1:
        return casos[0]
    a,b=casos[0],casos[1]
    if puntuar(a,texto)>=puntuar(b,texto)+2:
        return a
    return casos

def pregunta_actual(caso,respuestas):
    for q in caso.get("preguntas",[]):
        if q["id"] not in respuestas:
            return q
    return None

def respuesta_pregunta(caso,q):
    return {
        "estado":"pregunta",
        "caso":caso["id"],
        "titulo":caso["titulo"],
        "pregunta":q["texto"],
        "pregunta_id":q["id"],
        "opciones":q.get("opciones",[])
    }

def resultado(caso):
    r=caso["resultado"]
    return {
        "estado":"resuelto",
        "caso":caso["id"],
        "titulo":caso["titulo"],
        "prepara":r["prepara"],
        "confirma":r["confirma"],
        "fuente":r["fuente"]
    }

def iniciar(servicio):
    if servicio not in ("cita","documento"):
        return {"estado":"error","mensaje":"Servicio no disponible."}
    return {
        "estado":"necesita_descripcion",
        "pregunta":"¿Qué necesitas?",
        "opciones":[
            {"id":x["id"],"texto":x["texto"]}
            for x in OPCIONES
        ]
    }

def seleccionar(caso_id):
    caso=obtener_caso(caso_id)
    if not caso:
        return {"estado":"no_identificado","mensaje":"No encontramos esa opción."}
    q=caso["preguntas"][0] if caso.get("preguntas") else None
    if not q:
        return resultado(caso)
    return respuesta_pregunta(caso,q)

def continuar(caso_id,respuestas=None):
    respuestas=dict(respuestas or {})
    caso=obtener_caso(caso_id)

    if not caso:
        return {
            "estado":"no_identificado",
            "mensaje":"No encontramos ese trámite."
        }

    q=pregunta_actual(caso,respuestas)

    if q:
        return respuesta_pregunta(caso,q)

    return resultado(caso)

def interpretar(servicio,texto,respuestas=None):
    respuestas=dict(respuestas or {})
    texto=(texto or "").strip()

    # Si ya existe un caso, jamás volvemos a interpretar
    # el texto inicial del usuario.
    caso_id=respuestas.get("_caso")

    if caso_id:
        return continuar(caso_id,respuestas)

    if not texto:
        return iniciar(servicio)

    # Permite que el texto sea directamente el ID de una opción.
    directo=obtener_caso(texto)
    if directo and directo["servicio"]==servicio:
        respuestas["_caso"]=directo["id"]
        return continuar(directo["id"],respuestas)

    encontrados=identificar(servicio,texto)

    if not encontrados:
        return {
            "estado":"necesita_descripcion",
            "pregunta":"No quiero adivinar. Dime con tus propias palabras qué necesitas.",
            "opciones":[
                {"id":x["id"],"texto":x["texto"]}
                for x in OPCIONES
                if x["id"]!="no_se"
            ]
        }

    if isinstance(encontrados,list):
        return {
            "estado":"seleccionar",
            "pregunta":"¿Cuál de estas opciones se parece a lo que necesitas?",
            "opciones":[
                {"id":x["id"],"texto":x["titulo"]}
                for x in encontrados
            ]
        }

    respuestas["_caso"]=encontrados["id"]
    return continuar(encontrados["id"],respuestas)
