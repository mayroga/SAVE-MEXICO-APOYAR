import os,re
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="1.0.0")
app.mount("/static",StaticFiles(directory="static"),name="static")

class Texto(BaseModel):
    texto:str=""

SERVICIOS={
 "pasaporte":{
  "nombre":"PASAPORTE",
  "frases":["pasaporte","pasaportes","renovar pasaporte","sacar pasaporte","pasaporte mexicano"]
 },
 "matricula":{
  "nombre":"MATRÍCULA CONSULAR",
  "frases":["matricula","matrícula","matricula consular","matrícula consular"]
 },
 "ine":{
  "nombre":"INE",
  "frases":["ine","credencial para votar","credencial de elector","votar"]
 },
 "registro":{
  "nombre":"REGISTRO DE NACIMIENTO",
  "frases":["registrar a mi hijo","registrar hijo","registro de nacimiento","acta de nacimiento","registrar nacimiento","nacimiento"]
 },
 "poder":{
  "nombre":"PODER O AUTORIZACIÓN",
  "frases":["poder","poder notarial","autorizacion","autorización","dar poder","mandar poder"]
 }
}

def detectar(texto):
    t=re.sub(r"\s+"," ",texto.lower().strip())
    for clave,data in SERVICIOS.items():
        for frase in data["frases"]:
            if frase in t:
                return clave,data["nombre"]
    return None,None

@app.get("/")
def inicio():
    return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
    return {
        "ok":True,
        "app":"MEXICANO APOYA MEXICANO",
        "mensaje":"Servicio disponible"
    }

@app.get("/api/servicios")
def servicios():
    return {
        "ok":True,
        "servicios":[
            {"id":"pasaporte","nombre":"PASAPORTE"},
            {"id":"matricula","nombre":"MATRÍCULA CONSULAR"},
            {"id":"ine","nombre":"INE"},
            {"id":"registro","nombre":"REGISTRO DE NACIMIENTO"},
            {"id":"poder","nombre":"PODER O AUTORIZACIÓN"}
        ]
    }

@app.post("/api/entender")
def entender(data:Texto):
    clave,nombre=detectar(data.texto)

    if not clave:
        return {
            "ok":True,
            "encontrado":False,
            "mensaje":"No entendí todavía qué necesitas.",
            "siguiente":"Dime con palabras sencillas qué quieres hacer."
        }

    return {
        "ok":True,
        "encontrado":True,
        "servicio":clave,
        "nombre":nombre,
        "mensaje":f"Entendí que necesitas ayuda con {nombre}.",
        "siguiente":"Ahora te haré las preguntas necesarias para preparar tu caso."
    }

@app.get("/api/servicio/{servicio}")
def servicio(servicio:str):
    if servicio not in SERVICIOS:
        return {
            "ok":False,
            "mensaje":"No encontramos ese servicio."
        }

    nombre=SERVICIOS[servicio]["nombre"]

    return {
        "ok":True,
        "servicio":servicio,
        "nombre":nombre,
        "mensaje":f"Vamos a preparar tu caso de {nombre}.",
        "proceso":[
            "Entender lo que necesitas",
            "Hacer solamente las preguntas necesarias",
            "Organizar la información",
            "Decirte claramente qué debes preparar",
            "Indicarte qué debes confirmar con el Consulado"
        ]
    }
