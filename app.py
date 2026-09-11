import os,io
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any,Dict,Optional
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,Paragraph
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from consular_engine import iniciar,seleccionar,seleccionar_caso,continuar,interpretar,obtener_caso,FUENTES

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="3.0.0")
app.mount("/static",StaticFiles(directory="static"),name="static")

class Respuesta(BaseModel):
 servicio:Optional[str]=""
 caso:Optional[str]=""
 pregunta_id:Optional[str]=""
 texto:Optional[str]=""
 respuestas:Dict[str,Any]={}
 resultado:Optional[Dict[str,Any]]=None

@app.get("/")
def home():
 return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","version":"3.0.0"}

@app.get("/api/casos")
def casos(servicio:Optional[str]=None):
 from consular_engine import catalogo
 return {"estado":"seleccionar","tipo":"catalogo","servicio":servicio or "todos","opciones":catalogo(servicio)}

@app.get("/api/inicio/{servicio}")
def inicio(servicio:str):
 return iniciar(servicio)

@app.post("/api/iniciar")
def api_iniciar(data:Respuesta):
 if not data.servicio:raise HTTPException(400,"Falta seleccionar el tipo de servicio.")
 if data.caso:
  return seleccionar_caso(data.caso,data.respuestas)
 return iniciar(data.servicio,data.caso,data.respuestas)

@app.post("/api/entender")
def entender(data:Respuesta):
 if not data.servicio:raise HTTPException(400,"Falta seleccionar el servicio.")
 return interpretar(data.servicio,data.texto or "",data.respuestas,data.pregunta_id)

@app.post("/api/responder")
def responder(data:Respuesta):
 if not data.servicio:raise HTTPException(400,"Falta seleccionar el servicio.")
 texto=(data.texto or "").strip()
 res=dict(data.respuestas or {})

 if data.caso:
  caso=obtener_caso(data.caso)
  if not caso:raise HTTPException(404,"Trámite no encontrado.")
  if data.pregunta_id and texto:
   res[data.pregunta_id]=texto
  return continuar(data.caso,res,data.pregunta_id,texto)

 return interpretar(data.servicio,texto,res,data.pregunta_id)

def esc(v):
 return str(v or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br/>")

def lista_pdf(items):
 return [str(x) for x in (items or []) if str(x).strip()]

def generar_pdf(resultado):
 buf=io.BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=LETTER,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
 styles=getSampleStyleSheet()
 titulo=styles["Title"];titulo.alignment=TA_CENTER;titulo.fontSize=19
 h=styles["Heading2"];h.fontSize=12;h.spaceBefore=14;h.spaceAfter=8
 body=styles["BodyText"];body.fontSize=9.5;body.leading=13
 small=styles["BodyText"];small.fontSize=8;small.leading=11
 story=[]

 def H(t):story.append(Paragraph(esc(t),h));story.append(Spacer(1,4))
 def P(t):story.append(Paragraph(esc(t),body));story.append(Spacer(1,6))
 def L(items):
  for x in lista_pdf(items):P("• "+x)
 def tabla(filas):
  if not filas:return
  t=Table(filas,colWidths=[145,345],repeatRows=1)
  t.setStyle(TableStyle([
   ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173452")),
   ("TEXTCOLOR",(0,0),(-1,0),colors.white),
   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
   ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
   ("FONTSIZE",(0,0),(-1,-1),9),
   ("LEADING",(0,0),(-1,-1),12),
   ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#b7c1cb")),
   ("VALIGN",(0,0),(-1,-1),"TOP"),
   ("BACKGROUND",(0,1),(-1,-1),colors.HexColor("#f7f9fb")),
   ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f7f9fb")]),
   ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
   ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)
  ]))
  story.append(t);story.append(Spacer(1,8))

 nivel=resultado.get("nivel","amarillo")
 estado=resultado.get("estado_texto","TE FALTA ALGO")
 perfil=resultado.get("perfil") or {}
 docs=resultado.get("documentos") or []
 tiene=[x.get("nombre") for x in docs if x.get("estado")=="tiene"]
 falta=[x.get("nombre") for x in docs if x.get("estado")=="falta"]
 revisar=[x.get("nombre") for x in docs if x.get("estado")=="revisar"]

 story.append(Paragraph("MEXICANO APOYA MEXICANO",titulo))
 story.append(Paragraph("HOJA DE RUTA PERSONAL DEL TRÁMITE",titulo))
 story.append(Spacer(1,12))
 story.append(Paragraph("<b>"+esc(estado)+"</b>",Paragraph("BodyText",styles).clone(
  "estado",fontSize=12,leading=16,alignment=TA_CENTER,textColor=
  colors.HexColor("#9b2424" if nivel=="rojo" else "#8a6500" if nivel=="amarillo" else "#087f3e"))))
 story.append(Spacer(1,12))

 H("1. DATOS PERSONALES")
 filas=[["DATO","INFORMACIÓN"]]
 campos=[
  ("Nombre",perfil.get("nombre")),
  ("Nacionalidad",perfil.get("nacionalidad")),
  ("Teléfono",perfil.get("telefono")),
  ("Dirección",perfil.get("direccion")),
  ("Estado",perfil.get("estado")),
  ("ZIP",perfil.get("zip") or perfil.get("codigo_postal")),
  ("Correo",perfil.get("email") or perfil.get("correo"))
 ]
 for a,b in campos:filas.append([a,b or "PENDIENTE DE COMPLETAR"])
 tabla(filas)

 H("2. TRÁMITE")
 P(resultado.get("tramite") or resultado.get("titulo") or "PENDIENTE DE COMPLETAR")

 personas=resultado.get("personas_obligatorias") or []
 if personas:
  H("3. PERSONAS QUE DEBEN PRESENTARSE")
  L(personas)

 H("4. REQUISITOS OBLIGATORIOS")
 L(resultado.get("requisitos_obligatorios"))

 H("5. LO QUE YA TIENES")
 L(tiene or ["No se registró todavía un documento como disponible."])

 H("6. LO QUE TE FALTA")
 L(falta or ["No se identificó un documento faltante en las respuestas."])

 H("7. LO QUE DEBES CONFIRMAR")
 L(revisar)
 L(resultado.get("especiales"))

 H("8. ¿QUÉ DEBES HACER?")
 P(resultado.get("prepara"))

 H("9. CITA")
 L(resultado.get("cita"))
 if not resultado.get("cita"):P("No corresponde cita según la información registrada.")

 H("10. DOCUMENTOS ORIGINALES")
 L(resultado.get("originales"))

 if resultado.get("copias"):
  H("11. COPIAS")
  L(resultado.get("copias"))

 H("12. PAGO")
 P(resultado.get("pago"))

 H("13. ANTES DE FIRMAR O IMPRIMIR")
 P(resultado.get("revision"))

 if resultado.get("vigencia"):
  H("14. VIGENCIA")
  P(resultado.get("vigencia"))

 if resultado.get("entrega"):
  H("15. ENTREGA")
  P(resultado.get("entrega"))

 H("16. INFORMACIÓN IMPORTANTE")
 L(resultado.get("importante"))
 if resultado.get("confirma"):P(resultado.get("confirma"))

 H("INFORMACIÓN OFICIAL")
 P(resultado.get("fuente") or FUENTES.get("tarifas",""))

 story.append(Spacer(1,12))
 story.append(Paragraph(
  "Esta Hoja de Ruta se basa en la información proporcionada durante la consulta y no sustituye la revisión de la autoridad consular. "+
  "MEXICANO APOYA MEXICANO es una aplicación independiente y no es el Gobierno de México ni representa a ningún Consulado.",
  small
 ))
 doc.build(story)
 buf.seek(0)
 return buf

@app.post("/api/pdf")
def pdf(data:Respuesta):
 r=data.resultado
 if not r:
  if data.caso:
   caso=obtener_caso(data.caso)
   if not caso:raise HTTPException(404,"Trámite no encontrado.")
   r=continuar(data.caso,data.respuestas or {})
  else:raise HTTPException(400,"Primero termina la consulta.")
 if not r or r.get("tipo")!="resultado":
  raise HTTPException(400,"La consulta todavía no está terminada.")
 try:
  pdf_file=generar_pdf(r)
 except Exception as e:
  raise HTTPException(500,f"No se pudo generar el PDF: {e}")
 return StreamingResponse(pdf_file,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf"})

if __name__=="__main__":
 import uvicorn
 uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
