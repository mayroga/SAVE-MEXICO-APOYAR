from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from consular_engine import iniciar, interpretar, continuar, catalogo

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="2.0.0")
app.mount("/static",StaticFiles(directory="static"),name="static")

class Inicio(BaseModel):
    servicio:str
    texto:str=""

class Respuesta(BaseModel):
    servicio:str
    caso:str=""
    texto:str=""
    respuestas:dict={}
    pregunta_id:str=""

@app.get("/")
def inicio():
    return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
    return {"ok":True,"app":"MEXICANO APOYA MEXICANO","motor":"consular_engine"}

@app.get("/api/casos")
def casos():
    return {"ok":True,"casos":catalogo()}

@app.get("/api/inicio/{servicio}")
def comenzar(servicio:str):
    if servicio not in ("cita","documento"):
        return {"ok":False,"mensaje":"Servicio no disponible."}
    r=iniciar(servicio)
    r["ok"]=True
    r["servicio"]=servicio
    return r

@app.post("/api/iniciar")
def iniciar_caso(data:Inicio):
    if data.servicio not in ("cita","documento"):
        return {"ok":False,"mensaje":"Servicio no disponible."}
    r=interpretar(data.servicio,data.texto,{})
    r["ok"]=True
    r["servicio"]=data.servicio
    return r

@app.post("/api/responder")
def responder(data:Respuesta):
    if data.servicio not in ("cita","documento"):
        return {"ok":False,"mensaje":"Servicio no disponible."}

    respuestas=dict(data.respuestas or {})

    if data.pregunta_id and data.texto.strip():
        respuestas[data.pregunta_id]=data.texto.strip()

    if data.caso:
        r=continuar(data.caso,respuestas)
    elif data.texto.strip():
        r=interpretar(data.servicio,data.texto,respuestas)
    else:
        return {
            "ok":False,
            "mensaje":"Necesitamos tu respuesta para continuar."
        }

    r["ok"]=True
    r["servicio"]=data.servicio
    r["respuestas"]=respuestas
    return r

@app.post("/api/entender")
def entender(data:Inicio):
    if data.servicio not in ("cita","documento"):
        return {"ok":False,"mensaje":"Servicio no disponible."}

    if not data.texto.strip():
        return {
            "ok":False,
            "estado":"necesita_descripcion",
            "pregunta":"Cuéntame con tus propias palabras qué necesitas resolver."
        }

    r=interpretar(data.servicio,data.texto,{})
    r["ok"]=True
    r["servicio"]=data.servicio
    return r
