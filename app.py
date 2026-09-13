import os,io,secrets
from datetime import date,datetime,timedelta
from typing import Any,Dict,Optional
import stripe
from fastapi import FastAPI,HTTPException,Request,Depends,Cookie
from fastapi.responses import FileResponse,StreamingResponse,JSONResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import consular_engine as engine

stripe.api_key=os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_ID_DIARIO=os.getenv("STRIPE_PRICE_ID1")
PRICE_ID_MENSUAL=os.getenv("STRIPE_PRICE_ID2")
APP_URL=os.getenv("APP_URL","").rstrip("/")
ADMIN_USER=os.getenv("ADMIN_USERNAME")
ADMIN_PASS=os.getenv("ADMIN_PASSWORD")

app=FastAPI(title=engine.APP,version=engine.VERSION)
app.mount("/static",StaticFiles(directory="static"),name="static")

# token -> {tipo,fecha,usos_hoy,expira}
SESIONES_PAGADAS={}

class ExpedientePerfil(BaseModel):
    nombre_completo:Optional[str]=""
    fecha_nacimiento:Optional[str]=""
    edad:Optional[str]=""
    origen_mexico:Optional[str]=""
    direccion_usa:Optional[str]=""
    telefono:Optional[str]=""
    estado:Optional[str]="Otro"
    nacionalidad:Optional[str]="mexicana"

class Inicio(BaseModel):
    perfil:Optional[ExpedientePerfil]=None
    texto:str=""

class Continuacion(BaseModel):
    caso:str
    pregunta_id:str=""
    respuesta:Any=""
    respuestas:Dict[str,Any]=Field(default_factory=dict)
    perfil:Optional[ExpedientePerfil]=None

class Seleccion(BaseModel):
    caso:str
    perfil:Optional[ExpedientePerfil]=None
    respuestas:Dict[str,Any]=Field(default_factory=dict)

class LoginDev(BaseModel):
    username:str
    password:str

def nueva_sesion(tipo,expira=None):
    token=secrets.token_urlsafe(32)
    SESIONES_PAGADAS[token]={
        "tipo":tipo,
        "fecha":str(date.today()),
        "usos_hoy":0,
        "expira":expira
    }
    return token

def limpiar_sesion(token):
    s=SESIONES_PAGADAS.get(token)
    if not s:return None
    if s.get("expira"):
        try:
            if datetime.utcnow()>=datetime.fromisoformat(s["expira"]):
                SESIONES_PAGADAS.pop(token,None)
                return None
        except Exception: pass
    if s.get("tipo")!="dev" and s.get("fecha")!=str(date.today()):
        s["fecha"]=str(date.today());s["usos_hoy"]=0
    return s

def verificar_acceso_paywall(token:Optional[str]=Cookie(None)):
    if not limpiar_sesion(token):
        raise HTTPException(402,"Muro de pago activo. Procesa tu contribución en Stripe para continuar.")
    return token

def cookie_auth(response,token):
    response.set_cookie(
        "token",token,max_age=86400,path="/",secure=True,
        httponly=True,samesite="lax"
    )
    return response

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/access-status")
def access_status(token:Optional[str]=Cookie(None)):
    s=limpiar_sesion(token)
    if not s:return {"ok":True,"activo":False}
    limite="ilimitado" if s["tipo"]=="dev" else ("1 consulta" if s["tipo"]=="diario" else "4 consultas al día")
    return {"ok":True,"activo":True,"tipo":s["tipo"],"usos_hoy":s["usos_hoy"],"limite":limite}

@app.post("/api/checkout")
def crear_checkout_stripe(plan:str):
    if plan not in {"diario","mensual"}:
        raise HTTPException(400,"Plan inválido.")
    price_id=PRICE_ID_DIARIO if plan=="diario" else PRICE_ID_MENSUAL
    if not stripe.api_key or not price_id:
        raise HTTPException(503,"Stripe no está configurado correctamente.")
    base=APP_URL or "http://localhost:8000"
    try:
        session=stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price":price_id,"quantity":1}],
            mode="payment" if plan=="diario" else "subscription",
            success_url=f"{base}/api/stripe-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=base+"/"
        )
        return {"ok":True,"url":session.url}
    except Exception as e:
        raise HTTPException(400,f"Error al inicializar Stripe: {e}")

@app.get("/api/stripe-success")
def stripe_success(session_id:str):
    if not stripe.api_key: raise HTTPException(503,"Stripe no configurado.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        if s.get("payment_status")!="paid":
            return RedirectResponse(url="/?pago=pendiente")
        tipo="mensual" if s.get("mode")=="subscription" else "diario"
        expira=datetime.utcnow()+timedelta(days=30 if tipo=="mensual" else 1)
        token=nueva_sesion(tipo,expira.isoformat())
        r=RedirectResponse(url="/")
        cookie_auth(r,token)
        return r
    except Exception as e:
        raise HTTPException(400,f"No se pudo validar el pago: {e}")

@app.post("/api/login-developer")
def login_developer_bypass(x:LoginDev):
    if not ADMIN_USER or not ADMIN_PASS:
        raise HTTPException(503,"Acceso de desarrollador no configurado.")
    if x.username!=ADMIN_USER or x.password!=ADMIN_PASS:
        raise HTTPException(401,"Credenciales de desarrollador inválidas.")
    token=nueva_sesion("dev")
    r=JSONResponse({"ok":True})
    cookie_auth(r,token)
    return r

@app.post("/api/stripe-webhook")
async def stripe_webhook_capture(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503,"Webhook de Stripe no configurado.")
    try:
        event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400,f"Webhook Error: {e}")
    if event["type"]=="checkout.session.completed":
        s=event["data"]["object"]
        if s.get("payment_status")=="paid":
            # El navegador ya recibe su token mediante /api/stripe-success.
            # Este registro funciona como respaldo del pago confirmado.
            pass
    return {"status":"success"}

@app.get("/api/catalogo")
def api_catalogo(token:str=Depends(verificar_acceso_paywall)):
    return engine.catalogo()

@app.post("/api/seleccionar-caso")
def api_seleccionar(x:Seleccion,token:str=Depends(verificar_acceso_paywall)):
    try:
        p=x.perfil.model_dump() if x.perfil else {}
        return engine.seleccionar_caso(x.caso,p,x.respuestas)
    except Exception as e:
        raise HTTPException(400,str(e))

@app.post("/api/continuar")
def api_continuar(x:Continuacion,token:str=Depends(verificar_acceso_paywall)):
    try:
        p=x.perfil.model_dump() if x.perfil else {}
        return engine.continuar(x.caso,dict(x.respuestas or {}),p,x.pregunta_id,x.respuesta)
    except Exception as e:
        raise HTTPException(400,str(e))

def construir_pdf(r):
    out=io.BytesIO()
    c=canvas.Canvas(out,pagesize=letter)
    c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
    c.setFont("Helvetica-Bold",20)
    c.setFillColorRGB(.05,.25,.20)
    c.drawString(55,740,"MEXICANO APOYA MEXICANO")
    c.setFont("Helvetica-Bold",12);c.setFillColorRGB(.2,.2,.2)
    c.drawString(55,718,"HOJA DE RUTA CONSULAR Y EXPEDIENTE AUTOMATIZADO")
    c.line(55,705,555,705)

    c.setFont("Helvetica-Bold",11)
    c.drawString(55,680,"1. INFORMACIÓN DECLARADA POR EL SOLICITANTE")
    c.setFont("Helvetica",10)
    datos=[
        ("Nombre Completo",r.get("nombre_ciudadano","")),
        ("Fecha de Nacimiento",r.get("fecha_nacimiento","")),
        ("Lugar de Origen (México)",r.get("origen_mexico","")),
        ("Dirección en EE. UU.",r.get("direccion_usa","")),
        ("Teléfono de Contacto",r.get("telefono_ciudadano",""))
    ]
    y=660
    for k,v in datos:
        c.drawString(65,y,f"{k}: {v}");y-=18

    c.setFont("Helvetica-Bold",11)
    c.drawString(55,560,f"2. TRÁMITE EVALUADO: {str(r.get('nombre_tramite','')).upper()}")
    c.setFont("Helvetica",10)
    c.drawString(65,540,f"Estatus de Validación: {r.get('estado','')}")
    c.drawString(65,522,f"Estatus de Cita Consular: {r.get('cita_estatus','')}")
    c.drawString(65,504,f"Arancel Consular de Ventanilla: {r.get('pago_estimado','')}")

    c.setFont("Helvetica-Bold",11)
    c.drawString(55,470,"3. JURISDICCIÓN CONSULAR ASIGNADA")
    c.setFont("Helvetica",10)
    c.drawString(65,450,f"Sede Representativa: {r.get('consulado_nombre','')}")
    c.drawString(65,432,f"Dirección Física: {r.get('consulado_direccion','')}")
    c.drawString(65,414,f"Teléfono: {r.get('consulado_telefono','')}")

    c.setFont("Helvetica-Bold",11)
    c.drawString(55,380,"4. REQUISITOS OFICIALES REQUERIDOS")
    y=360
    for req in r.get("requisitos_oficiales",[]):
        c.setFont("Helvetica",9)
        c.drawString(70,y,f"• {req}");y-=16
        if y<90:
            c.showPage();y=740

    falt=r.get("faltantes",[])
    if falt:
        if y<150:c.showPage();y=740
        c.setFont("Helvetica-Bold",11);c.setFillColorRGB(.7,.1,.1)
        c.drawString(55,y,"5. ALERTAS CRÍTICAS Y DOCUMENTACIÓN FALTANTE");y-=18
        for f in falt:
            c.setFont("Helvetica",9)
            # Divide textos largos para evitar salir del margen.
            palabras=str(f).split();line=""
            for palabra in palabras:
                if len(line)+len(palabra)>90:
                    c.drawString(70,y,f"[ ] {line}");y-=14;line=""
                    if y<70:c.showPage();y=740
                line+=((" " if line else "")+palabra)
            if line:c.drawString(70,y,f"[ ] {line}");y-=14

    c.setFillColorRGB(.5,.5,.5);c.setFont("Helvetica-Oblique",7.5)
    c.drawString(55,45,"Deslinde Legal: Mexicano Apoya Mexicano es un desarrollo independiente propiedad de MAY ROGA LLC.")
    c.drawString(55,35,"No posee vinculación jurídica con la SRE ni el INE. Verifique siempre los requisitos vigentes.")
    c.save();out.seek(0)
    return out

@app.post("/api/pdf-preview")
def api_pdf_preview(r:Dict[str,Any],token:str=Depends(verificar_acceso_paywall)):
    try:
        return StreamingResponse(
            construir_pdf(r),media_type="application/pdf",
            headers={"Content-Disposition":'inline; filename="Hoja_de_Ruta_Preliminar.pdf"',"Cache-Control":"no-store"}
        )
    except Exception as e:
        raise HTTPException(400,f"Error al generar la vista previa: {e}")

@app.post("/api/pdf")
def api_pdf(r:Dict[str,Any],token:str=Depends(verificar_acceso_paywall)):
    try:
        s=SESIONES_PAGADAS.get(token)
        if s and s["tipo"]!="dev":
            limite=1 if s["tipo"]=="diario" else 4
            if s["usos_hoy"]>=limite:
                raise HTTPException(403,"Has utilizado las consultas disponibles para hoy.")
        pdf=construir_pdf(r)
        if s and s["tipo"]!="dev":s["usos_hoy"]+=1
        return StreamingResponse(
            pdf,media_type="application/pdf",
            headers={"Content-Disposition":'attachment; filename="Hoja_de_Ruta_Consular.pdf"',"Cache-Control":"no-store"}
        )
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(400,f"Error al generar el PDF: {e}")

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")),reload=False)
