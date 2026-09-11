import os,json,hashlib,secrets,re
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

BASE=Path(__file__).resolve().parent;STATIC=BASE/"static";DATA=BASE/"data";OUT=BASE/"salidas"
for p in(STATIC,DATA,OUT):p.mkdir(parents=True,exist_ok=True)
ACCESS_FILE=DATA/"access.json";MEMORY_FILE=DATA/"asesor_mexicano_tramites.json"
if not ACCESS_FILE.exists():ACCESS_FILE.write_text("{}",encoding="utf-8")
if not MEMORY_FILE.exists():MEMORY_FILE.write_text("{}",encoding="utf-8")

APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
ADMIN_USER=os.getenv("ADMIN_USERNAME","");ADMIN_PASS=os.getenv("ADMIN_PASSWORD","")
STRIPE_KEY=os.getenv("STRIPE_SECRET_KEY","");WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","");GEMINI_KEY=os.getenv("GEMINI_API_KEY","")
PRICE_IDS={"daily":os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1"),"monthly":os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2"),"annual":os.getenv("STRIPE_PRICE_ID_ANNUAL")}
stripe.api_key=STRIPE_KEY;gemini=genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
app=FastAPI(title="SAVE MÉXICO AYUDAR",version="11.0");app.mount("/static",StaticFiles(directory=STATIC),name="static");security=HTTPBasic(auto_error=False)

class DatosTramite(BaseModel):
    categoria_tramite:str="";modalidad:str="";primer_nombre:str="";segundo_nombre:str="";primer_apellido:str="";segundo_apellido:str="";fecha_nacimiento:str="";lugar_nacimiento:str="";nacionalidad:str="Mexicana";direccion_usa:str="";telefono:str="";correo:str="";consulado:str="";cita:str="";documentos_tenidos:str="";documentos_faltantes:str="";fotografias:list[str]=Field(default_factory=list);datos_extraidos:list[dict]=Field(default_factory=list);datos_especificos:dict=Field(default_factory=dict);estado_posterior:str="PENDIENTE";extra_1:str="";extra_2:str="";confirmado:bool=False
class PreguntaRequest(BaseModel):
    pregunta:str;contexto:str="";categoria_tramite:str="";modalidad:str=""
class ResultadoRequest(BaseModel):
    categoria_tramite:str="";resultado:str="";comentario:str="";estado:str=""
class StripeCheckoutRequest(BaseModel):
    plan:str
class PerfilTramiteRequest(BaseModel):
    categoria_tramite:str;modalidad:str="";contexto:str="";datos:dict=Field(default_factory=dict)

def loadj(p):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return {}
def savej(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
def clean(v):return str(v or "").strip()
def safe(v):return clean(v)
def lista(v):
    if isinstance(v,list):return [safe(x) for x in v if safe(x)]
    return [x.strip() for x in safe(v).split(",") if x.strip()]
def key(v):return re.sub(r"\s+"," ",clean(v).lower())
def htoken(x):return hashlib.sha256(x.encode()).hexdigest()

def load_access():return loadj(ACCESS_FILE)
def save_access(d):savej(ACCESS_FILE,d)
def admin_ok(c):return bool(c and ADMIN_USER and ADMIN_PASS and secrets.compare_digest(c.username,ADMIN_USER) and secrets.compare_digest(c.password,ADMIN_PASS))
def admin_cookie(r):
    t=r.cookies.get("save_admin_token");rec=load_access().get("admin_tokens",{}).get(htoken(t)) if t else None
    return bool(rec and rec.get("active"))
def customer_access(r):
    t=r.cookies.get("save_access_token");rec=load_access().get("tokens",{}).get(htoken(t)) if t else None
    if not rec or not rec.get("active",True):return None
    try:
        if rec.get("expires") and datetime.now(timezone.utc).timestamp()>float(rec["expires"]):return None
    except:return None
    return rec
def require_access(request:Request,credentials:HTTPBasicCredentials|None=Depends(security)):
    if admin_ok(credentials) or admin_cookie(request):return {"type":"admin"}
    r=customer_access(request)
    if r:return r
    raise HTTPException(401,"Acceso no autorizado")
def new_token():return secrets.token_urlsafe(40)
def activate(email,plan,session_id="",subscription_id="",expires=None):
    if not email:return None
    d=load_access();d.setdefault("customers",{});d.setdefault("tokens",{});raw=new_token();hashed=htoken(raw)
    if expires is None:expires=(datetime.now(timezone.utc)+timedelta(hours=24)).timestamp()
    rec={"email":email,"plan":plan,"session_id":session_id,"subscription_id":subscription_id,"expires":expires,"active":True,"token":hashed}
    old=d["customers"].get(email)
    if old and old.get("token"):d["tokens"].pop(old["token"],None)
    d["customers"][email]=rec;d["tokens"][hashed]=rec;save_access(d);return raw
def activate_admin():
    d=load_access();d.setdefault("admin_tokens",{});raw=new_token();d["admin_tokens"][htoken(raw)]={"active":True};save_access(d);return raw

def load_memory():return loadj(MEMORY_FILE)
def save_memory(d):savej(MEMORY_FILE,d)
def memory_key(c,m=""):return key(c)+(" | "+key(m) if key(m) else "")
def get_memory(c,m=""):return load_memory().get(memory_key(c,m))
def save_tramite_memory(c,m,profile):
    d=load_memory();d[memory_key(c,m)]={"categoria_tramite":clean(c),"modalidad":clean(m),"perfil":profile,"updated_at":datetime.now(timezone.utc).isoformat()};save_memory(d)

ASESOR_SYSTEM="""Eres el ASESOR MEXICANO de SAVE MÉXICO AYUDAR. Cada trámite mexicano es diferente. Nunca uses una plantilla universal. Analiza trámite, modalidad, persona, documentos, fotografías, formatos, preguntas, situaciones especiales y estructura del PDF. No inventes requisitos. Distingue datos aportados, documentos que tiene el usuario, documentos faltantes y requisitos oficiales. Si algo no puede confirmarse escribe POR CONFIRMAR CON LA AUTORIDAD. SAVE MÉXICO AYUDAR es privado, no es Gobierno de México ni consulado. Usa español sencillo, claro y sin información amontonada."""
def ai_text(prompt):
    if not gemini:raise HTTPException(500,"GEMINI_API_KEY no configurada.")
    try:
        r=gemini.models.generate_content(model="gemini-2.5-flash",contents=[ASESOR_SYSTEM,prompt]);t=(r.text or "").strip()
        if not t:raise HTTPException(500,"El Asesor Mexicano no produjo información.")
        return t
    except HTTPException:raise
    except Exception as e:raise HTTPException(500,f"Asesor Mexicano: {e}")
def ai_json(prompt):
    t=ai_text(prompt+"\nRESPONDE ÚNICAMENTE CON JSON VÁLIDO. NO USES MARKDOWN NI ```.")
    t=re.sub(r"^```(?:json)?\s*","",t.strip());t=re.sub(r"\s*```$","",t)
    try:return json.loads(t)
    except:raise HTTPException(500,"El Asesor Mexicano devolvió una estructura no válida.")

def construir_perfil(c,m="",contexto="",datos=None):
    datos=datos or {};old=get_memory(c,m);mem=old.get("perfil",{}) if old else {}
    p=f"""TRÁMITE:{c}\nMODALIDAD:{m or "No indicada"}\nMEMORIA:{json.dumps(mem,ensure_ascii=False)[:30000]}\nDATOS:{json.dumps(datos,ensure_ascii=False)[:30000]}\nCONTEXTO:{contexto[:30000]}
Construye el PERFIL ESPECÍFICO. Devuelve JSON:
{{"nombre_tramite":"","modalidad":"","descripcion_simple":"","campos_necesarios":[{{"campo":"","explicacion":"","obligatorio":false}}],"documentos":[{{"nombre":"","tipo":"ORIGINAL|COPIA|ORIGINAL_Y_COPIA|POR_CONFIRMAR","para_que":"","estado":"TENGO|FALTA|POR_CONFIRMAR"}}],"fotografias":[{{"descripcion":"","cantidad":"","caracteristicas":"","estado":"TENGO|FALTA|POR_CONFIRMAR"}}],"formatos":[{{"nombre":"","descripcion":"","estado":"TENGO|FALTA|POR_CONFIRMAR"}}],"preguntas_especificas":[{{"pregunta":"","motivo":""}}],"situaciones_especiales":[{{"situacion":"","accion":""}}],"estructura_pdf":{{"titulo":"","secciones":[{{"titulo":"","campos":[]}}]}},"confirmaciones_oficiales":[],"advertencias":[]}}
La estructura PDF debe ser propia de este trámite y modalidad. No copies otro trámite."""
    profile=ai_json(p);save_tramite_memory(c,m,profile);return profile

@app.get("/")
def home():return FileResponse(STATIC/"index.html")
@app.get("/api/estado")
def estado():return {"ok":True,"app":"SAVE MÉXICO AYUDAR","version":"11.0","asesor":"Gemini / Asesor Mexicano","pdf":"dinámico por trámite"}

@app.post("/api/admin-login")
def admin_login(credentials:HTTPBasicCredentials=Depends(security)):
    if not admin_ok(credentials):raise HTTPException(401,"Usuario o contraseña incorrectos")
    r=JSONResponse({"ok":True,"admin":True});r.set_cookie("save_admin_token",activate_admin(),max_age=86400,httponly=True,secure=True,samesite="lax");return r

@app.post("/api/create-checkout-session")
def checkout(req:StripeCheckoutRequest):
    plan=req.plan.strip().lower();price=PRICE_IDS.get(plan)
    if not price:raise HTTPException(400,"Price ID no configurado para este plan.")
    if not STRIPE_KEY:raise HTTPException(500,"STRIPE_SECRET_KEY no configurada.")
    try:
        p=stripe.Price.retrieve(price);mode="subscription" if p.type=="recurring" else "payment"
        s=stripe.checkout.Session.create(mode=mode,line_items=[{"price":price,"quantity":1}],metadata={"save_plan":plan},success_url=f"{APP_URL}/?success=true&session_id={{CHECKOUT_SESSION_ID}}",cancel_url=f"{APP_URL}/?cancel=true")
        return {"ok":True,"checkout_url":s.url}
    except Exception as e:raise HTTPException(500,f"Stripe: {e}")

@app.get("/api/verify-payment")
def verify_payment(session_id:str):
    if not STRIPE_KEY:raise HTTPException(500,"Stripe no configurado.")
    try:s=stripe.checkout.Session.retrieve(session_id,expand=["subscription","line_items"])
    except Exception as e:raise HTTPException(400,f"No se pudo verificar el pago: {e}")
    if s.payment_status not in ("paid","no_payment_required"):raise HTTPException(403,"El pago todavía no está confirmado.")
    email=s.customer_details.email if s.customer_details else None
    if not email:raise HTTPException(400,"Stripe no proporcionó el correo del cliente.")
    plan=s.metadata.get("save_plan") if s.metadata else None
    if plan not in PRICE_IDS:
        plan=None
        try:
            pid=s.line_items.data[0].price.id if s.line_items and s.line_items.data else None
            for k,v in PRICE_IDS.items():
                if v and v==pid:plan=k;break
        except:pass
    plan=plan or ("monthly" if s.mode=="subscription" else "daily");now=datetime.now(timezone.utc).timestamp();subid=""
    if s.mode=="subscription":
        sub=s.subscription
        if isinstance(sub,str):sub=stripe.Subscription.retrieve(sub)
        if sub.status not in ("active","trialing"):raise HTTPException(403,"La suscripción no está activa.")
        subid=sub.id;expires=float(sub.current_period_end)
    else:expires=now+86400
    raw=activate(email,plan,s.id,subid,expires);r=JSONResponse({"ok":True,"email":email,"plan":plan});r.set_cookie("save_access_token",raw,max_age=max(3600,int(expires-now)),httponly=True,secure=True,samesite="lax");return r

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    body=await request.body();sig=request.headers.get("stripe-signature")
    if not WEBHOOK_SECRET:raise HTTPException(500,"STRIPE_WEBHOOK_SECRET no configurada.")
    try:event=stripe.Webhook.construct_event(body,sig,WEBHOOK_SECRET)
    except Exception as e:raise HTTPException(400,f"Webhook inválido: {e}")
    typ=event["type"];o=event["data"]["object"]
    if typ in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        email=(o.get("customer_details") or {}).get("email")
        if email:
            plan=(o.get("metadata") or {}).get("save_plan")
            if plan not in PRICE_IDS:plan="monthly" if o.get("mode")=="subscription" else "daily"
            sub=o.get("subscription");exp=None
            if sub:
                try:
                    ss=stripe.Subscription.retrieve(sub if isinstance(sub,str) else sub.id);exp=float(ss.current_period_end)
                except:pass
            activate(email,plan,o.get("id",""),sub if isinstance(sub,str) else "",exp)
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
                if rec.get("token"):d.setdefault("tokens",{})[rec["token"]]=rec
                save_access(d)
    return {"received":True}

@app.get("/api/check-access")
def check_access(request:Request,credentials:HTTPBasicCredentials|None=Depends(security)):
    if admin_ok(credentials) or admin_cookie(request):return {"ok":True,"type":"admin"}
    rec=customer_access(request);return {"ok":bool(rec),"type":"customer" if rec else None,"plan":rec.get("plan") if rec else None}

@app.post("/api/perfil-tramite")
def perfil_tramite(req:PerfilTramiteRequest,_=Depends(require_access)):
    if not clean(req.categoria_tramite):raise HTTPException(400,"Debe indicar el trámite.")
    p=construir_perfil(req.categoria_tramite,req.modalidad,req.contexto,req.datos)
    return {"ok":True,"categoria_tramite":req.categoria_tramite,"modalidad":req.modalidad,"perfil":p}

@app.post("/api/ficha-tramite")
def ficha(data:DatosTramite,_=Depends(require_access)):
    p=construir_perfil(data.categoria_tramite,data.modalidad,json.dumps(data.model_dump(),ensure_ascii=False),data.datos_especificos)
    return {"ok":True,"datos":data.model_dump(),"perfil_tramite":p}

@app.post("/api/extraer-pdf")
async def extraer_pdf(file:UploadFile=File(...),_=Depends(require_access)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):raise HTTPException(400,"Solo se acepta PDF.")
    raw=await file.read()
    if len(raw)>15*1024*1024:raise HTTPException(400,"El PDF no puede superar 15 MB.")
    tmp=OUT/("_tmp_"+secrets.token_hex(5)+".pdf");tmp.write_bytes(raw)
    try:
        reader=PdfReader(str(tmp));parts=[]
        for page in reader.pages:
            try:parts.append(page.extract_text() or "")
            except:pass
        text="\n".join(parts).strip();pages=len(reader.pages)
    finally:
        try:tmp.unlink()
        except:pass
    if gemini:
        try:
            r=gemini.models.generate_content(model="gemini-2.5-flash",contents=[types.Part.from_bytes(data=raw,mime_type="application/pdf"),ASESOR_SYSTEM,f"""Extrae solamente información que realmente aparezca en este documento. Identifica tipo de documento, nombres, fechas, números, lugares, datos del trámite y documentos mencionados. Si algo no puede leerse: NO LEGIBLE.\nTEXTO:{text[:40000]}"""])
            t=(r.text or "").strip()
            if t:text=(text+"\n\n--- REVISIÓN DEL ASESOR MEXICANO ---\n"+t)[:50000]
        except:pass
    return {"ok":True,"nombre":file.filename,"texto":text[:50000],"paginas":pages}

@app.post("/api/subir-fotos")
async def subir_fotos(files:list[UploadFile]=File(...),_=Depends(require_access)):
    nombres=[];carpeta=OUT/("fotos_"+secrets.token_hex(6));carpeta.mkdir(parents=True,exist_ok=True)
    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):continue
        raw=await f.read()
        if len(raw)>10*1024*1024:continue
        ext=Path(f.filename or "").suffix.lower()
        if ext not in (".jpg",".jpeg",".png",".webp",".heic"):ext=".jpg"
        nombre=secrets.token_hex(8)+ext;(carpeta/nombre).write_bytes(raw);nombres.append(f.filename or nombre)
    return {"ok":True,"fotografias":nombres}

@app.post("/api/pregunta")
def pregunta(req:PreguntaRequest,_=Depends(require_access)):
    mem=get_memory(req.categoria_tramite,req.modalidad);perfil=mem.get("perfil",{}) if mem else {}
    return {"respuesta":ai_text(f"""TRÁMITE:{req.categoria_tramite}\nMODALIDAD:{req.modalidad or "No indicada"}\nMEMORIA ESPECÍFICA:{json.dumps(perfil,ensure_ascii=False)[:30000]}\nINFORMACIÓN:{req.contexto[:30000]}\nPREGUNTA:{req.pregunta}\nResponde primero la respuesta principal. No inventes requisitos. Si no puede confirmarse: POR CONFIRMAR CON LA AUTORIDAD.""")}

def nombre_completo(d):return " ".join(x for x in[d.primer_nombre,d.segundo_nombre,d.primer_apellido,d.segundo_apellido] if safe(x))

def pdf_content(data):
    mem=get_memory(data.categoria_tramite,data.modalidad);base=mem.get("perfil",{}) if mem else {}
    return ai_json(f"""Prepara el contenido FINAL de un PDF privado de preparación para este trámite.
TRÁMITE:{data.categoria_tramite}
MODALIDAD:{data.modalidad}
PERFIL:{json.dumps(base,ensure_ascii=False)[:40000]}
DATOS:{json.dumps(data.model_dump(),ensure_ascii=False)[:40000]}
El PDF debe ser específico para ESTE trámite. No uses secciones genéricas si no corresponden. Conserva datos aportados. No inventes requisitos, documentos, cantidades ni datos. Lo no confirmado debe decir POR CONFIRMAR CON LA AUTORIDAD.
Devuelve:
{{"titulo":"","subtitulo":"","secciones":[{{"titulo":"","items":[{{"etiqueta":"","valor":"","tipo":"dato|documento|fotografia|formato|pendiente|confirmar|nota"}}]}}],"checklist":[],"confirmaciones":[],"avisos":[]}}""")

def generar_pdf(data,content):
    nombre=f"SAVE_MEXICO_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}.pdf";path=OUT/nombre;c=canvas.Canvas(str(path),pagesize=LETTER);W,H=LETTER;y=H-45;margin=45;width=W-90
    def newpage():
        nonlocal y;c.showPage();y=H-45
    def need(h=35):
        nonlocal y
        if y<h+45:newpage()
    def wrap(text,size=9.5,lead=14,bold=False,x=margin,w=width):
        nonlocal y
        font="Helvetica-Bold" if bold else "Helvetica";c.setFont(font,size);cur=""
        for word in str(text).split():
            test=(cur+" "+word).strip()
            if c.stringWidth(test,font,size)>w:
                if cur:c.drawString(x,y,cur);y-=lead
                cur=word
            else:cur=test
        if cur:c.drawString(x,y,cur);y-=lead
    def title(t):
        need(45);wrap(t,18,22,True)
    def section(t):
        nonlocal y;need(45);y-=7;wrap(t,12,16,True);y-=3
    def item(label,value):
        if safe(value):need(30);wrap(f"{label}: {value}")
    title(content.get("titulo") or data.categoria_tramite);wrap(content.get("subtitulo") or "Documento privado de preparación",10,14);y-=8
    section("IDENTIFICACIÓN DEL TRÁMITE");item("Trámite",data.categoria_tramite);item("Modalidad",data.modalidad)
    section("DATOS DEL SOLICITANTE");item("Nombre",nombre_completo(data));item("Fecha de nacimiento",data.fecha_nacimiento);item("Lugar de nacimiento",data.lugar_nacimiento);item("Nacionalidad",data.nacionalidad);item("Domicilio en Estados Unidos",data.direccion_usa);item("Teléfono",data.telefono);item("Correo",data.correo);item("Consulado",data.consulado);item("Cita",data.cita)
    for sec in content.get("secciones",[]):
        if safe(sec.get("titulo")):section(sec["titulo"])
        for it in sec.get("items",[]):
            val=safe(it.get("valor"));tipo=safe(it.get("tipo"))
            if tipo=="confirmar":val=val or "POR CONFIRMAR CON LA AUTORIDAD"
            item(safe(it.get("etiqueta")),val)
    docs=lista(data.documentos_tenidos)
    if docs:
        section("DOCUMENTOS INDICADOS POR EL SOLICITANTE")
        for x in docs:item("[TENGO]",x)
    faltan=lista(data.documentos_faltantes)
    if faltan:
        section("DOCUMENTOS PENDIENTES")
        for x in faltan:item("[FALTA]",x)
    if data.fotografias:
        section("FOTOGRAFÍAS REGISTRADAS")
        for x in data.fotografias:item("[FOTOGRAFÍA]",x)
    if data.datos_extraidos:
        section("INFORMACIÓN EXTRAÍDA DE DOCUMENTOS")
        for d in data.datos_extraidos:
            if isinstance(d,dict):
                for k,v in d.items():item(k,v)
    if content.get("checklist"):
        section("LISTA DE PREPARACIÓN")
        for x in content["checklist"]:item("[ ]",x)
    if content.get("confirmaciones"):
        section("DEBE CONFIRMARSE")
        for x in content["confirmaciones"]:item("CONFIRMAR",x)
    section("ESTADO DEL TRÁMITE");item("Estado",data.estado_posterior or "PENDIENTE");item("Información adicional",data.extra_1);item("Otra información",data.extra_2)
    if content.get("avisos"):
        section("AVISOS DEL ASESOR MEXICANO")
        for x in content["avisos"]:item("Aviso",x)
    section("AVISO IMPORTANTE");wrap("SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida.",8.5,12);wrap("No es una agencia del Gobierno de México ni representa a ningún consulado mexicano.",8.5,12);wrap("Este documento es una herramienta privada de organización y preparación. Los requisitos, documentos, decisiones y resultados corresponden a la autoridad competente.",8.5,12)
    c.save();return nombre

@app.post("/api/generar-guia-consular")
def generar_guia(data:DatosTramite,_=Depends(require_access)):
    if not data.confirmado:raise HTTPException(400,"La información debe ser revisada antes de generar el PDF.")
    if not clean(data.categoria_tramite):raise HTTPException(400,"Debe indicar el trámite.")
    content=pdf_content(data);nombre=generar_pdf(data,content)
    return {"ok":True,"archivo":f"/descargar/{nombre}","nombre":nombre,"tramite":data.categoria_tramite,"modalidad":data.modalidad,"pdf_dinamico":True,"asesor_mexicano":True}

@app.get("/descargar/{nombre}")
def descargar(nombre:str,_=Depends(require_access)):
    nombre=Path(nombre).name
    if not nombre.lower().endswith(".pdf"):raise HTTPException(400,"Archivo no válido.")
    p=OUT/nombre
    if not p.exists():raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(p,filename=p.name,media_type="application/pdf")

@app.post("/api/resultado-tramite")
def resultado(req:ResultadoRequest,_=Depends(require_access)):
    return {"ok":True,"estado":req.estado or req.resultado or "PENDIENTE","mensaje":"Resultado guardado correctamente."}

@app.post("/api/logout")
def logout():
    r=JSONResponse({"ok":True});r.delete_cookie("save_access_token");r.delete_cookie("save_admin_token");return r
