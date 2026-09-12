import os,io,re
from typing import Any,Dict,Optional
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from consular_engine import (
    APP,VERSION,iniciar,seleccionar_caso,continuar,interpretar,
    resultado,catalogo,obtener_fuentes,obtener_contacto,obtener_tarifas,
    obtener_manual,tramite_oficial,caso_info,procesar
)

app=FastAPI(title=APP,version=VERSION)
app.mount("/static",StaticFiles(directory="static"),name="static")

class Inicio(BaseModel):
    perfil:Dict[str,Any]={}
    texto:str=""
class Interpretacion(BaseModel):
    texto:str=""
    perfil:Dict[str,Any]={}
    caso:Optional[str]=None
class Continuacion(BaseModel):
    caso:str
    pregunta_id:str=""
    respuesta:Any=""
    texto:str=""
    respuestas:Dict[str,Any]={}
    perfil:Dict[str,Any]={}
class Seleccion(BaseModel):
    caso:str
    perfil:Dict[str,Any]={}
    respuestas:Dict[str,Any]={}
class ResultadoRequest(BaseModel):
    caso:str
    respuestas:Dict[str,Any]={}
    perfil:Dict[str,Any]={}

def limpiar(x:Any)->str:
    x="" if x is None else str(x)
    x=re.sub(r"[ \t]+"," ",x)
    x=re.sub(r"\n{3,}","\n\n",x)
    return x.strip()

def lista_pdf(items:Any)->list:
    if not items:return []
    if isinstance(items,str):items=[items]
    if not isinstance(items,(list,tuple)):items=[items]
    return [limpiar(x) for x in items if limpiar(x)]

def datos_pdf(r:Dict[str,Any])->Dict[str,Any]:
    return {
        "datos":r.get("datos_personales",r.get("datos",{})),
        "tramite":r.get("tramite",r.get("servicio","")),
        "personas":r.get("personas",r.get("personas_que_deben_presentarse",[])),
        "requisitos":r.get("requisitos",r.get("documentos",[])),
        "originales":r.get("originales",[]),
        "copias":r.get("copias",[]),
        "faltantes":r.get("faltantes",r.get("missing",[])),
        "confirmar":r.get("confirmar",r.get("por_confirmar",[])),
        "pago":r.get("pago",r.get("tarifa","")),
        "cita":r.get("cita",[]),
        "vigencia":r.get("vigencia",""),
        "entrega":r.get("entrega",""),
        "especial":r.get("especial",r.get("situaciones_especiales",[])),
        "acciones":r.get("acciones",[]),
        "fuente":r.get("fuente_oficial",r.get("fuente","")),
        "contacto":r.get("contacto",{})
    }

def texto_pdf(c,txt,y,size=10,bold=False,leading=14):
    txt=limpiar(txt)
    if not txt:return y
    c.setFont("Helvetica-Bold" if bold else "Helvetica",size)
    maxw=500
    palabras=txt.split()
    linea=""
    for p in palabras:
        t=(linea+" "+p).strip()
        if c.stringWidth(t,"Helvetica-Bold" if bold else "Helvetica",size)<=maxw:
            linea=t
        else:
            if y<55:
                c.showPage();y=750
                c.setFont("Helvetica-Bold" if bold else "Helvetica",size)
            c.drawString(55,y,linea);y-=leading
            linea=p
    if linea:
        if y<55:c.showPage();y=750
        c.drawString(55,y,linea);y-=leading
    return y

def seccion(c,titulo,y):
    if y<75:c.showPage();y=750
    c.setFillColorRGB(.07,.38,.63)
    c.setFont("Helvetica-Bold",12)
    c.drawString(55,y,titulo)
    c.setFillColorRGB(0,0,0)
    return y-18

def construir_pdf(r:Dict[str,Any])->io.BytesIO:
    d=datos_pdf(r)
    out=io.BytesIO()
    c=canvas.Canvas(out,pagesize=letter)
    y=750
    c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
    c.setFont("Helvetica-Bold",18)
    c.drawString(55,y,"MEXICANO APOYA MEXICANO")
    y-=22
    c.setFont("Helvetica-Bold",14)
    y=texto_pdf(c,"HOJA DE RUTA / CHECKLIST",y,14,True,18)-8
    c.setFont("Helvetica",9)
    y=texto_pdf(c,"Preparación informativa para tu trámite. Confirma siempre los requisitos con el Consulado de México que corresponde a tu residencia.",y,9)-10

    y=seccion(c,"1. DATOS PERSONALES",y)
    datos=d["datos"]
    if isinstance(datos,dict):
        nombres={
            "nombre_completo":"Nombre",
            "fecha_nacimiento":"Fecha de nacimiento",
            "edad":"Edad",
            "direccion":"Dirección",
            "estado":"Estado",
            "codigo_postal":"Código postal",
            "telefono":"Teléfono",
            "trabajo":"Trabajo / ocupación"
        }
        for k,n in nombres.items():
            v=datos.get(k)
            if v not in (None,"","-"):
                y=texto_pdf(c,f"{n}: {v}",y)
    else:y=texto_pdf(c,datos,y)

    y-=5
    y=seccion(c,"2. TU TRÁMITE",y)
    y=texto_pdf(c,d["tramite"],y,11,True)

    bloques=[
        ("3. PERSONAS QUE DEBEN PRESENTARSE",d["personas"]),
        ("4. REQUISITOS OBLIGATORIOS",d["requisitos"]),
        ("5. DOCUMENTOS ORIGINALES",d["originales"]),
        ("6. COPIAS",d["copias"]),
        ("7. LO QUE TE FALTA",d["faltantes"]),
        ("8. LO QUE DEBES CONFIRMAR",d["confirmar"]),
    ]
    for titulo,items in bloques:
        vals=lista_pdf(items)
        if not vals:continue
        y-=5;y=seccion(c,titulo,y)
        for v in vals:y=texto_pdf(c,"• "+v,y)

    for titulo,val in [
        ("9. PAGO",d["pago"]),
        ("10. CITA",d["cita"]),
        ("11. VIGENCIA",d["vigencia"]),
        ("12. ENTREGA",d["entrega"])
    ]:
        vals=lista_pdf(val)
        if not vals:continue
        y-=5;y=seccion(c,titulo,y)
        for v in vals:y=texto_pdf(c,"• "+v,y)

    vals=lista_pdf(d["especial"])
    if vals:
        y-=5;y=seccion(c,"13. INFORMACIÓN ESPECIAL",y)
        for v in vals:y=texto_pdf(c,"• "+v,y)

    vals=lista_pdf(d["acciones"])
    if vals:
        y-=5;y=seccion(c,"14. QUÉ DEBES HACER",y)
        for i,v in enumerate(vals,1):y=texto_pdf(c,f"{i}. {v}",y)

    y-=5;y=seccion(c,"15. INFORMACIÓN OFICIAL",y)
    y=texto_pdf(c,d["fuente"],y)
    if isinstance(d["contacto"],dict):
        for k,v in d["contacto"].items():
            if v:y=texto_pdf(c,f"{k}: {v}",y)

    if y<55:c.showPage();y=750
    c.setFont("Helvetica",7)
    c.setFillColorRGB(.35,.35,.35)
    c.drawString(55,38,"MEXICANO APOYA MEXICANO no es el Gobierno de México ni sustituye la información oficial.")
    c.save()
    out.seek(0)
    return out

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
    return {"app":APP,"version":VERSION,"ok":True}

@app.get("/health")
def health():
    return {"status":"ok","app":APP,"version":VERSION}

@app.get("/api/catalogo")
def api_catalogo():
    return catalogo()

@app.get("/api/fuentes")
def api_fuentes():
    return obtener_fuentes()

@app.get("/api/contacto")
def api_contacto():
    return obtener_contacto()

@app.get("/api/tarifas")
def api_tarifas():
    return obtener_tarifas()

@app.get("/api/manual")
def api_manual():
    return obtener_manual()

@app.post("/api/iniciar")
def api_iniciar(x:Inicio):
    return iniciar(x.perfil,x.texto)

@app.post("/api/start")
def api_start(x:Inicio):
    return iniciar(x.perfil,x.texto)

@app.post("/api/interpretar")
def api_interpretar(x:Interpretacion):
    return interpretar(x.texto,x.perfil,x.caso)

@app.post("/api/seleccionar-caso")
def api_seleccionar(x:Seleccion):
    try:
        return seleccionar_caso(x.caso,x.perfil,x.respuestas)
    except Exception as e:
        raise HTTPException(400,str(e))

@app.post("/api/seleccionar_caso")
def api_seleccionar_2(x:Seleccion):
    return api_seleccionar(x)

@app.post("/api/continuar")
def api_continuar(x:Continuacion):
    try:
        r=dict(x.respuestas or {})
        if x.pregunta_id:r[x.pregunta_id]=x.respuesta
        perfil=dict(x.perfil or {})
        if x.texto and not x.respuesta: r[x.pregunta_id]=x.texto
        return continuar(x.caso,x.pregunta_id,x.respuesta,r,perfil,x.texto)
    except TypeError:
        try:
            return continuar(x.caso,x.pregunta_id,x.respuesta,r,perfil)
        except Exception as e:
            raise HTTPException(400,str(e))
    except Exception as e:
        raise HTTPException(400,str(e))

@app.post("/api/resultado")
def api_resultado(x:ResultadoRequest):
    try:return resultado(x.caso,x.respuestas,x.perfil)
    except Exception as e:raise HTTPException(400,str(e))

@app.get("/api/tramite/{caso}")
def api_tramite(caso:str):
    try:return tramite_oficial(caso)
    except Exception as e:raise HTTPException(404,str(e))

@app.get("/api/caso/{caso}")
def api_caso(caso:str):
    try:return caso_info(caso)
    except Exception as e:raise HTTPException(404,str(e))

@app.post("/api/procesar")
def api_procesar(data:Dict[str,Any]):
    try:return procesar(data)
    except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/pdf")
def api_pdf(data:ResultadoRequest):
    try:
        r=resultado(data.caso,data.respuestas,data.perfil)
        pdf=construir_pdf(r)
        nombre="hoja_de_ruta.pdf"
        return StreamingResponse(pdf,media_type="application/pdf",headers={
            "Content-Disposition":f'attachment; filename="{nombre}"'
        })
    except Exception as e:
        raise HTTPException(400,f"No se pudo generar el PDF: {e}")

@app.post("/api/generar-pdf")
def api_pdf_2(data:ResultadoRequest):
    return api_pdf(data)

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")),reload=False)
