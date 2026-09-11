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
from consular_engine import iniciar,interpretar,continuar,catalogo,obtener_caso,resultado

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="5.0.0")
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
def inicio():return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","motor":"consular_engine","version":"5.0.0"}

@app.get("/api/casos")
def casos(servicio:str=""):
 return {"ok":True,"casos":catalogo(servicio or None)}

@app.get("/api/inicio/{servicio}")
def comenzar(servicio:str):
 if servicio not in ("cita","documento"):return {"ok":False,"mensaje":"Servicio no disponible."}
 r=iniciar(servicio);r["ok"]=True;r["servicio"]=servicio
 return r

@app.post("/api/iniciar")
def iniciar_caso(data:Inicio):
 if data.servicio not in ("cita","documento"):return {"ok":False,"mensaje":"Servicio no disponible."}
 r=interpretar(data.servicio,data.texto,{})
 r["ok"]=True;r["servicio"]=data.servicio
 return r

@app.post("/api/entender")
def entender(data:Inicio):
 if data.servicio not in ("cita","documento"):return {"ok":False,"mensaje":"Servicio no disponible."}
 if not data.texto.strip():return {"ok":False,"estado":"necesita_descripcion","pregunta":"Cuéntame con tus propias palabras qué necesitas resolver."}
 r=interpretar(data.servicio,data.texto,{})
 r["ok"]=True;r["servicio"]=data.servicio
 return r

@app.post("/api/responder")
def responder(data:Respuesta):
 if data.servicio not in ("cita","documento"):return {"ok":False,"mensaje":"Servicio no disponible."}
 respuestas=dict(data.respuestas or {})
 if data.pregunta_id and data.texto.strip():respuestas[data.pregunta_id]=data.texto.strip()
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

def esc(t):
 return str(t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br/>")

def P(t,s):
 return Paragraph(esc(t),s)

def agregar_lista(st,titulo,items,simbolo,body):
 st.append(Paragraph(titulo,body["h"]))
 if items:
  for x in items:st.append(P(simbolo+" "+x,body["b"]))
 else:st.append(P("No se registraron elementos en esta categoría.",body["b"]))
 st.append(Spacer(1,3))

def crear_pdf(caso_id,respuestas):
 caso=obtener_caso(caso_id)
 if not caso:return None
 d=resultado(caso,respuestas)
 perfil=d.get("perfil") or {}
 c=d.get("checklist") or {}
 especiales=d.get("especiales") or []
 ruta=d.get("ruta") or {}
 buf=BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=letter,rightMargin=40,leftMargin=40,topMargin=38,bottomMargin=38)
 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("T",parent=styles["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=5)
 subt=ParagraphStyle("ST",parent=styles["BodyText"],fontSize=10,leading=13,alignment=TA_CENTER,spaceAfter=12)
 h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=12.5,leading=15,spaceBefore=9,spaceAfter=5)
 b=ParagraphStyle("B",parent=styles["BodyText"],fontSize=9.7,leading=13.5,spaceAfter=4)
 small=ParagraphStyle("S",parent=b,fontSize=7.5,leading=10)
 estado=ParagraphStyle("E",parent=b,fontSize=11,leading=15,spaceAfter=7)
 st={"h":h,"b":b}
 e=[]
 fecha=datetime.now().strftime("%d/%m/%Y %H:%M")

 e.append(Paragraph("MEXICANO APOYA MEXICANO",titulo))
 e.append(Paragraph("HOJA DE RUTA PERSONAL / CHECKLIST DE REQUISITOS",subt))
 e.append(P("Fecha de consulta: "+fecha,b))

 e.append(Paragraph("1. DATOS DE LA PERSONA",h))
 datos=[
  ["Nombre y apellido",perfil.get("nombre","PENDIENTE DE COMPLETAR")],
  ["Nacionalidad",perfil.get("nacionalidad","PENDIENTE DE COMPLETAR")],
  ["Teléfono",perfil.get("telefono","PENDIENTE DE COMPLETAR")],
  ["Dirección",perfil.get("direccion","PENDIENTE DE COMPLETAR")],
  ["Estado",perfil.get("estado","PENDIENTE DE COMPLETAR")],
  ["Código postal",perfil.get("codigo_postal","PENDIENTE DE COMPLETAR")],
  ["Correo",perfil.get("correo","PENDIENTE DE COMPLETAR")]
 ]
 tabla=Table([[esc(a),esc(v)] for a,v in datos],colWidths=[135,350],repeatRows=0)
 tabla.setStyle(TableStyle([
  ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
  ("FONTSIZE",(0,0),(-1,-1),8.5),
  ("LEADING",(0,0),(-1,-1),11),
  ("VALIGN",(0,0),(-1,-1),"TOP"),
  ("GRID",(0,0),(-1,-1),.35,colors.grey),
  ("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),
  ("LEFTPADDING",(0,0),(-1,-1),5),
  ("RIGHTPADDING",(0,0),(-1,-1),5),
  ("TOPPADDING",(0,0),(-1,-1),4),
  ("BOTTOMPADDING",(0,0),(-1,-1),4)
 ]))
 e.append(tabla)

 e.append(Paragraph("2. TRÁMITE",h))
 e.append(P(d.get("titulo",caso.get("titulo","")),b))
 e.append(P("Estado: "+d.get("estado_texto",""),estado))

 if perfil.get("menor")=="Sí":
  e.append(P("El texto proporcionado indica que hay un menor involucrado. Los datos específicos del menor deben completarse cuando correspondan.",b))

 if especiales:
  e.append(Paragraph("3. ATENCIÓN A TU CASO",h))
  for x in especiales:e.append(P("⚠ "+x,b))

 e.append(Paragraph("4. LO QUE YA TIENES",h))
 if c.get("tiene"):
  for x in c["tiene"]:e.append(P("☑ "+x,b))
 else:e.append(P("No se confirmó ningún documento como disponible.",b))

 e.append(Paragraph("5. LO QUE TE FALTA",h))
 if c.get("falta"):
  for x in c["falta"]:e.append(P("☐ "+x,b))
 else:e.append(P("No se identificó un documento faltante mediante tus respuestas.",b))

 e.append(Paragraph("6. LO QUE DEBES CONFIRMAR",h))
 if c.get("revisar"):
  for x in c["revisar"]:e.append(P("□ "+x,b))
 else:e.append(P("No quedaron documentos pendientes de confirmar.",b))

 e.append(Paragraph("7. ¿QUÉ DEBES HACER?",h))
 e.append(P(d.get("prepara"),b))

 if ruta.get("cita"):
  e.append(Paragraph("8. CITA",h))
  e.append(P(ruta["cita"],b))

 e.append(Paragraph("9. DOCUMENTOS ORIGINALES",h))
 e.append(P(ruta.get("llevar_original"),b))

 e.append(Paragraph("10. COPIAS",h))
 e.append(P(ruta.get("copias"),b))

 e.append(Paragraph("11. PAGO",h))
 e.append(P(d.get("pago"),b))

 if d.get("revision"):
  e.append(Paragraph("12. ANTES DE FIRMAR O IMPRIMIR",h))
  e.append(P(d["revision"],b))

 if d.get("vigencia") and caso_id in {"pasaporte_menor","pasaporte_primera_vez","matricula_primera_adulto","matricula_renovacion","matricula_menor"}:
  e.append(Paragraph("13. VIGENCIA",h))
  e.append(P(d["vigencia"],b))

 if d.get("entrega") and d.get("nivel")!="rojo":
  e.append(Paragraph("14. ENTREGA",h))
  e.append(P(d["entrega"],b))

 e.append(Paragraph("15. INFORMACIÓN IMPORTANTE",h))
 e.append(P(d.get("confirma"),b))

 e.append(Paragraph("16. INFORMACIÓN OFICIAL",h))
 e.append(P("Fuente oficial:",b))
 e.append(P(d.get("fuente"),small))
 e.append(Spacer(1,5))
 e.append(P("Citas oficiales: "+ "https://citas.sre.gob.mx",small))
 e.append(P("Tarifas oficiales: "+ "https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",small))

 e.append(Spacer(1,8))
 e.append(Paragraph("AVISO",h))
 e.append(P(d.get("aviso"),small))
 e.append(P("Esta Hoja de Ruta se basa en la información proporcionada durante la consulta. No sustituye la revisión de la autoridad consular. Si tus documentos o circunstancias cambian, vuelve a revisar los requisitos oficiales.",small))

 doc.build(e)
 buf.seek(0)
 return buf

@app.post("/api/pdf")
def generar_pdf(data:PDFData):
 caso=obtener_caso(data.caso)
 if not caso:return {"ok":False,"mensaje":"No encontramos el trámite seleccionado."}
 buf=crear_pdf(data.caso,dict(data.respuestas or {}))
 if not buf:return {"ok":False,"mensaje":"No fue posible generar el PDF."}
 return StreamingResponse(buf,media_type="application/pdf",headers={"Content-Disposition":'attachment; filename="Hoja_Ruta_Mexicano_Apoya_Mexicano.pdf"'})
