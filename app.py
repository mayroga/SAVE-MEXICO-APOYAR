import os,json,secrets,uuid,re
from datetime import datetime
from pathlib import Path
import stripe
from fastapi import FastAPI,HTTPException,Request,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static"
DATA=BASE/"data"
OUT=BASE/"out"
TRAMITES=DATA/"tramites.json"
OUT.mkdir(exist_ok=True)
STATIC.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
PRICE_DAILY=os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1","")
PRICE_MONTHLY=os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2","")
PRICE_ANNUAL=os.getenv("STRIPE_PRICE_ID_ANNUAL","")

if STRIPE_SECRET_KEY:
    stripe.api_key=STRIPE_SECRET_KEY

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="3.0.0")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")

ADMIN_TOKENS=set()
ACCESS_TOKENS=set()

class Login(BaseModel):
    username:str
    password:str

class Checkout(BaseModel):
    plan:str

class Guide(BaseModel):
    tramite:str
    modalidad:str=""
    datos_personales:dict={}
    datos_especificos:dict={}
    documentos:dict={}
    documentos_disponibles:list=[]
    documentos_faltantes:list=[]
    documentos_dudosos:list=[]
    idioma:str="es"

def load_data():
    if not TRAMITES.exists():
        raise HTTPException(500,"No existe data/tramites.json.")
    try:
        return json.loads(TRAMITES.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(500,f"No se pudo leer tramites.json: {e}")

def get_tramites():
    return load_data().get("tramites",{})

def get_tramite(tid):
    t=get_tramites().get(tid)
    if not t:
        raise HTTPException(404,"Trámite no encontrado.")
    return t

def get_modalidad(tid,mid):
    t=get_tramite(tid)
    m=t.get("modalidades",{}).get(mid)
    if not m:
        raise HTTPException(404,"Modalidad no encontrada.")
    return m

def new_token(store):
    token=secrets.token_urlsafe(32)
    store.add(token)
    return token

def cookie_access(request:Request):
    admin=request.cookies.get("save_admin_token")
    paid=request.cookies.get("save_access_token")
    return (admin in ADMIN_TOKENS),(paid in ACCESS_TOKENS)

def require_access(request:Request):
    admin,paid=cookie_access(request)
    if not(admin or paid):
        raise HTTPException(401,"Se requiere acceso autorizado.")
    return True

def clean_name(name):
    return re.sub(r"[^A-Za-z0-9._-]","_",name)[:120]

def pdf_line(c,text,x,y,width=500,size=10,leading=14):
    c.setFont("Helvetica",size)
    lines=simpleSplit(str(text), "Helvetica", size, width)
    for line in lines:
        if y<55:
            c.showPage()
            y=LETTER[1]-55
            c.setFont("Helvetica",size)
        c.drawString(x,y,line)
        y-=leading
    return y

def pdf_section(c,title,y):
    if y<85:
        c.showPage()
        y=LETTER[1]-55
    c.setFont("Helvetica-Bold",12)
    c.drawString(45,y,title)
    return y-19

def make_pdf(g:Guide):
    t=get_tramite(g.tramite)
    m=get_modalidad(g.tramite,g.modalidad)
    nombre=t.get("nombre",g.tramite)
    modalidad=m.get("nombre",g.modalidad)
    now=datetime.now().strftime("%Y-%m-%d %H:%M")
    filename=f"guia_{g.tramite}_{g.modalidad}_{uuid.uuid4().hex[:10]}.pdf"
    path=OUT/clean_name(filename)
    c=canvas.Canvas(str(path),pagesize=LETTER)
    y=LETTER[1]-50

    c.setTitle(f"SAVE MÉXICO AYUDAR - {nombre}")
    c.setFont("Helvetica-Bold",18)
    c.drawString(45,y,"SAVE MÉXICO AYUDAR")
    y-=25
    c.setFont("Helvetica-Bold",14)
    y=pdf_line(c,nombre,45,y,500,14,18)
    y=pdf_line(c,f"Modalidad: {modalidad}",45,y-3,500,10,14)
    y=pdf_line(c,f"Preparado: {now}",45,y-2,500,9,13)
    y-=8

    y=pdf_section(c,"1. DATOS PERSONALES",y)
    if g.datos_personales:
        for k,v in g.datos_personales.items():
            if v not in ("",None):
                y=pdf_line(c,f"{k.replace('_',' ').title()}: {v}",55,y,480,10,14)
    else:
        y=pdf_line(c,"No se proporcionaron datos personales.",55,y,480)

    y-=5
    y=pdf_section(c,"2. INFORMACIÓN ESPECÍFICA DEL TRÁMITE",y)
    if g.datos_especificos:
        preguntas={x.get("id"):x for x in m.get("preguntas",[])}
        for k,v in g.datos_especificos.items():
            texto=preguntas.get(k,{}).get("texto",k.replace("_"," ").title())
            y=pdf_line(c,f"{texto}",55,y,480,10,14)
            y=pdf_line(c,f"Respuesta: {v if v not in ('',None) else 'Sin respuesta'}",70,y,465,10,14)
            y-=2
    else:
        y=pdf_line(c,"No se proporcionaron respuestas adicionales.",55,y,480)

    y-=5
    y=pdf_section(c,"3. DOCUMENTOS CORRESPONDIENTES",y)
    docs=m.get("documentos",[])
    if docs:
        for d in docs:
            y=pdf_line(c,f"• {d}",55,y,480,10,14)
    else:
        y=pdf_line(c,"POR CONFIRMAR CON LA AUTORIDAD.",55,y,480,10,14)

    y-=5
    y=pdf_section(c,"4. DOCUMENTOS QUE LA PERSONA DECLARA TENER",y)
    if g.documentos_disponibles:
        for d in g.documentos_disponibles:
            y=pdf_line(c,f"• {d}",55,y,480,10,14)
    else:
        y=pdf_line(c,"Ninguno marcado como disponible.",55,y,480)

    y-=5
    y=pdf_section(c,"5. DOCUMENTOS QUE LA PERSONA DECLARA NO TENER",y)
    if g.documentos_faltantes:
        for d in g.documentos_faltantes:
            y=pdf_line(c,f"• {d}",55,y,480,10,14)
    else:
        y=pdf_line(c,"Ninguno marcado como faltante.",55,y,480)

    y-=5
    y=pdf_section(c,"6. DOCUMENTOS SOBRE LOS QUE TIENE DUDA",y)
    if g.documentos_dudosos:
        for d in g.documentos_dudosos:
            y=pdf_line(c,f"• {d}",55,y,480,10,14)
    else:
        y=pdf_line(c,"Ninguno marcado como dudoso.",55,y,480)

    especiales=m.get("casos_especiales",[])
    if especiales:
        y-=5
        y=pdf_section(c,"7. SITUACIONES ESPECIALES A CONSIDERAR",y)
        for x in especiales:
            y=pdf_line(c,f"• {x}",55,y,480,10,14)

    pdf=m.get("pdf",{})
    secciones=pdf.get("secciones",[])
    if secciones:
        y-=5
        y=pdf_section(c,"8. INFORMACIÓN ESPECÍFICA DE ESTA MODALIDAD",y)
        for x in secciones:
            y=pdf_line(c,f"• {x}",55,y,480,10,14)

    y-=5
    y=pdf_section(c,"9. ADVERTENCIAS IMPORTANTES",y)
    warnings=[
        "Esta guía organiza la información proporcionada por la persona usuaria.",
        "La guía NO sustituye las instrucciones del Consulado de México ni del INE.",
        "Los requisitos, costos, citas, documentos aceptados y procedimientos pueden cambiar.",
        "Cuando exista una duda o un requisito dependiente del Consulado, debe confirmarse directamente con la autoridad.",
        "La generación de este PDF no garantiza la aceptación ni aprobación del trámite."
    ]
    for x in warnings:
        y=pdf_line(c,f"• {x}",55,y,480,10,14)

    y-=5
    y=pdf_section(c,"10. FUENTES OFICIALES",y)
    fuentes=t.get("fuentes",[])
    if fuentes:
        for x in fuentes:
            y=pdf_line(c,f"• {x}",55,y,480,10,14)
    else:
        y=pdf_line(c,"POR CONFIRMAR CON LA AUTORIDAD.",55,y,480)

    y-=10
    y=pdf_line(c,"Documento generado por SAVE MÉXICO AYUDAR.",45,y,500,8,11)
    y=pdf_line(c,"La información oficial debe verificarse antes de acudir al trámite.",45,y,500,8,11)
    c.save()
    return path

@app.get("/")
async def home():
    p=STATIC/"index.html"
    if not p.exists():
        raise HTTPException(404,"No existe static/index.html.")
    return FileResponse(str(p))

@app.get("/api/check-access")
async def check_access(request:Request):
    admin,paid=cookie_access(request)
    return {"access":bool(admin or paid),"admin":admin,"paid":paid}

@app.post("/api/admin-login")
async def admin_login(data:Login):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(503,"El acceso administrativo no está configurado.")
    if not secrets.compare_digest(data.username,ADMIN_USERNAME) or not secrets.compare_digest(data.password,ADMIN_PASSWORD):
        raise HTTPException(401,"Usuario o contraseña incorrectos.")
    token=new_token(ADMIN_TOKENS)
    r=JSONResponse({"ok":True,"access":True,"admin":True,"message":"Acceso administrativo autorizado."})
    r.set_cookie("save_admin_token",token,httponly=True,secure=True,samesite="lax",max_age=86400)
    return r

@app.post("/api/create-checkout-session")
async def create_checkout_session(data:Checkout,request:Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503,"Stripe no está configurado.")
    prices={"daily":PRICE_DAILY,"monthly":PRICE_MONTHLY,"annual":PRICE_ANNUAL}
    price=prices.get(data.plan)
    if not price:
        raise HTTPException(400,"Plan de pago no configurado.")
    try:
        session=stripe.checkout.Session.create(
            mode="subscription" if data.plan in ("monthly","annual") else "payment",
            line_items=[{"price":price,"quantity":1}],
            success_url=f"{APP_URL}/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?payment=cancelled",
            metadata={"plan":data.plan,"app":"save_mexico_ayudar"},
            allow_promotion_codes=True
        )
        return {"ok":True,"id":session.id,"url":session.url}
    except Exception as e:
        raise HTTPException(500,f"No se pudo crear el pago: {e}")

@app.get("/api/verify-payment")
async def verify_payment(session_id:str,request:Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503,"Stripe no está configurado.")
    if not session_id:
        raise HTTPException(400,"Falta session_id.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        paid=s.get("payment_status")=="paid"
        status=s.get("status")
        if not paid or status!="complete":
            return {"access":False,"paid":False,"status":status,"payment_status":s.get("payment_status")}
        token=new_token(ACCESS_TOKENS)
        r=JSONResponse({"access":True,"paid":True,"status":"complete"})
        r.set_cookie("save_access_token",token,httponly=True,secure=True,samesite="lax",max_age=86400)
        return r
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    payload=await request.body()
    signature=request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503,"Webhook de Stripe no configurado.")
    try:
        event=stripe.Webhook.construct_event(payload,signature,STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400,"Webhook inválido.")
    event_type=event.get("type","")
    if event_type in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        session=event["data"]["object"]
        if session.get("payment_status")=="paid":
            return {"received":True,"paid":True}
    return {"received":True}

@app.get("/api/tramites")
async def tramites(request:Request):
    require_access(request)
    data=get_tramites()
    result=[]
    for tid,t in data.items():
        result.append({
            "id":tid,
            "nombre":t.get("nombre",tid),
            "nombre_corto":t.get("nombre_corto",t.get("nombre",tid)),
            "autoridad":t.get("autoridad","")
        })
    return {"tramites":result}

@app.get("/api/modalidades")
async def modalidades(tramite:str,request:Request):
    require_access(request)
    t=get_tramite(tramite)
    result=[]
    for mid,m in t.get("modalidades",{}).items():
        result.append({
            "id":mid,
            "nombre":m.get("nombre",mid),
            "descripcion":m.get("descripcion","")
        })
    return {"tramite":tramite,"modalidades":result}

@app.get("/api/ficha-tramite")
async def ficha_tramite(tramite:str,request:Request,modalidad:str|None=None):
    require_access(request)
    t=get_tramite(tramite)
    if modalidad:
        m=get_modalidad(tramite,modalidad)
        return {
            "tramite":tramite,
            "nombre":t.get("nombre",tramite),
            "autoridad":t.get("autoridad",""),
            "modalidad":modalidad,
            "ficha":m,
            "fuentes":t.get("fuentes",[])
        }
    mods={}
    for mid,m in t.get("modalidades",{}).items():
        mods[mid]={
            "nombre":m.get("nombre",mid),
            "descripcion":m.get("descripcion","")
        }
    return {
        "tramite":tramite,
        "nombre":t.get("nombre",tramite),
        "autoridad":t.get("autoridad",""),
        "modalidades":mods,
        "fuentes":t.get("fuentes",[])
    }

@app.get("/api/perfil-tramite")
async def perfil_tramite(tramite:str,request:Request,modalidad:str|None=None):
    require_access(request)
    t=get_tramite(tramite)
    if modalidad:
        m=get_modalidad(tramite,modalidad)
        return {
            "tramite":tramite,
            "nombre":t.get("nombre",tramite),
            "modalidad":modalidad,
            "modalidad_nombre":m.get("nombre",modalidad),
            "autoridad":t.get("autoridad",""),
            "costo":t.get("costo",""),
            "vigencia":t.get("vigencia",""),
            "cita":t.get("cita",""),
            "fuentes":t.get("fuentes",[])
        }
    return {
        "tramite":tramite,
        "nombre":t.get("nombre",tramite),
        "autoridad":t.get("autoridad",""),
        "costo":t.get("costo",""),
        "vigencia":t.get("vigencia",""),
        "cita":t.get("cita",""),
        "modalidades":{
            k:v.get("nombre",k) for k,v in t.get("modalidades",{}).items()
        },
        "fuentes":t.get("fuentes",[])
    }

@app.get("/api/pregunta")
async def pregunta(tramite:str,modalidad:str,numero:int,request:Request):
    require_access(request)
    m=get_modalidad(tramite,modalidad)
    preguntas=m.get("preguntas",[])
    if numero<0 or numero>=len(preguntas):
        raise HTTPException(404,"Pregunta no encontrada.")
    return {"numero":numero,"total":len(preguntas),"pregunta":preguntas[numero]}

@app.post("/api/resultado-tramite")
async def resultado_tramite(payload:dict,request:Request):
    require_access(request)
    tramite=payload.get("tramite")
    modalidad=payload.get("modalidad")
    if not tramite or not modalidad:
        raise HTTPException(400,"Faltan trámite o modalidad.")
    m=get_modalidad(tramite,modalidad)
    docs=m.get("documentos",[])
    respuestas=payload.get("datos_especificos",{})
    disponibles=payload.get("documentos_disponibles",[])
    faltantes=payload.get("documentos_faltantes",[])
    dudosos=payload.get("documentos_dudosos",[])
    return {
        "tramite":tramite,
        "modalidad":modalidad,
        "modalidad_nombre":m.get("nombre",modalidad),
        "documentos_correspondientes":docs,
        "documentos_disponibles":disponibles,
        "documentos_faltantes":faltantes,
        "documentos_dudosos":dudosos,
        "respuestas":respuestas,
        "casos_especiales":m.get("casos_especiales",[]),
        "pdf":m.get("pdf",{})
    }

@app.post("/api/generar-guia-consular")
async def generar_guia(g:Guide,request:Request):
    require_access(request)
    if g.tramite not in get_tramites():
        raise HTTPException(404,"Trámite no encontrado.")
    if g.modalidad not in get_tramite(g.tramite).get("modalidades",{}):
        raise HTTPException(404,"Modalidad no encontrada.")
    try:
        path=make_pdf(g)
        return {
            "ok":True,
            "filename":path.name,
            "file":path.name,
            "download":f"/descargar/{path.name}"
        }
    except Exception as e:
        raise HTTPException(500,f"No se pudo generar el PDF: {e}")

@app.post("/api/extraer-pdf")
async def extraer_pdf(request:Request,file:UploadFile=File(...)):
    require_access(request)
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400,"El archivo debe ser PDF.")
    raw=await file.read()
    if len(raw)>15*1024*1024:
        raise HTTPException(400,"El PDF supera el tamaño permitido.")
    temp=OUT/f"tmp_{uuid.uuid4().hex}.pdf"
    try:
        temp.write_bytes(raw)
        reader=PdfReader(str(temp))
        text="\n".join((p.extract_text() or "") for p in reader.pages)
        return {"ok":True,"filename":file.filename,"pages":len(reader.pages),"text":text[:100000]}
    except Exception as e:
        raise HTTPException(400,f"No se pudo leer el PDF: {e}")
    finally:
        try:temp.unlink(missing_ok=True)
        except Exception:pass

@app.post("/api/subir-fotos")
async def subir_fotos(request:Request,files:list[UploadFile]=File(...)):
    require_access(request)
    saved=[]
    allowed={".jpg",".jpeg",".png",".webp"}
    for f in files[:10]:
        ext=Path(f.filename or "").suffix.lower()
        if ext not in allowed:
            continue
        raw=await f.read()
        if len(raw)>8*1024*1024:
            continue
        name=f"foto_{uuid.uuid4().hex}{ext}"
        path=OUT/name
        path.write_bytes(raw)
        saved.append(name)
    return {"ok":True,"files":saved}

@app.get("/descargar/{nombre}")
async def descargar(nombre:str,request:Request):
    require_access(request)
    safe=Path(nombre).name
    path=OUT/safe
    if not path.exists() or path.suffix.lower()!=".pdf":
        raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=safe,
        headers={"Content-Disposition":f'attachment; filename="{safe}"'}
    )

@app.get("/api/fuentes")
async def fuentes(request:Request,tramite:str|None=None):
    require_access(request)
    if tramite:
        t=get_tramite(tramite)
        return {"tramite":tramite,"fuentes":t.get("fuentes",[])}
    data=load_data()
    return {
        "fuentes_generales":data.get("fuentes_oficiales",{}),
        "nota":data.get("nota_general","")
    }

@app.post("/api/logout")
async def logout(request:Request):
    a=request.cookies.get("save_admin_token")
    p=request.cookies.get("save_access_token")
    if a:ADMIN_TOKENS.discard(a)
    if p:ACCESS_TOKENS.discard(p)
    r=JSONResponse({"ok":True})
    r.delete_cookie("save_admin_token")
    r.delete_cookie("save_access_token")
    return r

@app.get("/health")
async def health():
    return {
        "ok":True,
        "app":"SAVE MÉXICO AYUDAR",
        "version":"3.0.0",
        "tramites":list(get_tramites().keys()),
        "stripe":bool(STRIPE_SECRET_KEY)
    }

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))

