from io import BytesIO
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from consular_engine import iniciar,interpretar,continuar,catalogo,obtener_caso,resultado

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="4.0.0")
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
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","motor":"consular_engine","version":"4.0.0"}

@app.get("/api/casos")
def casos(servicio:str=""):
 return {"ok":True,"casos":catalogo(servicio or None)}

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

@app.post("/api/entender")
def entender(data:Inicio):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 if not data.texto.strip():
  return {"ok":False,"estado":"necesita_descripcion","pregunta":"Cuéntame con tus propias palabras qué necesitas resolver."}
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
  respuestas["_caso"]=data.caso
  r=continuar(data.caso,respuestas)
 elif data.texto.strip():
  r=interpretar(data.servicio,data.texto,respuestas)
 else:
  return {"ok":False,"mensaje":"Necesitamos tu respuesta para continuar."}
 respuestas=dict(r.get("respuestas") or respuestas)
 if data.caso:respuestas["_caso"]=data.caso
 r["ok"]=True
 r["servicio"]=data.servicio
 r["respuestas"]=respuestas
 return r

def esc(t):
 return str(t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def P(t,s):
 return Paragraph(esc(t),s)

def crear_pdf(caso_id,respuestas):
 caso=obtener_caso(caso_id)
 if not caso:return None
 d=resultado(caso,respuestas)
 buf=BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=letter,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("T",parent=styles["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=10)
 h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=12.5,leading=16,spaceBefore=10,spaceAfter=6)
 body=ParagraphStyle("B",parent=styles["BodyText"],fontSize=10,leading=14,spaceAfter=5)
 small=ParagraphStyle("S",parent=body,fontSize=8.2,leading=11)

 e=[]
 fecha=datetime.now().strftime("%d/%m/%Y %H:%M")
 nivel=d.get("nivel","")
 estado=d.get("estado_texto","")
 etiqueta={"verde":"PARECES LISTO","amarillo":"TE FALTA ALGO","rojo":"ATENCIÓN"}.get(nivel,"RESULTADO")

 e += [
  Paragraph("MEXICANO APOYA MEXICANO",titulo),
  Paragraph("HOJA DE RUTA / CHECKLIST DE REQUISITOS",h),
  P(f"Fecha de consulta: {fecha}",body),
  P(f"Trámite: {d.get('titulo',caso.get('titulo',''))}",body),
  P(f"ESTADO: {etiqueta}",h),
  P(estado,body)
 ]

 e.append(Paragraph("1. ¿QUÉ DEBES PREPARAR?",h))
 e.append(P(d.get("prepara"),body))

 c=d.get("checklist",{})
 e.append(Paragraph("2. LO QUE YA TIENES",h))
 if c.get("tiene"):
  for x in c["tiene"]:e.append(P("☑ "+x,body))
 else:e.append(P("No marcaste ningún documento como disponible.",body))

 e.append(Paragraph("3. LO QUE TE FALTA",h))
 if c.get("falta"):
  for x in c["falta"]:e.append(P("☐ "+x,body))
 else:e.append(P("No marcaste documentos como faltantes.",body))

 e.append(Paragraph("4. LO QUE NO ESTÁS SEGURO DE TENER",h))
 if c.get("revisar"):
  for x in c["revisar"]:e.append(P("□ "+x,body))
 else:e.append(P("No dejaste documentos pendientes de confirmar.",body))

 especiales=d.get("especiales") or []
 if especiales:
  e.append(Paragraph("5. ATENCIÓN A TU CASO",h))
  for x in especiales:e.append(P("⚠ "+x,body))

 e.append(Paragraph("6. DOCUMENTOS / REQUISITOS",h))
 docs=c.get("documentos") or []
 if docs:
  for x in docs:e.append(P("• "+x,body))
 else:e.append(P("Revisa los requisitos específicos indicados en tu resultado.",body))

 ruta=d.get("ruta") or {}
 e.append(Paragraph("7. ORIGINALES",h))
 e.append(P(ruta.get("llevar_original"),body))

 e.append(Paragraph("8. COPIAS",h))
 e.append(P(ruta.get("copias"),body))

 e.append(Paragraph("9. CITA",h))
 e.append(P(ruta.get("cita"),body))

 e.append(Paragraph("10. PAGO",h))
 e.append(P(d.get("pago"),body))

 if d.get("vigencia"):
  e.append(Paragraph("11. VIGENCIA",h))
  e.append(P(d["vigencia"],body))

 if d.get("entrega"):
  e.append(Paragraph("12. ENTREGA",h))
  e.append(P(d["entrega"],body))

 if d.get("revision"):
  e.append(Paragraph("13. ANTES DE FIRMAR / IMPRIMIR",h))
  e.append(P(d["revision"],body))

 e.append(Paragraph("14. INFORMACIÓN OFICIAL",h))
 e.append(P(d.get("fuente"),small))
 e.append(Spacer(1,10))
 e.append(P(d.get("confirma"),body))
 e.append(P(d.get("aviso"),small))
 e.append(P("Consulta oficial de citas: https://citas.sre.gob.mx",small))
 e.append(P("Consulta oficial de tarifas: https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",small))

 doc.build(e)
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
 return StreamingResponse(
  buf,
  media_type="application/pdf",
  headers={"Content-Disposition":'attachment; filename="Hoja_Ruta_Mexicano_Apoya_Mexicano.pdf"'}
 )
