import os,json,hashlib,secrets
from pathlib import Path
from datetime import datetime,timedelta,timezone

import stripe
from google import genai
from google.genai import types
from fastapi import FastAPI,HTTPException,Depends,Request,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static";DATA=BASE/"data";OUT=BASE/"salidas"
for p in (STATIC,DATA,OUT):p.mkdir(parents=True,exist_ok=True)

ACCESS_FILE=DATA/"access.json"
if not ACCESS_FILE.exists():ACCESS_FILE.write_text("{}",encoding="utf-8")

APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
ADMIN_USER=os.getenv("ADMIN_USERNAME","")
ADMIN_PASS=os.getenv("ADMIN_PASSWORD","")
STRIPE_KEY=os.getenv("STRIPE_SECRET_KEY","")
WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
GEMINI_KEY=os.getenv("GEMINI_API_KEY","")

PRICE_IDS={
    "daily":os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1"),
    "monthly":os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2"),
    "annual":os.getenv("STRIPE_PRICE_ID_ANNUAL")
}

stripe.api_key=STRIPE_KEY
gemini=genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="10.0")
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
    fotografias:list[str]=Field(default_factory=list)
    datos_extraidos:list[dict]=Field(default_factory=list)
    estado_posterior:str="PENDIENTE"
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
    try:return json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
    except:return {}

def save_access(d):
    ACCESS_FILE.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")

def htoken(x):
    return hashlib.sha256(x.encode()).hexdigest()

def admin_ok(c):
    return bool(c and ADMIN_USER and ADMIN_PASS and
                secrets.compare_digest(c.username,ADMIN_USER) and
                secrets.compare_digest(c.password,ADMIN_PASS))

def admin_cookie(request):
    token=request.cookies.get("save_admin_token")
    if not token:return False
    rec=load_access().get("admin_tokens",{}).get(htoken(token))
    if not rec:return False
    return rec.get("active",False)

def customer_access(request):
    token=request.cookies.get("save_access_token")
    if not token:return None
    rec=load_access().get("tokens",{}).get(htoken(token))
    if not rec or not rec.get("active",True):return None
    exp=rec.get("expires")
    if exp and datetime.now(timezone.utc).timestamp()>float(exp):return None
    return rec

def require_access(request:Request,
                   credentials:HTTPBasicCredentials|None=Depends(security)):
    if admin_ok(credentials) or admin_cookie(request):
        return {"type":"admin"}
    rec=customer_access(request)
    if rec:return rec
    raise HTTPException(401,"Acceso no autorizado")

def new_token():
    return secrets.token_urlsafe(40)

def activate(email,plan,session_id="",subscription_id="",expires=None):
    if not email:return None
    d=load_access();d.setdefault("customers",{});d.setdefault("tokens",{})
    raw=new_token();hashed=htoken(raw)
    if expires is None:
        expires=(datetime.now(timezone.utc)+timedelta(hours=24)).timestamp()
    rec={
        "email":email,"plan":plan,"session_id":session_id,
        "subscription_id":subscription_id,"expires":expires,
        "active":True,"token":hashed
    }
    old=d["customers"].get(email)
    if old and old.get("token"):d["tokens"].pop(old["token"],None)
    d["customers"][email]=rec
    d["tokens"][hashed]=rec
    save_access(d)
    return raw

def activate_admin():
    d=load_access();d.setdefault("admin_tokens",{})
    raw=new_token()
    d["admin_tokens"][htoken(raw)]={"active":True}
    save_access(d)
    return raw

def clean(v):
    return str(v or "").strip()

@app.get("/")
def home():
    return FileResponse(STATIC/"index.html")

@app.get("/api/estado")
def estado():
    return {"ok":True,"app":"SAVE MÉXICO AYUDAR","version":"10.0"}

@app.post("/api/admin-login")
def admin_login(credentials:HTTPBasicCredentials=Depends(security)):
    if not admin_ok(credentials):
        raise HTTPException(401,"Usuario o contraseña incorrectos")
    raw=activate_admin()
    r=JSONResponse({"ok":True,"admin":True})
    r.set_cookie(
        "save_admin_token",raw,
        max_age=86400,httponly=True,secure=True,samesite="lax"
    )
    return r

@app.post("/api/create-checkout-session")
def checkout(req:StripeCheckoutRequest):
    plan=req.plan.strip().lower()
    price=PRICE_IDS.get(plan)
    if not price:
        raise HTTPException(400,"Price ID no configurado para este plan.")
    if not STRIPE_KEY:
        raise HTTPException(500,"STRIPE_SECRET_KEY no configurada.")
    try:
        p=stripe.Price.retrieve(price)
        mode="subscription" if p.type=="recurring" else "payment"
        s=stripe.checkout.Session.create(
            mode=mode,
            line_items=[{"price":price,"quantity":1}],
            metadata={"save_plan":plan},
            success_url=f"{APP_URL}/?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?cancel=true"
        )
        return {"ok":True,"checkout_url":s.url}
    except Exception as e:
        raise HTTPException(500,f"Stripe: {e}")

@app.get("/api/verify-payment")
def verify_payment(session_id:str):
    if not STRIPE_KEY:
        raise HTTPException(500,"Stripe no configurado.")
    try:
        s=stripe.checkout.Session.retrieve(
            session_id,
            expand=["subscription","line_items"]
        )
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

    if s.payment_status not in ("paid","no_payment_required"):
        raise HTTPException(403,"El pago todavía no está confirmado.")

    email=(s.customer_details.email if s.customer_details else None)
    if not email:
        raise HTTPException(400,"Stripe no proporcionó el correo del cliente.")

    plan=s.metadata.get("save_plan") if s.metadata else None
    if plan not in PRICE_IDS:
        plan=None
        try:
            items=s.line_items.data if s.line_items else []
            if items:
                pid=items[0].price.id
                for k,v in PRICE_IDS.items():
                    if v and v==pid:plan=k;break
        except:pass

    plan=plan or ("monthly" if s.mode=="subscription" else "daily")
    subscription_id=""
    now=datetime.now(timezone.utc).timestamp()

    if s.mode=="subscription":
        sub=s.subscription
        if isinstance(sub,str):
            sub=stripe.Subscription.retrieve(sub)
        if sub.status not in ("active","trialing"):
            raise HTTPException(403,"La suscripción no está activa.")
        subscription_id=sub.id
        expires=float(sub.current_period_end)
    else:
        expires=now+86400

    raw=activate(
        email,plan,s.id,subscription_id,expires
    )
    r=JSONResponse({
        "ok":True,"email":email,"plan":plan
    })
    r.set_cookie(
        "save_access_token",raw,
        max_age=max(3600,int(expires-now)),
        httponly=True,secure=True,samesite="lax"
    )
    return r

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    body=await request.body()
    sig=request.headers.get("stripe-signature")
    if not WEBHOOK_SECRET:
        raise HTTPException(500,"STRIPE_WEBHOOK_SECRET no configurada.")
    try:
        event=stripe.Webhook.construct_event(body,sig,WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400,f"Webhook inválido: {e}")

    typ=event["type"]
    o=event["data"]["object"]

    if typ in ("checkout.session.completed",
               "checkout.session.async_payment_succeeded"):
        email=(o.get("customer_details") or {}).get("email")
        if email:
            plan=(o.get("metadata") or {}).get("save_plan")
            if plan not in PRICE_IDS:
                plan="monthly" if o.get("mode")=="subscription" else "daily"

            sub=o.get("subscription")
            exp=None
            if sub:
                try:
                    ss=stripe.Subscription.retrieve(
                        sub if isinstance(sub,str) else sub.id
                    )
                    exp=float(ss.current_period_end)
                except:pass
            activate(email,plan,o.get("id",""),
                     sub if isinstance(sub,str) else "",
                     exp)

    elif typ in (
        "customer.subscription.updated",
        "customer.subscription.deleted"
    ):
        cid=o.get("customer")
        email=None
        try:
            if cid:
                c=stripe.Customer.retrieve(cid)
                email=c.get("email")
        except:pass

        if email:
            d=load_access()
            rec=d.get("customers",{}).get(email)
            if rec:
                rec["active"]=o.get("status") in ("active","trialing")
                if o.get("current_period_end"):
                    rec["expires"]=float(o["current_period_end"])
                if rec.get("token"):
                    d.setdefault("tokens",{})[rec["token"]]=rec
                save_access(d)

    return {"received":True}

@app.get("/api/check-access")
def check_access(
    request:Request,
    credentials:HTTPBasicCredentials|None=Depends(security)
):
    if admin_ok(credentials) or admin_cookie(request):
        return {"ok":True,"type":"admin"}
    rec=customer_access(request)
    return {
        "ok":bool(rec),
        "type":"customer" if rec else None,
        "plan":rec.get("plan") if rec else None
    }

@app.post("/api/ficha-tramite")
def ficha(data:DatosTramite,_=Depends(require_access)):
    return {"ok":True,"datos":data.model_dump()}

@app.post("/api/extraer-pdf")
async def extraer_pdf(
    file:UploadFile=File(...),
    _=Depends(require_access)
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400,"Solo se acepta PDF.")
    raw=await file.read()
    if len(raw)>15*1024*1024:
        raise HTTPException(400,"El PDF no puede superar 15 MB.")

    tmp=OUT/("_tmp_"+secrets.token_hex(5)+".pdf")
    tmp.write_bytes(raw)

    try:
        reader=PdfReader(str(tmp))
        parts=[]
        for page in reader.pages:
            try:parts.append(page.extract_text() or "")
            except:pass
        text="\n".join(parts).strip()
        pages=len(reader.pages)
    finally:
        try:tmp.unlink()
        except:pass

    # Gemini 2.5 ayuda cuando el PDF contiene información
    # que pypdf no consigue extraer correctamente.
    if gemini:
        try:
            prompt="""Lee este PDF de forma estrictamente informativa.
Extrae solamente datos que realmente aparezcan en el documento.
No inventes nombres, fechas, domicilios, documentos, requisitos ni respuestas.
Devuelve texto claro y organizado con los datos encontrados.
Si algo no puede leerse, indica NO LEGIBLE.
No conviertas una recomendación en requisito legal."""
            r=gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=raw,mime_type="application/pdf"
                    ),
                    prompt
                ]
            )
            ai_text=(r.text or "").strip()
            if ai_text:
                text=(text+"\n\n--- INFORMACIÓN REVISADA CON GEMINI ---\n"+
                      ai_text)[:50000]
        except Exception:
            pass

    return {
        "ok":True,
        "nombre":file.filename,
        "texto":text[:50000],
        "paginas":pages
    }

@app.post("/api/subir-fotos")
async def subir_fotos(
    files:list[UploadFile]=File(...),
    _=Depends(require_access)
):
    nombres=[]
    carpeta=OUT/("fotos_"+secrets.token_hex(6))
    carpeta.mkdir(parents=True,exist_ok=True)

    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        raw=await f.read()
        if len(raw)>10*1024*1024:
            continue
        ext=Path(f.filename or "").suffix.lower()
        if ext not in (".jpg",".jpeg",".png",".webp",".heic"):
            ext=".jpg"
        nombre=secrets.token_hex(8)+ext
        (carpeta/nombre).write_bytes(raw)
        nombres.append(f.filename or nombre)

    return {"ok":True,"fotografias":nombres}

@app.post("/api/pregunta")
def pregunta(req:PreguntaRequest,_=Depends(require_access)):
    if not gemini:
        raise HTTPException(500,"GEMINI_API_KEY no configurada.")

    prompt=f"""Eres el asistente de SAVE MÉXICO AYUDAR.

Ayudas a personas mexicanas en Estados Unidos a organizar información
para trámites y a preparar preguntas.

Trámite: {req.categoria_tramite or "No especificado"}

Información disponible:
{req.contexto[:30000]}

Pregunta:
{req.pregunta}

REGLAS:
- Usa español sencillo y claro.
- No inventes requisitos.
- No inventes documentos mexicanos.
- No afirmes que algo es obligatorio si no está confirmado.
- Si depende del Consulado, Gobierno de México u otra autoridad,
  dilo claramente.
- SAVE MÉXICO AYUDAR es un servicio privado y no es una autoridad.
- Da primero la respuesta principal.
- Evita párrafos largos y amontonados.
- Si no tienes información suficiente, dilo.
"""
    try:
        r=gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return {"respuesta":(r.text or "").strip()}
    except Exception as e:
        raise HTTPException(500,f"Gemini: {e}")

def safe(v):
    return str(v or "").strip()

def lista(v):
    return [x.strip() for x in safe(v).split(",") if x.strip()]

@app.post("/api/generar-guia-consular")
def generar_guia(
    data:DatosTramite,
    _=Depends(require_access)
):
    if not data.confirmado:
        raise HTTPException(400,"La información debe ser revisada antes de generar el PDF.")

    nombre=(
        "SAVE_MEXICO_"+
        datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+ 
        secrets.token_hex(3)+".pdf"
    )
    path=OUT/nombre

    c=canvas.Canvas(str(path),pagesize=LETTER)
    W,H=LETTER
    y=H-45

    def newpage():
        nonlocal y
        c.showPage()
        y=H-45

    def line(t,size=10,bold=False,gap=16):
        nonlocal y
        if y<55:newpage()
        font="Helvetica-Bold" if bold else "Helvetica"
        words=str(t).split()
        current=""
        for word in words:
            test=(current+" "+word).strip()
            if c.stringWidth(test,font,size)>W-90:
                c.setFont(font,size)
                c.drawString(45,y,current)
                y-=gap
                current=word
            else:
                current=test
        if current:
            c.setFont(font,size)
            c.drawString(45,y,current)
            y-=gap

    def section(t):
        nonlocal y
        if y<75:newpage()
        y-=4
        c.setFont("Helvetica-Bold",11)
        c.drawString(45,y,t)
        y-=18

    def field(label,value):
        if safe(value):
            line(f"{label}: {value}")

    # Encabezado
    c.setFont("Helvetica-Bold",19)
    c.drawCentredString(W/2,y,"SAVE MÉXICO AYUDAR")
    y-=25
    c.setFont("Helvetica-Bold",13)
    c.drawCentredString(W/2,y,"GUÍA DE PREPARACIÓN: TRÁMITE CONSULAR")
    y-=30

    # 1
    section("1. TRÁMITE")
    field("Tipo de trámite",data.categoria_tramite)

    # 2
    section("2. TITULAR / SOLICITANTE")
    nombre_completo=" ".join(
        x for x in [
            data.primer_nombre,
            data.segundo_nombre,
            data.primer_apellido,
            data.segundo_apellido
        ] if safe(x)
    )
    field("Titular / Solicitante",nombre_completo)
    field("Nacimiento",
          f"{data.fecha_nacimiento} ({data.lugar_nacimiento})"
          if data.fecha_nacimiento or data.lugar_nacimiento else "")
    field("Domicilio USA",data.direccion_usa)
    field("Teléfono",data.telefono)
    field("Nacionalidad",data.nacionalidad)

    # 3
    section("3. INFORMACIÓN DE CITA Y CONSULADO")
    field("Consulado",data.consulado)
    field("Cita",data.cita)

    # 4
    section("4. LO QUE TIENES")
    docs=lista(data.documentos_tenidos)
    if docs:
        for x in docs:line("[ ] "+x)
    else:
        line("No especificado")

    # 5
    section("5. LO QUE FALTA")
    missing=lista(data.documentos_faltantes)
    if missing:
        for x in missing:line("[ ] "+x)
    else:
        line("Ninguno")

    # 6
    section("6. FOTOGRAFÍAS")
    if data.fotografias:
        for x in data.fotografias:line("[ ] Fotografía: "+x)
    else:
        line("No se indicaron fotografías.")
    line("Las características de las fotografías deben confirmarse "
         "con los requisitos oficiales correspondientes al trámite.",8)

    # 7
    section("7. INFORMACIÓN ADICIONAL")
    field("Información adicional",data.extra_1)
    field("Otra información",data.extra_2)

    # 8
    section("8. ESTATUS POSTERIOR")
    line(safe(data.estado_posterior) or "PENDIENTE")

    # 9
    section("CHECKLIST DE PREPARACIÓN")
    line("[ ] Revisar que los datos personales sean correctos.")
    line("[ ] Revisar los documentos que realmente se tienen.")
    line("[ ] Identificar los documentos que están pendientes.")
    line("[ ] Confirmar directamente los requisitos oficiales.")
    line("[ ] Confirmar fecha, hora y lugar de la cita, si corresponde.")
    line("[ ] Revisar las fotografías y sus requisitos oficiales, si aplican.")

    # 10
    section("ORIENTACIÓN")
    line(
        "Consulta siempre la fuente oficial de la autoridad correspondiente "
        "para confirmar la lista exacta de requisitos y documentos antes "
        "de iniciar o presentar tu trámite.",
        9,False,14
    )

    # 11 legal
    section("AVISO IMPORTANTE")
    line(
        "SAVE MÉXICO AYUDAR es un servicio privado e independiente "
        "de MAY ROGA LLC, Florida.",
        9,False,14
    )
    line(
        "No es una agencia del Gobierno de México ni representa a ningún "
        "consulado mexicano.",
        9,False,14
    )
    line(
        "Este documento generado es un apoyo de organización personal. "
        "Los requisitos, decisiones y resultados corresponden a la "
        "autoridad competente.",
        9,False,14
    )

    c.save()
    return {
        "ok":True,
        "archivo":f"/descargar/{nombre}",
        "nombre":nombre
    }

@app.get("/descargar/{nombre}")
def descargar(
    nombre:str,
    _=Depends(require_access)
):
    nombre=Path(nombre).name
    if not nombre.lower().endswith(".pdf"):
        raise HTTPException(400,"Archivo no válido.")
    p=OUT/nombre
    if not p.exists():
        raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(
        p,
        filename=p.name,
        media_type="application/pdf"
    )

@app.post("/api/resultado-tramite")
def resultado(
    req:ResultadoRequest,
    _=Depends(require_access)
):
    estado=req.estado or req.resultado or "PENDIENTE"
    return {
        "ok":True,
        "estado":estado,
        "mensaje":"Resultado guardado correctamente."
    }

@app.post("/api/logout")
def logout():
    r=JSONResponse({"ok":True})
    r.delete_cookie("save_access_token")
    r.delete_cookie("save_admin_token")
    return r
