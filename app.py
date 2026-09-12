import os,io,re
from typing import Any,Dict,Optional
from fastapi import FastAPI,HTTPException,UploadFile,File
from fastapi.responses import FileResponse,StreamingResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from consular_engine import (
 APP,VERSION,iniciar,seleccionar_caso,continuar,interpretar,resultado,
 catalogo,obtener_fuentes,obtener_contacto,obtener_tarifas,obtener_manual,
 tramite_oficial,caso_info,procesar
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
 respuestas:Dict[str,Any]={}

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

def limpiar(x):
 x="" if x is None else str(x)
 x=re.sub(r"[ \t]+"," ",x)
 x=re.sub(r"\n{3,}","\n\n",x)
 return x.strip()

def lista_pdf(x):
 if x is None:return []
 if isinstance(x,str):
  return [limpiar(x)] if limpiar(x) else []
 if isinstance(x,dict):
  return [f"{k}: {v}" for k,v in x.items() if limpiar(v)]
 if isinstance(x,(list,tuple)):
  return [limpiar(v) for v in x if limpiar(v)]
 return [limpiar(x)]

def texto_pdf(c,txt,y,size=10,bold=False,leading=14):
 txt=limpiar(txt)
 if not txt:return y
 font="Helvetica-Bold" if bold else "Helvetica"
 c.setFont(font,size)
 line=""
 for word in txt.split():
  test=(line+" "+word).strip()
  if c.stringWidth(test,font,size)<=500:
   line=test
  else:
   if y<65:c.showPage();y=750
   c.setFont(font,size);c.drawString(55,y,line);y-=leading
   line=word
 if line:
  if y<65:c.showPage();y=750
  c.setFont(font,size);c.drawString(55,y,line);y-=leading
 return y

def seccion(c,t,y):
 if y<80:c.showPage();y=750
 c.setFillColorRGB(.07,.38,.63)
 c.setFont("Helvetica-Bold",12)
 c.drawString(55,y,t)
 c.setFillColorRGB(0,0,0)
 return y-18

def campo_pdf(c,nombre,valor,y):
 if y<65:c.showPage();y=750
 c.setFont("Helvetica-Bold",9)
 c.drawString(55,y,nombre)
 c.acroform.textfield(
  name="campo_"+re.sub(r"\W+","_",nombre.lower()),
  value=limpiar(valor),
  x=175,y=y-4,width=340,height=17,
  borderWidth=1,borderStyle="underlined",
  forceBorder=True,fontName="Helvetica",fontSize=9
 )
 return y-25

def construir_pdf(r,editable=True):
 out=io.BytesIO()
 c=canvas.Canvas(out,pagesize=letter)
 c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
 y=750

 c.setFont("Helvetica-Bold",18)
 c.drawString(55,y,"MEXICANO APOYA MEXICANO")
 y-=24
 c.setFont("Helvetica-Bold",14)
 c.drawString(55,y,"HOJA DE RUTA / CHECKLIST")
 y-=22
 y=texto_pdf(c,"DOCUMENTO PREVIO — REVISA Y CORRIGE TUS DATOS ANTES DE CONFIRMAR.",y,9,True)-8

 p=r.get("perfil",{}) or {}
 y=seccion(c,"1. TUS DATOS",y)

 datos=[
  ("Nombre y apellidos",p.get("nombre_completo","")),
  ("Fecha de nacimiento",p.get("fecha_nacimiento","")),
  ("Edad",p.get("edad","")),
  ("Dirección",p.get("direccion","")),
  ("Estado",p.get("estado","")),
  ("Código postal",p.get("codigo_postal","")),
  ("Teléfono",p.get("telefono","")),
  ("Trabajo / ocupación",p.get("trabajo") or p.get("ocupacion",""))
 ]

 if editable:
  for n,v in datos:y=campo_pdf(c,n,v,y)
 else:
  for n,v in datos:
   if v:y=texto_pdf(c,f"{n}: {v}",y)

 y-=6
 y=seccion(c,"2. TRÁMITE",y)
 y=texto_pdf(c,r.get("nombre_tramite",""),y,11,True)

 bloques=[
  ("3. QUIÉN DEBE PRESENTARSE",r.get("personas")),
  ("4. REQUISITOS",r.get("requisitos")),
  ("5. DOCUMENTOS ORIGINALES",r.get("originales")),
  ("6. COPIAS",r.get("copias")),
  ("7. TE FALTA",r.get("faltantes")),
  ("8. INFORMACIÓN ESPECIAL",r.get("especial")),
  ("9. QUÉ DEBES HACER",r.get("acciones")),
  ("10. PAGO",r.get("pago")),
  ("11. CITA",r.get("cita")),
  ("12. VIGENCIA",r.get("vigencia")),
  ("13. ENTREGA",r.get("entrega"))
 ]

 for titulo,val in bloques:
  vals=lista_pdf(val)
  if not vals:continue
  y-=5;y=seccion(c,titulo,y)
  for v in vals:y=texto_pdf(c,"• "+v,y)

 y-=5
 y=seccion(c,"14. INFORMACIÓN OFICIAL",y)
 y=texto_pdf(c,r.get("fuente",""),y,8)

 y-=5
 y=texto_pdf(
  c,
  "IMPORTANTE: Este documento es una herramienta de preparación. "
  "No es un documento oficial del Gobierno de México. "
  "Confirma siempre los requisitos vigentes con el Consulado correspondiente.",
  y,7
 )

 if y<65:c.showPage();y=750
 c.setFont("Helvetica",7)
 c.setFillColorRGB(.35,.35,.35)
 c.drawString(55,38,"MEXICANO APOYA MEXICANO — DOCUMENTO DE PREPARACIÓN")
 c.save()
 out.seek(0)
 return out

def extraer_pdf_bytes(data):
 try:
  from pypdf import PdfReader
  reader=PdfReader(io.BytesIO(data))
  return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
 except Exception:
  return ""

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
 try:return iniciar(x.texto,x.perfil)
 except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/start")
def api_start(x:Inicio):
 return api_iniciar(x)

@app.post("/api/interpretar")
def api_interpretar(x:Interpretacion):
 try:return interpretar(x.caso,x.texto,x.respuestas,x.perfil)
 except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/seleccionar-caso")
def api_seleccionar(x:Seleccion):
 try:return seleccionar_caso(x.caso,x.perfil,x.respuestas)
 except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/seleccionar_caso")
def api_seleccionar_2(x:Seleccion):
 return api_seleccionar(x)

@app.post("/api/continuar")
def api_continuar(x:Continuacion):
 try:
  res=dict(x.respuestas or {})
  perfil=dict(x.perfil or {})
  res["texto"]=x.texto or x.respuesta or ""
  return continuar(x.caso,res,perfil,x.pregunta_id,x.respuesta or x.texto)
 except Exception as e:
  raise HTTPException(400,str(e))

@app.post("/api/resultado")
def api_resultado(x:ResultadoRequest):
 try:return resultado(x.caso,x.respuestas,x.perfil)
 except Exception as e:raise HTTPException(400,str(e))

@app.get("/api/tramite/{caso}")
def api_tramite(caso:str):
 c=caso_info(caso)
 if not c:raise HTTPException(404,"Trámite no disponible.")
 return tramite_oficial(caso)

@app.get("/api/caso/{caso}")
def api_caso(caso:str):
 c=caso_info(caso)
 if not c:raise HTTPException(404,"Trámite no disponible.")
 return c

@app.post("/api/procesar")
def api_procesar(data:Dict[str,Any]):
 try:return procesar(data.get("caso",""),data.get("respuestas",{}),data.get("perfil",{}))
 except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/documento")
async def api_documento(file:UploadFile=File(...)):
 if not file.filename.lower().endswith(".pdf"):
  raise HTTPException(400,"Solo se permite un archivo PDF.")
 data=await file.read()
 if len(data)>15*1024*1024:
  raise HTTPException(400,"El PDF no puede superar 15 MB.")
 texto=extraer_pdf_bytes(data)
 return {
  "ok":True,
  "nombre":file.filename,
  "texto":texto,
  "tiene_texto":bool(texto),
  "mensaje":"PDF leído. Revisa la información antes de utilizarla."
 }

@app.post("/api/pdf")
def api_pdf(x:ResultadoRequest):
 try:
  r=resultado(x.caso,x.respuestas,x.perfil)
  pdf=construir_pdf(r,True)
  return StreamingResponse(
   pdf,
   media_type="application/pdf",
   headers={"Content-Disposition":'attachment; filename="Hoja_de_Ruta_EDITABLE.pdf"'}
  )
 except Exception as e:
  raise HTTPException(400,f"No se pudo generar el PDF: {e}")

@app.post("/api/pdf-preview")
def api_pdf_preview(x:ResultadoRequest):
 try:
  r=resultado(x.caso,x.respuestas,x.perfil)
  pdf=construir_pdf(r,True)
  return StreamingResponse(
   pdf,
   media_type="application/pdf",
   headers={"Content-Disposition":'inline; filename="Hoja_de_Ruta_PREVIA.pdf"'}
  )
 except Exception as e:
  raise HTTPException(400,f"No se pudo preparar la vista previa: {e}")

@app.post("/api/generar-pdf")
def api_generar_pdf(x:ResultadoRequest):
 return api_pdf(x)

if __name__=="__main__":
 import uvicorn
 uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")),reload=False)
