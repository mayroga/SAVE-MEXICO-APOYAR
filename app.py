import os,json,secrets,uuid
from pathlib import Path
from typing import Any,Optional
import stripe
from fastapi import FastAPI,HTTPException,Request,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static";DATA=BASE/"data";OUT=BASE/"out";TRAMITES=DATA/"tramites.json"
STATIC.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)

ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
PRICE_DAILY=os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1","")
PRICE_MONTHLY=os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2","")
PRICE_ANNUAL=os.getenv("STRIPE_PRICE_ID_ANNUAL","")
if STRIPE_SECRET_KEY: stripe.api_key=STRIPE_SECRET_KEY

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="5.2.0")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")

ADMIN_TOKENS=set();ACCESS_TOKENS=set()

class Login(BaseModel):
    username:str
    password:str

class Checkout(BaseModel):
    plan:str

class Guide(BaseModel):
    tramite:str
    modalidad:str=""
    datos_personales:dict=Field(default_factory=dict)
    datos_especificos:dict=Field(default_factory=dict)
    documentos:dict=Field(default_factory=dict)
    documentos_disponibles:list=Field(default_factory=list)
    documentos_faltantes:list=Field(default_factory=list)
    documentos_dudosos:list=Field(default_factory=list)
    situaciones:list=Field(default_factory=list)
    aclaraciones:list=Field(default_factory=list)
    idioma:str="es"


# ============================================================
# DATOS
# ============================================================

def load_data():
    if not TRAMITES.exists():
        raise HTTPException(500,"No existe data/tramites.json.")
    try:return json.loads(TRAMITES.read_text(encoding="utf-8"))
    except Exception as e:raise HTTPException(500,f"No se pudo leer tramites.json: {e}")

def get_tramites():
    x=load_data().get("tramites",{})
    if isinstance(x,dict):return x
    if isinstance(x,list):
        r={}
        for v in x:
            if isinstance(v,dict):
                k=v.get("id") or v.get("codigo")
                if k:r[str(k)]=v
        return r
    return {}

def get_tramite(tid):
    t=get_tramites().get(tid)
    if not t:raise HTTPException(404,"Trámite no encontrado.")
    return t

def get_modalidades(tid):
    x=get_tramite(tid).get("modalidades",{})
    if isinstance(x,dict):return x
    if isinstance(x,list):
        r={}
        for v in x:
            if isinstance(v,dict):
                k=v.get("id") or v.get("codigo")
                if k:r[str(k)]=v
        return r
    return {}

def get_modalidad(tid,mid):
    m=get_modalidades(tid).get(mid)
    if not m:raise HTTPException(404,"Modalidad no encontrada.")
    return m


# ============================================================
# ACCESO
# ============================================================

def new_token(store):
    t=secrets.token_urlsafe(32);store.add(t);return t

def cookie_access(request):
    return (
        request.cookies.get("save_admin_token") in ADMIN_TOKENS,
        request.cookies.get("save_access_token") in ACCESS_TOKENS
    )

def require_access(request):
    a,p=cookie_access(request)
    if not(a or p):raise HTTPException(401,"Se requiere acceso autorizado.")
    return True


# ============================================================
# BASE
# ============================================================

@app.get("/")
async def home():
    f=STATIC/"index.html"
    if not f.exists():raise HTTPException(404,"No existe static/index.html.")
    return FileResponse(f)

@app.get("/health")
async def health():
    d=load_data();t=get_tramites()
    return {
        "ok":True,
        "app":"SAVE MÉXICO AYUDAR",
        "version":"5.2.0",
        "datos_version":d.get("version",""),
        "datos_actualizado":d.get("actualizado",""),
        "tramites":list(t.keys()),
        "tramites_count":len(t),
        "stripe":bool(STRIPE_SECRET_KEY),
        "stripe_webhook":bool(STRIPE_WEBHOOK_SECRET),
        "admin_configured":bool(ADMIN_USERNAME and ADMIN_PASSWORD)
    }


# ============================================================
# LOGIN / ACCESO
# ============================================================

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

@app.get("/api/check-access")
async def check_access(request:Request):
    a,p=cookie_access(request)
    return {"ok":True,"access":bool(a or p),"admin":a,"paid":p}

@app.post("/api/logout")
async def logout(request:Request):
    a=request.cookies.get("save_admin_token");p=request.cookies.get("save_access_token")
    if a:ADMIN_TOKENS.discard(a)
    if p:ACCESS_TOKENS.discard(p)
    r=JSONResponse({"ok":True});r.delete_cookie("save_admin_token");r.delete_cookie("save_access_token")
    return r


# ============================================================
# TRAMITES
# ============================================================

@app.get("/api/tramites")
async def tramites(request:Request):
    require_access(request);x=get_tramites()
    return {"tramites":[
        {
            "id":k,
            "nombre":v.get("nombre",k) if isinstance(v,dict) else k,
            "nombre_corto":v.get("nombre_corto",v.get("nombre",k)) if isinstance(v,dict) else k,
            "autoridad":v.get("autoridad","") if isinstance(v,dict) else ""
        } for k,v in x.items()
    ]}

@app.get("/api/modalidades")
async def modalidades(tramite:str,request:Request):
    require_access(request);x=get_modalidades(tramite)
    return {"tramite":tramite,"modalidades":[
        {
            "id":k,
            "nombre":v.get("nombre",k) if isinstance(v,dict) else k,
            "descripcion":v.get("descripcion","") if isinstance(v,dict) else ""
        } for k,v in x.items()
    ]}

@app.get("/api/ficha-tramite")
async def ficha_tramite(tramite:str,request:Request,modalidad:Optional[str]=None):
    require_access(request);t=get_tramite(tramite)
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
    return {
        "tramite":tramite,
        "nombre":t.get("nombre",tramite),
        "autoridad":t.get("autoridad",""),
        "modalidades":{
            k:{"nombre":v.get("nombre",k),"descripcion":v.get("descripcion","")}
            for k,v in get_modalidades(tramite).items()
        },
        "fuentes":t.get("fuentes",[])
    }


# ============================================================
# CONDICIONES
# ============================================================

def vals(v):
    if v is None:return []
    return v if isinstance(v,list) else [v]

def norm(v):
    return v.strip().lower() if isinstance(v,str) else v

def condition_match(answers,cond):
    if not cond:return True
    if isinstance(cond,bool):return cond
    if isinstance(cond,list):return all(condition_match(answers,x) for x in cond)
    if not isinstance(cond,dict):return True

    if "todas" in cond or "todos" in cond:
        return all(condition_match(answers,x) for x in vals(cond.get("todas",cond.get("todos"))))

    if "alguna" in cond or "alguno" in cond:
        return any(condition_match(answers,x) for x in vals(cond.get("alguna",cond.get("alguno"))))

    key=cond.get("campo") or cond.get("pregunta") or cond.get("id") or cond.get("clave")
    if not key:return True
    actual=answers.get(key)

    if "incluye" in cond:
        q=norm(cond["incluye"])
        if isinstance(actual,list):return q in [norm(x) for x in actual]
        return isinstance(actual,str) and q in norm(actual)

    if "contiene" in cond:
        q=norm(cond["contiene"])
        if isinstance(actual,list):return any(q in norm(x) for x in actual if isinstance(x,str))
        return isinstance(actual,str) and q in norm(actual)

    if "igual_a" in cond:return norm(actual)==norm(cond["igual_a"])
    if "es" in cond:return norm(actual)==norm(cond["es"])
    if "distinto_de" in cond:return norm(actual)!=norm(cond["distinto_de"])
    if "no_es" in cond:return norm(actual)!=norm(cond["no_es"])

    if "no_incluye" in cond:
        q=norm(cond["no_incluye"])
        if isinstance(actual,list):return q not in [norm(x) for x in actual]
        return not isinstance(actual,str) or q not in norm(actual)

    if "alguno_de" in cond:
        q=[norm(x) for x in vals(cond["alguno_de"])]
        if isinstance(actual,list):return any(norm(x) in q for x in actual)
        return norm(actual) in q

    if "todos_de" in cond:
        q=[norm(x) for x in vals(cond["todos_de"])]
        return isinstance(actual,list) and all(x in [norm(y) for y in actual] for x in q)

    if "cantidad_mayor_que" in cond:
        try:return float(actual or 0)>float(cond["cantidad_mayor_que"])
        except:return False

    if "cantidad_igual_a" in cond:
        try:return float(actual or 0)==float(cond["cantidad_igual_a"])
        except:return False

    if "existe" in cond:
        existe=actual not in (None,"",[],{})
        return existe==bool(cond["existe"])

    return True

def question_visible(q,answers):
    if not isinstance(q,dict):return False
    for k in ("mostrar_si","condicion","cuando"):
        if k in q and not condition_match(answers,q[k]):return False
    return True

def visible_questions(qs,answers):
    return [q for q in qs if question_visible(q,answers)] if isinstance(qs,list) else []

def empty(v):
    return v is None or v=="" or v==[] or v=={}

def unanswered_required(qs,answers):
    r=[]
    for q in visible_questions(qs,answers):
        if q.get("required") is not True:continue
        k=q.get("id") or q.get("clave") or q.get("campo")
        if k and empty(answers.get(k)):r.append(q)
    return r

def dynamic_situations(source,answers):
    r=[]
    if not isinstance(source,list):return r
    for x in source:
        if isinstance(x,dict):
            c=x.get("mostrar_si") or x.get("condicion") or x.get("cuando")
            if condition_match(answers,c):r.append(x)
    return r


# ============================================================
# DOCUMENTOS
# ============================================================

def document_condition(doc,answers):
    if not isinstance(doc,dict):return True
    for k in ("mostrar_si","condicion","cuando"):
        if k in doc and not condition_match(answers,doc[k]):return False
    return True

def document_items(modalidad,answers):
    docs=modalidad.get("documentos") or modalidad.get("documentos_requeridos") or []
    if isinstance(docs,dict):
        docs=[dict(v,id=k) if isinstance(v,dict) else {"id":k,"nombre":str(v)} for k,v in docs.items()]
    return [d for d in docs if isinstance(d,dict) and document_condition(d,answers)]

def document_rules(modalidad,answers):
    rules=modalidad.get("reglas_documentos",modalidad.get("document_rules",[]))
    if isinstance(rules,dict):
        rules=[dict(v,id=k) if isinstance(v,dict) else {"id":k} for k,v in rules.items()]
    r=[]
    for x in rules or []:
        if isinstance(x,dict):
            c=x.get("mostrar_si") or x.get("condicion") or x.get("cuando")
            if condition_match(answers,c):r.append(x)
    return r

def contradictions(modalidad,answers):
    rules=modalidad.get("contradicciones",[])
    if isinstance(rules,dict):rules=[rules]
    r=[]
    for x in rules or []:
        if isinstance(x,dict):
            c=x.get("condicion") or x.get("cuando") or x.get("mostrar_si")
            if condition_match(answers,c):
                r.append(x.get("mensaje",x.get("descripcion","Existe una inconsistencia que debe revisarse.")))
    return r


# ============================================================
# EVALUACION
# ============================================================

def evaluate_case(tid,mid,payload):
    t=get_tramite(tid);m=get_modalidad(tid,mid)
    answers={};answers.update(payload.datos_personales or {});answers.update(payload.datos_especificos or {})

    qs=m.get("preguntas") or m.get("questions") or []
    pending=unanswered_required(qs,answers)
    situations=dynamic_situations(m.get("situaciones",[]),answers)
    docs=document_items(m,answers)
    rules=document_rules(m,answers)
    inc=contradictions(m,answers)

    supplied=payload.documentos or {}
    available=set(payload.documentos_disponibles or [])
    missing=set(payload.documentos_faltantes or [])
    unsure=set(payload.documentos_dudosos or [])
    out=[]

    for d in docs:
        did=d.get("id","");state=supplied.get(did,"")
        if not state:
            if did in available:state="LO_TENGO"
            elif did in missing:state="NO_LO_TENGO"
            elif did in unsure:state="NO_ESTOY_SEGURO"
        out.append({
            "id":did,
            "bloque":d.get("bloque",""),
            "nombre":d.get("nombre",did),
            "estado":state,
            "obligatorio":bool(d.get("obligatorio",False)),
            "importancia":d.get("importancia",""),
            "nota":d.get("nota",d.get("descripcion","")),
            "motivo":d.get("motivo",""),
            "confirmar":bool(d.get("confirmar",d.get("confirmar_con_autoridad",False)))
        })

    for rule in rules:
        did=rule.get("documento") or rule.get("id")
        z=next((d for d in out if d["id"]==did),None)
        if z:
            if rule.get("obligatorio") is True:z["obligatorio"]=True
            if rule.get("confirmar") is True:z["confirmar"]=True
            if rule.get("motivo"):z["motivo"]=rule["motivo"]

    falt=[d for d in out if d["obligatorio"] and d["estado"] in ("NO_LO_TENGO","",None)]
    dud=[d for d in out if d["obligatorio"] and d["estado"]=="NO_ESTOY_SEGURO"]

    status="LISTO_PARA_CONFIRMAR"
    if pending:status="REQUIERE_CONFIRMACION"
    if falt:status="FALTAN_DOCUMENTOS"
    if dud:status="REQUIERE_CONFIRMACION"
    if inc:status="HAY_INCONSISTENCIAS"

    return {
        "ok":True,
        "tramite":tid,
        "tramite_nombre":t.get("nombre",tid),
        "modalidad":mid,
        "modalidad_nombre":m.get("nombre",mid),
        "estado_resultado":status,
        "preguntas_pendientes":[
            {"id":q.get("id") or q.get("clave") or q.get("campo"),
             "texto":q.get("texto",q.get("pregunta",""))}
            for q in pending
        ],
        "situaciones":situations,
        "documentos":out,
        "documentos_faltantes":[d["id"] for d in falt],
        "documentos_dudosos":[d["id"] for d in dud],
        "inconsistencias":inc,
        "autoridad":t.get("autoridad",""),
        "fuentes":t.get("fuentes",[])
    }


@app.post("/api/resultado-tramite")
async def resultado_tramite(payload:Guide,request:Request):
    require_access(request)
    if not payload.tramite:raise HTTPException(400,"Falta seleccionar el trámite.")
    if not payload.modalidad:raise HTTPException(400,"Falta seleccionar la modalidad.")
    return evaluate_case(payload.tramite,payload.modalidad,payload)


# ============================================================
# STRIPE
# ============================================================

@app.post("/api/create-checkout-session")
async def create_checkout_session(data:Checkout,request:Request):
    admin,_=cookie_access(request)
    if admin:return {"ok":True,"admin":True,"access":True}
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado.")

    prices={"daily":PRICE_DAILY,"monthly":PRICE_MONTHLY,"annual":PRICE_ANNUAL}
    price=prices.get(data.plan)
    if not price:raise HTTPException(400,"Plan de pago no configurado.")

    mode="subscription" if data.plan in ("monthly","annual") else "payment"

    try:
        s=stripe.checkout.Session.create(
            mode=mode,
            line_items=[{"price":price,"quantity":1}],
            success_url=APP_URL+"/?payment=success&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=APP_URL+"/?payment=cancel",
            metadata={"plan":data.plan}
        )
        return {"ok":True,"url":s.url,"session_id":s.id}
    except Exception as e:
        raise HTTPException(500,f"No se pudo crear el pago: {e}")

@app.get("/api/verify-payment")
async def verify_payment(session_id:str,request:Request):
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        if s.payment_status=="paid" or s.status=="complete":
            token=new_token(ACCESS_TOKENS)
            r=JSONResponse({
                "ok":True,
                "access":True,
                "payment_status":s.payment_status,
                "session_id":s.id
            })
            r.set_cookie("save_access_token",token,httponly=True,secure=True,samesite="lax",max_age=31536000)
            return r
        return {"ok":False,"access":False,"payment_status":s.payment_status,"status":s.status}
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/stripe-webhook")
async def stripe_webhook(request:Request):
    body=await request.body();sig=request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:raise HTTPException(503,"STRIPE_WEBHOOK_SECRET no está configurado.")
    try:
        event=stripe.Webhook.construct_event(body,sig,STRIPE_WEBHOOK_SECRET)
    except ValueError:raise HTTPException(400,"Webhook inválido.")
    except stripe.error.SignatureVerificationError:raise HTTPException(400,"Firma del webhook inválida.")

    if event.get("type") in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        s=event.get("data",{}).get("object",{})
        if s.get("payment_status")=="paid" or event.get("type")=="checkout.session.async_payment_succeeded":
            new_token(ACCESS_TOKENS)

    return {"received":True}


# ============================================================
# PDF
# ============================================================

def pdf_text(c,text,x,y,width,font="Helvetica",size=10,leading=13):
    c.setFont(font,size)
    for line in simpleSplit(str(text or ""),font,size,width):
        if y<45:c.showPage();c.setFont(font,size);y=LETTER[1]-45
        c.drawString(x,y,line);y-=leading
    return y

def pdf_document(c,d,y):
    if y<95:c.showPage();y=LETTER[1]-45
    did=d.get("id","");name=d.get("nombre",did)
    estado=d.get("estado","") or "NO INDICADO"
    ob="SÍ" if d.get("obligatorio") else "NO"
    co="SÍ" if d.get("confirmar") else "NO"

    c.setFont("Helvetica-Bold",11);c.drawString(45,y,f"DOCUMENTO: {did}");y-=17
    y=pdf_text(c,f"Nombre: {name}",55,y,500,"Helvetica-Bold",10)
    y=pdf_text(c,f"Estado: {estado}",55,y,500)
    y=pdf_text(c,f"Obligatorio: {ob}",55,y,500)
    y=pdf_text(c,f"Confirmar con autoridad: {co}",55,y,500)
    if d.get("importancia"):y=pdf_text(c,f"Importancia: {d['importancia']}",55,y,500)
    if d.get("motivo"):y=pdf_text(c,f"Motivo: {d['motivo']}",55,y,500)
    if d.get("nota"):y=pdf_text(c,f"Nota: {d['nota']}",55,y,500)
    return y-12

def make_pdf(payload):
    result=evaluate_case(payload.tramite,payload.modalidad,payload)
    t=get_tramite(payload.tramite);m=get_modalidad(payload.tramite,payload.modalidad)
    filename=f"guia_{payload.tramite}_{payload.modalidad}_{uuid.uuid4().hex[:10]}.pdf"
    path=OUT/filename;c=canvas.Canvas(str(path),pagesize=LETTER)
    w,h=LETTER;y=h-45;c.setTitle("SAVE MÉXICO AYUDAR")

    c.setFont("Helvetica-Bold",17);c.drawString(45,y,"SAVE MÉXICO AYUDAR");y-=25
    y=pdf_text(c,"GUÍA PERSONALIZADA DE PREPARACIÓN DOCUMENTAL",45,y,520,"Helvetica-Bold",13,16)
    y-=8
    y=pdf_text(c,f"Trámite: {t.get('nombre',payload.tramite)}",45,y,520,"Helvetica-Bold",11)
    y=pdf_text(c,f"Modalidad: {m.get('nombre',payload.modalidad)}",45,y,520,"Helvetica-Bold",11)
    if t.get("autoridad"):y=pdf_text(c,f"Autoridad: {t['autoridad']}",45,y,520)
    y-=10;c.line(45,y,565,y);y-=20

    c.setFont("Helvetica-Bold",12);c.drawString(45,y,"RESULTADO");y-=18
    y=pdf_text(c,f"Estado: {result.get('estado_resultado','')}",45,y,520,"Helvetica-Bold",11);y-=8

    datos=payload.datos_personales or {}
    if datos:
        if y<120:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"DATOS PROPORCIONADOS");y-=18
        labels={
            "nombres":"Nombres","apellido_paterno":"Apellido paterno","apellido_materno":"Apellido materno",
            "fecha_nacimiento":"Fecha de nacimiento","lugar_nacimiento":"Lugar de nacimiento",
            "entidad_nacimiento":"Entidad de nacimiento","sexo":"Sexo","nacionalidad":"Nacionalidad",
            "estado_residencia_usa":"Estado de residencia en EE. UU.","ciudad_residencia_usa":"Ciudad de residencia",
            "domicilio_usa":"Domicilio","codigo_postal":"Código postal","telefono":"Teléfono","email":"Correo electrónico"
        }
        for k,v in datos.items():
            if not empty(v):y=pdf_text(c,f"{labels.get(k,k)}: {v}",55,y,500)
        y-=10

    if y<100:c.showPage();y=h-45
    c.setFont("Helvetica-Bold",13);c.drawString(45,y,"DOCUMENTOS APLICABLES");y-=22
    for d in result.get("documentos",[]):y=pdf_document(c,d,y)

    situations=result.get("situaciones",[])
    if situations:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"SITUACIONES DETECTADAS");y-=18
        for s in situations:
            text=s.get("texto") or s.get("descripcion") or s.get("nombre","") if isinstance(s,dict) else str(s)
            if text:y=pdf_text(c,"• "+text,55,y,500)
        y-=10

    inc=result.get("inconsistencias",[])
    if inc:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"INCONSISTENCIAS QUE DEBEN REVISARSE");y-=18
        for x in inc:y=pdf_text(c,"• "+str(x),55,y,500)
        y-=10

    falt=result.get("documentos_faltantes",[])
    if falt:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"DOCUMENTOS FALTANTES");y-=18
        for x in falt:y=pdf_text(c,"• "+str(x),55,y,500)
        y-=10

    dud=result.get("documentos_dudosos",[])
    if dud:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"DOCUMENTOS QUE DEBEN CONFIRMARSE");y-=18
        for x in dud:y=pdf_text(c,"• "+str(x),55,y,500)
        y-=10

    confirmados=[d for d in result.get("documentos",[]) if d.get("confirmar")]
    if confirmados:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"PUNTOS A CONFIRMAR CON LA AUTORIDAD");y-=18
        for d in confirmados:y=pdf_text(c,"• "+d.get("nombre",d.get("id","")),55,y,500)
        y-=10

    pending=result.get("preguntas_pendientes",[])
    if pending:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"INFORMACIÓN PENDIENTE");y-=18
        for q in pending:y=pdf_text(c,"• "+q.get("texto",q.get("id","")),55,y,500)
        y-=10

    fuentes=result.get("fuentes",[])
    if fuentes:
        if y<110:c.showPage();y=h-45
        c.setFont("Helvetica-Bold",12);c.drawString(45,y,"FUENTES / REFERENCIAS");y-=18
        for f in fuentes:
            text=f.get("nombre") or f.get("titulo") or f.get("url") or str(f) if isinstance(f,dict) else str(f)
            y=pdf_text(c,"• "+text,55,y,500)

    if y<90:c.showPage();y=h-45
    y-=20;c.setFont("Helvetica-Bold",10);y=pdf_text(c,"IMPORTANTE",45,y,520,"Helvetica-Bold",10)
    y=pdf_text(c,"Esta guía refleja la información proporcionada por el usuario y las reglas configuradas para el trámite seleccionado.",45,y,520,"Helvetica",9,12)
    y=pdf_text(c,"Los requisitos que dependan de la autoridad deben confirmarse directamente antes de acudir.",45,y,520,"Helvetica",9,12)
    pdf_text(c,"SAVE MÉXICO AYUDAR no inventa requisitos, costos, citas ni excepciones.",45,y,520,"Helvetica",9,12)
    c.save()
    return path


@app.post("/api/generar-guia-consular")
async def generar_guia_consular(payload:Guide,request:Request):
    require_access(request)
    if not payload.tramite:raise HTTPException(400,"Falta seleccionar el trámite.")
    if not payload.modalidad:raise HTTPException(400,"Falta seleccionar la modalidad.")
    p=make_pdf(payload)
    return {"ok":True,"filename":p.name,"url":f"/descargar/{p.name}"}


@app.get("/descargar/{filename}")
async def descargar(filename:str,request:Request):
    require_access(request)
    safe=Path(filename).name
    if safe!=filename or Path(safe).suffix.lower()!=".pdf":raise HTTPException(400,"Archivo no permitido.")
    p=OUT/safe
    if not p.exists():raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(p,media_type="application/pdf",filename=p.name)


# ============================================================
# ARCHIVOS
# ============================================================

@app.post("/api/subir-documento")
async def subir_documento(request:Request,file:UploadFile=File(...)):
    require_access(request)
    if not file.filename:raise HTTPException(400,"No se recibió archivo.")
    ext=Path(file.filename).suffix.lower()
    if ext not in {".pdf",".jpg",".jpeg",".png"}:raise HTTPException(400,"Tipo de archivo no permitido.")
    data=await file.read()
    if len(data)>10*1024*1024:raise HTTPException(400,"El archivo supera 10 MB.")
    name=uuid.uuid4().hex+ext;p=OUT/name;p.write_bytes(data)
    pages=None
    if ext==".pdf":
        try:pages=len(PdfReader(str(p)).pages)
        except:pass
    return {"ok":True,"filename":name,"original_filename":file.filename,"size":len(data),"paginas":pages}


if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")),reload=False)
