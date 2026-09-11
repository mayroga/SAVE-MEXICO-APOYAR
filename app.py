from io import BytesIO
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from consular_engine import iniciar,interpretar,continuar,catalogo,obtener_caso,resultado

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="3.0.0")
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

class PDFData(BaseModel):
 caso:str
 respuestas:dict={}

@app.get("/")
def inicio():
 return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","motor":"consular_engine"}

@app.get("/api/casos")
def casos(servicio:str=""):
 return {"ok":True,"casos":catalogo(servicio or None)}

@app.get("/api/inicio/{servicio}")
def comenzar(servicio:str):
 if servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 r=iniciar(servicio);r["ok"]=True;r["servicio"]=servicio
 return r

@app.post("/api/iniciar")
def iniciar_caso(data:Inicio):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 r=interpretar(data.servicio,data.texto,{})
 r["ok"]=True;r["servicio"]=data.servicio
 return r

@app.post("/api/responder")
def responder(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 respuestas=dict(data.respuestas or {})
 if data.pregunta_id and data.texto.strip():
  respuestas[data.pregunta_id]=data.texto.strip()
 if data.caso:
  respuestas["_caso"]=data.caso
  r=continuar(data.caso,respuestas)
 elif data.texto.strip():
  r=interpretar(data.servicio,data.texto,respuestas)
 else:
  return {"ok":False,"mensaje":"Necesitamos tu respuesta para continuar."}
 respuestas=dict(r.get("respuestas") or respuestas)
 if data.caso:respuestas["_caso"]=data.caso
 r["ok"]=True;r["servicio"]=data.servicio;r["respuestas"]=respuestas
 return r

@app.post("/api/entender")
def entender(data:Inicio):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 if not data.texto.strip():
  return {"ok":False,"estado":"necesita_descripcion","pregunta":"Cuéntame con tus propias palabras qué necesitas resolver."}
 r=interpretar(data.servicio,data.texto,{})
 r["ok"]=True;r["servicio"]=data.servicio
 return r

def pdf_parrafo(texto,style):
 return Paragraph(str(texto or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"),style)

def crear_pdf(caso_id,respuestas):
 caso=obtener_caso(caso_id)
 if not caso:return None
 datos=resultado(caso,respuestas)
 buf=BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=letter,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("Titulo",parent=styles["Title"],fontSize=19,leading=23,alignment=TA_CENTER,spaceAfter=10)
 subtitulo=ParagraphStyle("Sub",parent=styles["Heading2"],fontSize=13,leading=17,spaceBefore=10,spaceAfter=6)
 texto=ParagraphStyle("Texto",parent=styles["BodyText"],fontSize=10.5,leading=15,spaceAfter=5)
 pequeno=ParagraphStyle("Pequeno",parent=texto,fontSize=8.5,leading=12)
 elementos=[]
 fecha=datetime.now().strftime("%d/%m/%Y %H:%M")
 elementos += [
  Paragraph("MEXICANO APOYA MEXICANO",titulo),
  Paragraph("HOJA DE RUTA / CHECKLIST DE REQUISITOS FÍSICOS",subtitulo),
  Paragraph(f"<b>Fecha de consulta:</b> {fecha}",texto),
  Paragraph(f"<b>Trámite:</b> {caso['titulo']}",texto),
  Spacer(1,8)
 ]

 elementos.append(Paragraph("1. ¿QUÉ DEBES PREPARAR?",subtitulo))
 elementos.append(pdf_parrafo(datos["prepara"],texto))

 c=datos.get("checklist",{})
 tiene=c.get("tiene",[])
 falta=c.get("falta",[])
 revisar=c.get("revisar",[])

 elementos.append(Paragraph("2. LO QUE YA TIENES",subtitulo))
 if tiene:
  for x in tiene:elementos.append(Paragraph("☑ "+x,texto))
 else:elementos.append(Paragraph("No marcaste ningún documento como disponible.",texto))

 elementos.append(Paragraph("3. LO QUE TE FALTA",subtitulo))
 if falta:
  for x in falta:elementos.append(Paragraph("☐ "+x,texto))
 else:elementos.append(Paragraph("No marcaste documentos como faltantes.",texto))

 elementos.append(Paragraph("4. LO QUE NO ESTÁS SEGURO DE TENER",subtitulo))
 if revisar:
  for x in revisar:elementos.append(Paragraph("□ "+x,texto))
 else:elementos.append(Paragraph("No dejaste documentos pendientes de confirmar.",texto))

 elementos.append(Paragraph("5. DOCUMENTOS PARA PREPARAR",subtitulo))
 for x in c.get("documentos",[]):
  elementos.append(Paragraph("• "+x,texto))

 elementos.append(Paragraph("6. ORIGINAL Y COPIA",subtitulo))
 elementos.append(Paragraph(
  "<b>ORIGINAL:</b> Lleva los documentos originales que correspondan a tu trámite y a tu situación.",
  texto))
 elementos.append(Paragraph(
  "<b>COPIA:</b> Lleva las copias que indique el consulado para ese trámite. No asumas que una copia sustituye al original.",
  texto))

 elementos.append(Paragraph("7. CITA",subtitulo))
 elementos.append(Paragraph(
  "Revisa las instrucciones de tu consulado sobre la cita y conserva tu confirmación. "
  "Los requisitos pueden variar según el consulado y el trámite.",texto))

 elementos.append(Paragraph("8. PAGO",subtitulo))
 elementos.append(pdf_parrafo(datos.get("pago"),texto))

 elementos.append(Paragraph("9. IMPORTANTE",subtitulo))
 elementos.append(pdf_parrafo(datos.get("confirma"),texto))
 elementos.append(pdf_parrafo(datos.get("aviso"),pequeno))

 elementos.append(Paragraph("10. INFORMACIÓN OFICIAL",subtitulo))
 elementos.append(Paragraph(datos.get("fuente",""),pequeno))
 elementos.append(Spacer(1,12))
 elementos.append(Paragraph(
  "Esta hoja es una guía de preparación. No es un documento emitido por el Gobierno de México "
  "ni sustituye la confirmación del consulado.",pequeno))

 doc.build(elementos)
 buf.seek(0)
 return buf

@app.post("/api/pdf")
def generar_pdf(data:PDFData):
 caso=obtener_caso(data.caso)
 if not caso:
  return {"ok":False,"mensaje":"No encontramos el trámite seleccionado."}
 buf=crear_pdf(data.caso,dict(data.respuestas or {}))
 if not buf:
  return {"ok":False,"mensaje":"No fue posible generar el PDF."}
 nombre="Hoja_Ruta_Mexicano_Apoya_Mexicano.pdf"
 return StreamingResponse(
  buf,
  media_type="application/pdf",
  headers={"Content-Disposition":f'attachment; filename="{nombre}"'}
 )
