from io import BytesIO
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib import colors
from consular_engine import iniciar,interpretar,continuar,catalogo,obtener_caso,resultado,fusionar_contexto

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="6.0.0")
app.mount("/static",StaticFiles(directory="static"),name="static")

class Inicio(BaseModel):
 servicio:str
 texto:str=""

class Respuesta(BaseModel):
 servicio:str
 caso:str=""
 texto:str=""
 respuestas:dict=Field(default_factory=dict)
 pregunta_id:str=""

class PDFData(BaseModel):
 caso:str
 respuestas:dict=Field(default_factory=dict)

@app.get("/")
def raiz():
 return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","motor":"consular_engine","version":"6.0.0"}

@app.get("/api/casos")
def casos(servicio:str=""):
 return {"ok":True,"casos":catalogo(servicio or None)}

@app.get("/api/inicio/{servicio}")
def comenzar(servicio:str):
 if servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 r=iniciar(servicio)
 r.update({"ok":True,"servicio":servicio})
 return r

@app.post("/api/iniciar")
def iniciar_caso(data:Inicio):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 r=interpretar(data.servicio,data.texto,{})
 r.update({"ok":True,"servicio":data.servicio})
 return r

@app.post("/api/entender")
def entender(data:Inicio):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}
 if not data.texto.strip():
  return {"ok":False,"estado":"necesita_descripcion","pregunta":"Cuéntame con tus propias palabras qué necesitas resolver."}
 r=interpretar(data.servicio,data.texto,{})
 r.update({"ok":True,"servicio":data.servicio})
 return r

@app.post("/api/responder")
def responder(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  return {"ok":False,"mensaje":"Servicio no disponible."}

 respuestas=dict(data.respuestas or {})
 texto=data.texto.strip()

 if data.caso:
  respuestas=fusionar_contexto(respuestas,texto,data.pregunta_id)
  respuestas["_caso"]=data.caso
  respuestas["_pregunta_id"]=data.pregunta_id
  r=continuar(data.caso,respuestas)
 elif texto:
  r=interpretar(data.servicio,texto,respuestas)
 else:
  return {"ok":False,"mensaje":"Necesitamos tu respuesta para continuar."}

 respuestas=dict(r.get("respuestas") or respuestas)
 if data.caso:respuestas["_caso"]=data.caso
 r["respuestas"]=respuestas
 r["ok"]=True
 r["servicio"]=data.servicio
 return r

def esc(t):
 return str(t or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br/>")

def P(t,s):
 return Paragraph(esc(t),s)

def lista_pdf(st,titulo,items,simbolo,body):
 st.append(Paragraph(titulo,body["h"]))
 if items:
  for x in items:st.append(P(simbolo+str(x),body["b"]))
 else:
  st.append(P("No se registró información en esta categoría.",body["b"]))
 st.append(Spacer(1,4))

def crear_pdf(caso_id,respuestas):
 caso=obtener_caso(caso_id)
 if not caso:return None
 d=resultado(caso,dict(respuestas or {}))
 perfil=d.get("perfil") or {}
 c=d.get("checklist") or {}
 ruta=d.get("ruta") or {}
 especiales=d.get("especiales") or []
 personas=d.get("personas_obligatorias") or []
 obligatorios=d.get("requisitos_obligatorios") or []

 buf=BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=letter,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=38)

 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("T",parent=styles["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=5)
 subt=ParagraphStyle("ST",parent=styles["BodyText"],fontSize=10,leading=13,alignment=TA_CENTER,spaceAfter=12)
 h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=12.5,leading=15,spaceBefore=10,spaceAfter=6)
 b=ParagraphStyle("B",parent=styles["BodyText"],fontSize=9.7,leading=13.5,spaceAfter=4)
 estado=ParagraphStyle("E",parent=b,fontSize=11,leading=15,spaceAfter=8)
 small=ParagraphStyle("S",parent=b,fontSize=7.5,leading=10)

 e=[]
 fecha=datetime.now().strftime("%d/%m/%Y %H:%M")

 e.append(Paragraph("MEXICANO APOYA MEXICANO",titulo))
 e.append(Paragraph("HOJA DE RUTA PERSONAL / CHECKLIST DE REQUISITOS",subt))
 e.append(P("Fecha de consulta: "+fecha,b))

 e.append(Paragraph("1. DATOS PERSONALES",h))
 datos=[
 ["Nombre y apellido",perfil.get("nombre","PENDIENTE DE COMPLETAR")],
 ["Nacionalidad",perfil.get("nacionalidad","PENDIENTE DE COMPLETAR")],
 ["Teléfono",perfil.get("telefono","PENDIENTE DE COMPLETAR")],
 ["Dirección",perfil.get("direccion","PENDIENTE DE COMPLETAR")],
 ["Estado",perfil.get("estado","PENDIENTE DE COMPLETAR")],
 ["Código postal",perfil.get("codigo_postal","PENDIENTE DE COMPLETAR")],
 ["Correo",perfil.get("correo","PENDIENTE DE COMPLETAR")]
 ]
 tabla=Table([[esc(a),esc(v)] for a,v in datos],colWidths=[135,350])
 tabla.setStyle(TableStyle([
 ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
 ("FONTSIZE",(0,0),(-1,-1),8.5),
 ("LEADING",(0,0),(-1,-1),11),
 ("VALIGN",(0,0),(-1,-1),"TOP"),
 ("GRID",(0,0),(-1,-1),.35,colors.grey),
 ("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),
 ("LEFTPADDING",(0,0),(-1,-1),5),
 ("RIGHTPADDING",(0,0),(-1,-1),5),
 ("TOPPADDING",(0,0),(-1,-1),5),
 ("BOTTOMPADDING",(0,0),(-1,-1),5)
 ]))
 e.append(tabla)
 e.append(Spacer(1,8))

 e.append(Paragraph("2. PERSONAS QUE DEBEN PRESENTARSE",h))
 if personas:
  lista_pdf(e,"",personas,"• ",{"h":h,"b":b})
 else:
  if caso_id=="pasaporte_menor":
   e.append(P("El menor y quienes ejerzan la patria potestad o tutela deben revisarse según el caso.",b))
  elif caso_id=="matricula_menor":
   e.append(P("El menor y quienes ejerzan la patria potestad o tutela deben revisarse según el caso.",b))
  else:
   e.append(P("La presentación personal depende del trámite. Revisa la información oficial.",b))

 e.append(Paragraph("3. TRÁMITE",h))
 e.append(P(d.get("titulo",caso.get("titulo","")),b))
 e.append(P("ESTADO: "+d.get("estado_texto",""),estado))

 e.append(Paragraph("4. REQUISITOS OBLIGATORIOS",h))
 if obligatorios:
  lista_pdf(e,"",obligatorios,"• ",{"h":h,"b":b})
 else:
  e.append(P("Los requisitos deben revisarse según las respuestas proporcionadas.",b))

 e.append(Paragraph("5. LO QUE YA TIENES",h))
 lista_pdf(e,"",c.get("tiene") or [],"☑ ",{"h":h,"b":b})

 e.append(Paragraph("6. LO QUE TE FALTA",h))
 lista_pdf(e,"",c.get("falta") or [],"☐ ",{"h":h,"b":b})

 e.append(Paragraph("7. LO QUE DEBES CONFIRMAR",h))
 lista_pdf(e,"",c.get("revisar") or [],"□ ",{"h":h,"b":b})

 if especiales:
  e.append(Paragraph("8. ATENCIÓN A TU CASO",h))
  lista_pdf(e,"",especiales,"⚠ ",{"h":h,"b":b})

 e.append(Paragraph("9. ¿QUÉ DEBES HACER?",h))
 e.append(P(d.get("prepara","Revisa los requisitos oficiales antes de acudir."),b))

 if ruta.get("cita"):
  e.append(Paragraph("10. CITA",h))
  e.append(P(ruta["cita"],b))

 e.append(Paragraph("11. DOCUMENTOS ORIGINALES",h))
 e.append(P(ruta.get("llevar_original","Lleva los documentos originales que correspondan a tu trámite."),b))

 e.append(Paragraph("12. COPIAS",h))
 e.append(P(ruta.get("copias","Lleva copias únicamente cuando la fuente oficial las indique."),b))

 e.append(Paragraph("13. PAGO",h))
 e.append(P(d.get("pago","Confirma la tarifa y forma de pago vigente."),b))

 if d.get("revision"):
  e.append(Paragraph("14. ANTES DE FIRMAR O IMPRIMIR",h))
  e.append(P(d["revision"],b))

 if d.get("vigencia"):
  e.append(Paragraph("15. VIGENCIA",h))
  e.append(P(d["vigencia"],b))

 if d.get("entrega"):
  e.append(Paragraph("16. ENTREGA",h))
  e.append(P(d["entrega"],b))

 e.append(Paragraph("17. INFORMACIÓN IMPORTANTE",h))
 e.append(P(d.get("confirma","La autoridad consular puede solicitar documentación adicional."),b))

 e.append(Paragraph("18. INFORMACIÓN OFICIAL",h))
 e.append(P("Fuente oficial:",b))
 e.append(P(d.get("fuente",FUENTES["pasaporte"]) if "FUENTES" in globals() else d.get("fuente",""),small))
 e.append(P("Citas oficiales: https://citas.sre.gob.mx",small))
 e.append(P("Tarifas oficiales: https://consulmex.sre.gob.mx/miami/index.php/tarifas-consulares",small))

 e.append(Spacer(1,8))
 e.append(Paragraph("AVISO",h))
 e.append(P(d.get("aviso","Esta información no sustituye la revisión de la autoridad consular."),small))

 doc.build(e)
 buf.seek(0)
 return buf

@app.post("/api/pdf")
def generar_pdf(data:PDFData):
 caso=obtener_caso(data.caso)
 if not caso:
  return {"ok":False,"mensaje":"No encontramos el trámite seleccionado."}
 buf=crear_pdf(data.caso,data.respuestas)
 if not buf:
  return {"ok":False,"mensaje":"No fue posible generar el PDF."}
 return StreamingResponse(
  buf,
  media_type="application/pdf",
  headers={"Content-Disposition":'attachment; filename="Hoja_Ruta_Mexicano_Apoya_Mexicano.pdf"'}
 )
