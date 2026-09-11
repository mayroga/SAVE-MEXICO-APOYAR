import os,json,hashlib,secrets
from datetime import datetime,timedelta,timezone
from pathlib import Path
import stripe,httpx
from fastapi import FastAPI,HTTPException,Depends,Request
from fastapi.responses import HTMLResponse,FileResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
DEV_USER=os.getenv("DEV_USER") or os.getenv("ADMIN_USERNAME","")
DEV_PASS=os.getenv("DEV_PASS") or os.getenv("ADMIN_PASSWORD","")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
stripe.api_key=os.getenv("STRIPE_SECRET_KEY","")
WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
PRICE_IDS={"daily":os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1"),"monthly":os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2"),"annual":os.getenv("STRIPE_PRICE_ID_ANNUAL")}

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static";DATA=BASE/"data";OUT=BASE/"salidas"
STATIC.mkdir(parents=True,exist_ok=True)
DATA.mkdir(parents=True,exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)
ACCESS_FILE=DATA/"access.json"
if not ACCESS_FILE.exists():ACCESS_FILE.write_text("{}")

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="8.1")
app.mount("/static",StaticFiles(directory=STATIC),name="static")
security=HTTPBasic(auto_error=False)

class DatosTramite(BaseModel):
    categoria_tramite:str
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
    documentos_tenidos:list[str]=Field(default_factory=list)
    documentos_faltantes:list[str]=Field(default_factory=list)
    datos_extraidos:list[dict]=Field(default_factory=list)
    estado_posterior:str="pendiente"
    extra_1:str=""
    extra_2:str=""
    confirmado:bool=False

class PreguntaRequest(BaseModel):
    pregunta:str
    contexto:str=""

class ResultadoRequest(BaseModel):
    categoria_tramite:str=""
    resultado:str=""
    comentario:str=""

class StripeCheckoutRequest(BaseModel):
    plan:str

def load_access():
    try:return json.loads(ACCESS_FILE.read_text())
    except:return {}

def save_access(d):
    ACCESS_FILE.write_text(json.dumps(d,ensure_ascii=False,indent=2))

def hash_token(t):return hashlib.sha256(t.encode()).hexdigest()

def admin_ok(c):
    return bool(c and secrets.compare_digest(c.username,DEV_USER) and secrets.compare_digest(c.password,DEV_PASS))

def access_cookie(request):
    t=request.cookies.get("save_access_token")
    if not t:return None
    return load_access().get("tokens",{}).get(hash_token(t))

def require_access(request:Request,credentials:HTTPBasicCredentials|None=Depends(security)):
    if admin_ok(credentials):return {"type":"admin"}
    a=access_cookie(request)
    if not a:raise HTTPException(401,"Acceso no autorizado")
    exp=a.get("expires")
    if exp and datetime.now(timezone.utc).timestamp()>exp:raise HTTPException(401,"Acceso vencido")
    return a

def activate(email,plan,session_id="",subscription_id="",expires=None):
    if not email:return
    d=load_access();d.setdefault("customers",{})
    token=secrets.token_urlsafe(40)
    if expires is None:expires=(datetime.now(timezone.utc)+timedelta(hours=24)).timestamp()
    rec={"email":email,"plan":plan,"session_id":session_id,"subscription_id":subscription_id,"expires":expires,"active":True,"token":hash_token(token)}
    d["customers"][email]=rec;d.setdefault("tokens",{})[rec["token"]]=rec
    save_access(d)

@app.get("/")
def home():return FileResponse(STATIC/"index.html")

@app.post("/api/admin-login")
def admin_login(credentials:HTTPBasicCredentials=Depends(security)):
    if not admin_ok(credentials):raise HTTPException(401,"Usuario o contraseña incorrectos")
    return {"ok":True,"admin":True}

@app.post("/api/create-checkout-session")
def create_checkout(req:StripeCheckoutRequest):
    price_id=PRICE_IDS.get(req.plan)
    if not price_id:raise HTTPException(400,"Plan no configurado")
    try:
        p=stripe.Price.retrieve(price_id)
        mode="subscription" if p.type=="recurring" else "payment"
        s=stripe.checkout.Session.create(
            mode=mode,
            line_items=[{"price":price_id,"quantity":1}],
            success_url=f"{APP_URL}/?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?cancel=true",
            allow_promotion_codes=True
        )
        return {"checkout_url":s.url}
    except Exception as e:raise HTTPException(500,str(e))

@app.get("/api/verify-payment")
def verify_payment(session_id:str):
    try:s=stripe.checkout.Session.retrieve(session_id,expand=["subscription","customer"])
    except Exception as e:raise HTTPException(400,str(e))
    if s.payment_status not in ("paid","no_payment_required"):raise HTTPException(403,"Pago no confirmado")
    email=s.customer_details.email if s.customer_details else None
    if not email:raise HTTPException(400,"No se encontró el correo")
    plan="daily";sub_id="";expires=None
    if s.mode=="subscription":
        plan="monthly"
        sub=s.subscription
        if isinstance(sub,str):sub=stripe.Subscription.retrieve(sub)
        sub_id=sub.id
        if sub.status not in ("active","trialing"):raise HTTPException(403,"Suscripción no activa")
        expires=float(sub.current_period_end)
    else:
        for k,v in PRICE_IDS.items():
            if s.line_items if False else False:pass
        plan="daily"
        expires=(datetime.now(timezone.utc)+timedelta(hours=24)).timestamp()
    activate(email,plan,s.id,sub_id,expires)
    d=load_access();rec=d["customers"][email];raw=secrets.token_urlsafe(40)
    rec["token"]=hash_token(raw);d["tokens"][rec["token"]]=rec;save_access(d)
    r=HTMLResponse(json.dumps({"ok":True,"email":email,"plan":plan}))
    r.set_cookie("save_access_token",raw,max_age=max(86400,int(expires-datetime.now(timezone.utc).timestamp())),httponly=True,secure=True,samesite="lax")
    return r

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    body=await request.body();sig=request.headers.get("stripe-signature")
    try:event=stripe.Webhook.construct_event(body,sig,WEBHOOK_SECRET)
    except Exception:raise HTTPException(400,"Webhook inválido")
    o=event["data"]["object"];typ=event["type"]
    if typ in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        email=(o.get("customer_details") or {}).get("email")
        if email:
            plan="monthly" if o.get("mode")=="subscription" else "daily"
            exp=None
            sub=o.get("subscription")
            if sub:
                try:
                    ss=stripe.Subscription.retrieve(sub);exp=float(ss.current_period_end)
                except:pass
            activate(email,plan,o.get("id",""),sub,exp)
    elif typ in ("customer.subscription.updated","customer.subscription.deleted"):
        email=None
        cid=o.get("customer")
        if cid:
            try:
                c=stripe.Customer.retrieve(cid);email=c.get("email")
            except:pass
        if email:
            d=load_access();rec=d.get("customers",{}).get(email)
            if rec:
                rec["active"]=o.get("status") in ("active","trialing")
                rec["expires"]=float(o.get("current_period_end") or rec.get("expires",0))
                save_access(d)
    return {"received":True}

@app.get("/api/check-access")
def check_access(request:Request,credentials:HTTPBasicCredentials|None=Depends(security)):
    if admin_ok(credentials):return {"ok":True,"type":"admin"}
    a=access_cookie(request)
    if not a:return {"ok":False}
    if a.get("expires") and datetime.now(timezone.utc).timestamp()>a["expires"]:return {"ok":False}
    return {"ok":True,"type":"customer","plan":a.get("plan"),"email":a.get("email")}

@app.post("/api/ficha-tramite")
def ficha(data:DatosTramite,_=Depends(require_access)):return {"ok":True,"datos":data.model_dump()}

@app.post("/api/extraer-pdf")
async def extraer_pdf(request:Request,_=Depends(require_access)):
    form=await request.form();f=form.get("archivo")
    if not f:raise HTTPException(400,"Archivo no recibido")
    content=await f.read()
    return {"ok":True,"nombre":getattr(f,"filename","archivo"),"tamano":len(content),"datos":[]}

@app.post("/api/pregunta")
async def pregunta(req:PreguntaRequest,_=Depends(require_access)):
    if not GEMINI_API_KEY:raise HTTPException(500,"GEMINI_API_KEY no configurada")
    prompt=f"""Eres SAVE MÉXICO AYUDAR. Ayuda de forma clara, sencilla y respetuosa a una persona mexicana en Estados Unidos con trámites y documentos. No inventes requisitos. Si algo depende del consulado o autoridad, dilo claramente. Responde en español sencillo.
Contexto:{req.contexto}
Pregunta:{req.pregunta}"""
    try:
        async with httpx.AsyncClient(timeout=45) as c:
            r=await c.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",params={"key":GEMINI_API_KEY},json={"contents":[{"parts":[{"text":prompt}]}]})
        j=r.json();txt=j["candidates"][0]["content"]["parts"][0]["text"]
        return {"respuesta":txt}
    except Exception as e:raise HTTPException(500,str(e))

@app.post("/api/generar-guia-consular")
def generar_guia(data:DatosTramite,_=Depends(require_access)):
    nombre="guia_"+datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+secrets.token_hex(3)+".pdf"
    path=OUT/nombre;c=canvas.Canvas(str(path),pagesize=LETTER);w,h=LETTER;y=h-50
    def line(txt,size=11,space=18):
        nonlocal y
        if y<55:c.showPage();y=h-50
        c.setFont("Helvetica",size);c.drawString(45,y,str(txt)[:105]);y-=space
    line("SAVE MÉXICO AYUDAR",18,28);line("GUÍA DE PREPARACIÓN DE TRÁMITE",14,25)
    line(f"Trámite: {data.categoria_tramite}",12,22)
    campos=[("Nombre",f"{data.primer_nombre} {data.segundo_nombre} {data.primer_apellido} {data.segundo_apellido}"),("Fecha de nacimiento",data.fecha_nacimiento),("Lugar de nacimiento",data.lugar_nacimiento),("Dirección en EE.UU.",data.direccion_usa),("Teléfono",data.telefono),("Consulado",data.consulado),("Cita",data.cita)]
    for a,b in campos:
        if b:line(f"{a}: {b}")
    line("DOCUMENTOS QUE TIENE",13,22)
    for x in data.documentos_tenidos:line("• "+x)
    line("DOCUMENTOS QUE FALTAN",13,22)
    for x in data.documentos_faltantes:line("• "+x)
    if data.extra_1:line("Información adicional: "+data.extra_1)
    if data.extra_2:line("Información adicional: "+data.extra_2)
    line("Esta guía es una ayuda para organizar información. Los requisitos oficiales pueden cambiar.",9,25)
    c.save();return {"ok":True,"archivo":nombre}

@app.get("/descargar/{nombre}")
def descargar(nombre:str,_=Depends(require_access)):
    p=OUT/Path(nombre).name
    if not p.exists():raise HTTPException(404,"Archivo no encontrado")
    return FileResponse(p,filename=p.name,media_type="application/pdf")

@app.post("/api/resultado-tramite")
def resultado(req:ResultadoRequest,_=Depends(require_access)):
    return {"ok":True,"mensaje":"Resultado guardado","datos":req.model_dump()}

@app.post("/api/logout")
def logout():
    r=HTMLResponse('{"ok":true}')
    r.delete_cookie("save_access_token")
    return r

@app.get("/api/estado")
def estado():return {"ok":True,"app":"SAVE MÉXICO AYUDAR","version":"8.1"}
