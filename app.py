import os,json,hashlib,secrets
from pathlib import Path
from datetime import datetime,timedelta,timezone
import stripe
from google import genai
from fastapi import FastAPI,HTTPException,Depends,Request,UploadFile,File
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static";DATA=BASE/"data";OUT=BASE/"salidas"
STATIC.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
ACCESS_FILE=DATA/"access.json"
if not ACCESS_FILE.exists():ACCESS_FILE.write_text("{}")

APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
ADMIN_USER=os.getenv("ADMIN_USERNAME") or os.getenv("DEV_USER","")
ADMIN_PASS=os.getenv("ADMIN_PASSWORD") or os.getenv("DEV_PASS","")
GEMINI_KEY=os.getenv("GEMINI_API_KEY","")
STRIPE_KEY=os.getenv("STRIPE_SECRET_KEY","")
WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
PRICE_IDS={
 "daily":os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1"),
 "monthly":os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2"),
 "annual":os.getenv("STRIPE_PRICE_ID_ANNUAL")
}
stripe.api_key=STRIPE_KEY
gemini=genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="9.0")
app.mount("/static",StaticFiles(directory=STATIC),name="static")
security=HTTPBasic(auto_error=False)

class DatosTramite(BaseModel):
 categoria_tramite:str=""
 primer_nombre:str=""
 segundo_nombre:str=""
 primer_apellido:str=""
 segundo_apellido:str=""
 fecha_nacimiento:str=""
 lugar_nacimiento:str=""
 direccion_usa:str=""
 telefono:str=""
 nacionalidad:str="Mexicana"
 consulado:str=""
 cita:str=""
 documentos_tenidos:str=""
 documentos_faltantes:str=""
 datos_extraidos:list[dict]=Field(default_factory=list)
 estado_posterior:str="pendiente"
 extra_1:str=""
 extra_2:str=""
 confirmado:bool=False

class PreguntaRequest(BaseModel):
 pregunta:str
 contexto:str=""
 categoria_tramite:str=""

class ResultadoRequest(BaseModel):
 categoria_tramite:str=""
 resultado:str=""
 comentario:str=""
 estado:str=""

class StripeCheckoutRequest(BaseModel):
 plan:str

def load_access():
 try:return json.loads(ACCESS_FILE.read_text())
 except:return {}

def save_access(d):ACCESS_FILE.write_text(json.dumps(d,ensure_ascii=False,indent=2))

def htoken(x):return hashlib.sha256(x.encode()).hexdigest()

def admin_ok(c):
 return bool(c and ADMIN_USER and ADMIN_PASS and secrets.compare_digest(c.username,ADMIN_USER) and secrets.compare_digest(c.password,ADMIN_PASS))

def customer_access(request):
 token=request.cookies.get("save_access_token")
 if not token:return None
 rec=load_access().get("tokens",{}).get(htoken(token))
 if not rec or not rec.get("active",True):return None
 exp=rec.get("expires")
 if exp and datetime.now(timezone.utc).timestamp()>float(exp):return None
 return rec

def require_access(request:Request,credentials:HTTPBasicCredentials|None=Depends(security)):
 if admin_ok(credentials):return {"type":"admin"}
 rec=customer_access(request)
 if rec:return rec
 raise HTTPException(401,"Acceso no autorizado")

def activate(email,plan,session_id="",subscription_id="",expires=None):
 if not email:return None
 d=load_access();d.setdefault("customers",{});d.setdefault("tokens",{})
 raw=secrets.token_urlsafe(40);token=htoken(raw)
 if expires is None:expires=(datetime.now(timezone.utc)+timedelta(hours=24)).timestamp()
 rec={"email":email,"plan":plan,"session_id":session_id,"subscription_id":subscription_id,"expires":expires,"active":True,"token":token}
 d["customers"][email]=rec;d["tokens"][token]=rec;save_access(d)
 return raw

@app.get("/")
def home():return FileResponse(STATIC/"index.html")

@app.post("/api/admin-login")
def admin_login(credentials:HTTPBasicCredentials=Depends(security)):
 if not admin_ok(credentials):raise HTTPException(401,"Usuario o contraseña incorrectos")
 return {"ok":True,"admin":True}

@app.post("/api/create-checkout-session")
def checkout(req:StripeCheckoutRequest):
 price=PRICE_IDS.get(req.plan)
 if not price:raise HTTPException(400,"Price ID no configurado para este plan")
 try:
  p=stripe.Price.retrieve(price)
  mode="subscription" if p.type=="recurring" else "payment"
  s=stripe.checkout.Session.create(mode=mode,line_items=[{"price":price,"quantity":1}],success_url=f"{APP_URL}/?success=true&session_id={{CHECKOUT_SESSION_ID}}",cancel_url=f"{APP_URL}/?cancel=true")
  return {"checkout_url":s.url}
 except Exception as e:raise HTTPException(500,str(e))

@app.get("/api/verify-payment")
def verify_payment(session_id:str):
 try:s=stripe.checkout.Session.retrieve(session_id,expand=["subscription"])
 except Exception as e:raise HTTPException(400,str(e))
 if s.payment_status not in ("paid","no_payment_required"):raise HTTPException(403,"Pago no confirmado")
 email=(s.customer_details.email if s.customer_details else None)
 if not email:raise HTTPException(400,"No se encontró el correo del cliente")
 plan="daily";sub_id="";expires=(datetime.now(timezone.utc)+timedelta(hours=24)).timestamp()
 if s.mode=="subscription":
  sub=s.subscription
  if isinstance(sub,str):sub=stripe.Subscription.retrieve(sub)
  if sub.status not in ("active","trialing"):raise HTTPException(403,"Suscripción no activa")
  sub_id=sub.id;expires=float(sub.current_period_end);plan="monthly"
 raw=activate(email,plan,s.id,sub_id,expires)
 from fastapi.responses import JSONResponse
 r=JSONResponse({"ok":True,"email":email,"plan":plan})
 r.set_cookie("save_access_token",raw,max_age=max(3600,int(expires-datetime.now(timezone.utc).timestamp())),httponly=True,secure=True,samesite="lax")
 return r

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
 body=await request.body();sig=request.headers.get("stripe-signature")
 try:event=stripe.Webhook.construct_event(body,sig,WEBHOOK_SECRET)
 except Exception as e:raise HTTPException(400,f"Webhook inválido: {e}")
 o=event["data"]["object"];typ=event["type"]
 if typ in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
  email=(o.get("customer_details") or {}).get("email")
  if email:
   plan="monthly" if o.get("mode")=="subscription" else "daily";sub=o.get("subscription");exp=None
   if sub:
    try:
     ss=stripe.Subscription.retrieve(sub);exp=float(ss.current_period_end)
    except:pass
   activate(email,plan,o.get("id",""),sub or "",exp)
 elif typ in ("customer.subscription.updated","customer.subscription.deleted"):
  cid=o.get("customer");email=None
  try:
   if cid:email=stripe.Customer.retrieve(cid).get("email")
  except:pass
  if email:
   d=load_access();rec=d.get("customers",{}).get(email)
   if rec:
    rec["active"]=o.get("status") in ("active","trialing")
    if o.get("current_period_end"):rec["expires"]=float(o["current_period_end"])
    d.setdefault("tokens",{})[rec["token"]]=rec;save_access(d)
 return {"received":True}

@app.get("/api/check-access")
def check_access(request:Request,credentials:HTTPBasicCredentials|None=Depends(security)):
 if admin_ok(credentials):return {"ok":True,"type":"admin"}
 rec=customer_access(request)
 return {"ok":bool(rec),"type":"customer" if rec else None,"plan":rec.get("plan") if rec else None}

@app.post("/api/ficha-tramite")
def ficha(data:DatosTramite,_=Depends(require_access)):
 return {"ok":True,"datos":data.model_dump()}

@app.post("/api/extraer-pdf")
async def extraer_pdf(file:UploadFile=File(...),_=Depends(require_access)):
 if not file.filename or not file.filename.lower().endswith(".pdf"):raise HTTPException(400,"Solo se acepta PDF")
 raw=await file.read()
 if len(raw)>15*1024*1024:raise HTTPException(400,"El PDF es demasiado grande")
 tmp=OUT/("_tmp_"+secrets.token_hex(5)+".pdf");tmp.write_bytes(raw)
 try:
  reader=PdfReader(str(tmp));parts=[]
  for page in reader.pages:
   try:parts.append(page.extract_text() or "")
   except:pass
  text="\n".join(parts).strip()
 finally:
  try:tmp.unlink()
  except:pass
 return {"ok":True,"nombre":file.filename,"texto":text[:30000],"paginas":len(reader.pages)}

@app.post("/api/pregunta")
def pregunta(req:PreguntaRequest,_=Depends(require_access)):
 if not gemini:raise HTTPException(500,"GEMINI_API_KEY no configurada")
 contexto=req.contexto or ""
 tramite=req.categoria_tramite or ""
 prompt=f"""Eres el asistente de SAVE MÉXICO AYUDAR.
Ayudas a personas mexicanas en Estados Unidos a organizar y preparar información para sus trámites.
Usa lenguaje español sencillo, claro y respetuoso. No amontones información.
No inventes requisitos. Si una respuesta depende del Consulado, gobierno o autoridad, indícalo.
No afirmes que SAVE MÉXICO AYUDAR es una autoridad.
Trámite: {tramite}
Contexto: {contexto}
Pregunta del usuario: {req.pregunta}
Responde directamente. Da primero la respuesta principal y después, solamente si es necesario, pasos cortos."""
 try:
  r=gemini.models.generate_content(model="gemini-2.5-flash",contents=prompt)
  return {"respuesta":(r.text or "").strip()}
 except Exception as e:raise HTTPException(500,f"Gemini: {e}")

def safe(v):return str(v or "").strip()

@app.post("/api/generar-guia-consular")
def generar_guia(data:DatosTramite,_=Depends(require_access)):
 nombre="SAVE_MEXICO_"+datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+secrets.token_hex(3)+".pdf"
 path=OUT/nombre
 c=canvas.Canvas(str(path),pagesize=LETTER);W,H=LETTER;y=H-45
 def newpage():
  nonlocal y
  c.showPage();y=H-45
 def text(t,size=10,bold=False,gap=16):
  nonlocal y
  if y<55:newpage()
  c.setFont("Helvetica-Bold" if bold else "Helvetica",size)
  words=str(t).split();line=""
  for w in words:
   test=(line+" "+w).strip()
   if c.stringWidth(test,"Helvetica-Bold" if bold else "Helvetica",size)>W-90:
    c.drawString(45,y,line);y-=gap;line=w
   else:line=test
  if line:c.drawString(45,y,line);y-=gap
 def section(t):
  nonlocal y
  if y<75:newpage()
  y-=5;c.setFillColorRGB(.09,.27,.40);c.setFont("Helvetica-Bold",11);c.drawString(45,y,t);y-=18;c.setFillColorRGB(0,0,0)
 def field(label,value):
  if safe(value):text(f"{label}: {value}",10,False,15)
 c.setFillColorRGB(.09,.25,.38);c.setFont("Helvetica-Bold",19);c.drawCentredString(W/2,y,"SAVE MÉXICO AYUDAR");y-=25
 c.setFillColorRGB(0,0,0);c.setFont("Helvetica-Bold",13);c.drawCentredString(W/2,y,"GUÍA DE PREPARACIÓN DE TRÁMITE");y-=30
 section("1. TRÁMITE")
 field("Tipo de trámite",data.categoria_tramite)
 section("2. DATOS DE LA PERSONA")
 field("Primer nombre",data.primer_nombre);field("Segundo nombre",data.segundo_nombre)
 field("Primer apellido",data.primer_apellido);field("Segundo apellido",data.segundo_apellido)
 field("Fecha de nacimiento",data.fecha_nacimiento);field("Lugar de nacimiento",data.lugar_nacimiento)
 field("Nacionalidad",data.nacionalidad);field("Domicilio en Estados Unidos",data.direccion_usa);field("Teléfono",data.telefono)
 section("3. DOCUMENTOS QUE YA TIENE")
 docs=[x.strip() for x in safe(data.documentos_tenidos).split(",") if x.strip()]
 if docs:
  for x in docs:text("☐ "+x)
 else:text("No se indicó ningún documento.")
 section("4. DOCUMENTOS QUE FALTAN")
 miss=[x.strip() for x in safe(data.documentos_faltantes).split(",") if x.strip()]
 if miss:
  for x in miss:text("☐ "+x)
 else:text("No se indicó ningún documento pendiente.")
 section("5. INFORMACIÓN DEL TRÁMITE")
 field("Consulado",data.consulado);field("Cita",data.cita)
 field("Información adicional",data.extra_1);field("Información adicional",data.extra_2)
 section("6. ANTES DE PRESENTARSE")
 for x in ["Revisar que todos los datos personales sean correctos.","Revisar los documentos originales y copias que correspondan.","Confirmar los requisitos oficiales directamente con la autoridad correspondiente.","Confirmar fecha, hora y lugar de la cita, si aplica."]:
  text("☐ "+x)
 section("AVISO IMPORTANTE")
 text("Esta guía es una herramienta privada para organizar información y preparar un trámite. SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida. No es una agencia del Gobierno de México ni representa a ningún Consulado de México.")
 text("Los requisitos, documentos aceptados, citas, decisiones y resultados corresponden exclusivamente a la autoridad competente. Verifica siempre la información oficial antes de presentar tu trámite.",8)
 c.save()
 return {"ok":True,"archivo":f"/descargar/{nombre}","nombre":nombre}

@app.get("/descargar/{nombre}")
def descargar(nombre:str,_=Depends(require_access)):
 p=OUT/Path(nombre).name
 if not p.exists():raise HTTPException(404,"Archivo no encontrado")
 return FileResponse(p,filename=p.name,media_type="application/pdf")

@app.post("/api/resultado-tramite")
def resultado(req:ResultadoRequest,_=Depends(require_access)):
 estado=req.estado or req.resultado
 return {"ok":True,"estado":estado,"mensaje":"Resultado guardado correctamente."}

@app.post("/api/logout")
def logout():
 from fastapi.responses import JSONResponse
 r=JSONResponse({"ok":True});r.delete_cookie("save_access_token");return r

@app.get("/api/estado")
def estado():return {"ok":True,"app":"SAVE MÉXICO AYUDAR","version":"9.0"}
