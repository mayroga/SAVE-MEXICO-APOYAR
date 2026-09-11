from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="1.0.0")
app.mount("/static",StaticFiles(directory="static"),name="static")

class Respuesta(BaseModel):
    servicio:str
    paso:int=0
    respuesta:str=""

CITAS=[
    {"pregunta":"¿Para qué es tu cita en el Consulado?","opciones":["Pasaporte","Matrícula Consular","INE","Registro o acta","Poder o documento","Otra cosa"]},
    {"pregunta":"¿Tienes contigo la confirmación de tu cita?","opciones":["Sí","No","No sé"]},
    {"pregunta":"¿Quieres que preparemos una lista sencilla de lo que debes revisar antes de ir?","opciones":["Sí","No"]}
]

DOCUMENTOS=[
    {"pregunta":"Cuéntame con palabras sencillas qué necesitas resolver.","opciones":[]},
    {"pregunta":"¿Es algo relacionado con un documento mexicano?","opciones":["Sí","No","No sé"]},
    {"pregunta":"¿Quieres que te indiquemos qué información debes confirmar para saber qué documento o servicio corresponde a tu caso?","opciones":["Sí","No"]}
]

def flujo(servicio):
    return CITAS if servicio=="cita" else DOCUMENTOS

@app.get("/")
def inicio():
    return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
    return {"ok":True,"app":"MEXICANO APOYA MEXICANO"}

@app.get("/api/inicio/{servicio}")
def iniciar(servicio:str):
    if servicio not in ("cita","documento"):
        return {"ok":False,"mensaje":"Servicio no disponible."}
    f=flujo(servicio)
    return {
        "ok":True,
        "servicio":servicio,
        "paso":0,
        "total":len(f),
        "pregunta":f[0]["pregunta"],
        "opciones":f[0]["opciones"]
    }

@app.post("/api/responder")
def responder(data:Respuesta):
    if data.servicio not in ("cita","documento"):
        return {"ok":False,"mensaje":"Servicio no disponible."}

    f=flujo(data.servicio)
    paso=max(0,min(data.paso,len(f)-1))
    respuesta=data.respuesta.strip()

    if not respuesta:
        return {"ok":False,"mensaje":"Necesitamos tu respuesta para continuar."}

    siguiente=paso+1

    if siguiente<len(f):
        return {
            "ok":True,
            "terminado":False,
            "servicio":data.servicio,
            "paso":siguiente,
            "total":len(f),
            "pregunta":f[siguiente]["pregunta"],
            "opciones":f[siguiente]["opciones"]
        }

    if data.servicio=="cita":
        return {
            "ok":True,
            "terminado":True,
            "titulo":"PREPARA TU CITA",
            "resultado":[
                "Ten a mano la confirmación de tu cita.",
                "Revisa exactamente para qué servicio tienes la cita.",
                "Antes de salir, confirma en la información oficial del Consulado los documentos, fotografías, pagos y demás requisitos que correspondan a tu trámite.",
                "Si algo no está claro, confírmalo directamente con el Consulado antes de acudir."
            ]
        }

    return {
        "ok":True,
        "terminado":True,
        "titulo":"PREPARA TU CASO",
        "resultado":[
            "Ya tenemos una idea de lo que necesitas resolver.",
            "No queremos adivinar qué documento corresponde a tu caso.",
            "Vamos a identificar la información que debes confirmar para preparar el trámite correcto.",
            "La decisión final sobre el documento o servicio corresponde al Consulado."
        ]
    }

