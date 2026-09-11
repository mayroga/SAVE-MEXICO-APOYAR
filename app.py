import os,json,secrets,uuid,re
from datetime import datetime
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
STATIC=BASE/"static"
DATA=BASE/"data"
OUT=BASE/"out"
TRAMITES=DATA/"tramites.json"
STATIC.mkdir(parents=True,exist_ok=True)
DATA.mkdir(parents=True,exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)

ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
PRICE_DAILY=os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1","")
PRICE_MONTHLY=os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2","")
PRICE_ANNUAL=os.getenv("STRIPE_PRICE_ID_ANNUAL") or os.getenv("STRIPE_PRICE_ID3","")

if STRIPE_SECRET_KEY:
    stripe.api_key=STRIPE_SECRET_KEY

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="5.1.0")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")

ADMIN_TOKENS=set()
ACCESS_TOKENS=set()
PAYMENTS={}

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
    documentos:Any=Field(default_factory=list)
    documentos_disponibles:list=Field(default_factory=list)
    documentos_faltantes:list=Field(default_factory=list)
    documentos_dudosos:list=Field(default_factory=list)
    situaciones:list=Field(default_factory=list)
    aclaraciones:list=Field(default_factory=list)
    idioma:str="es"
    consulado:dict=Field(default_factory=dict)
    respuestas:dict=Field(default_factory=dict)
    resultado:dict=Field(default_factory=dict)

# ============================================================
# DATOS
# ============================================================

def load_data():
    if not TRAMITES.exists():
        raise HTTPException(500,"No existe data/tramites.json.")
    try:
        data=json.loads(TRAMITES.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(500,f"No se pudo leer data/tramites.json: {e}")
    if not isinstance(data,dict):
        raise HTTPException(500,"tramites.json debe contener un objeto JSON.")
    return data

def _items(value):
    if isinstance(value,dict):
        return [(str(k),v) for k,v in value.items() if isinstance(v,dict)]
    if isinstance(value,list):
        out=[]
        for x in value:
            if isinstance(x,dict):
                k=x.get("id") or x.get("codigo") or x.get("clave")
                if k:
                    out.append((str(k),x))
        return out
    return []

def get_tramites():
    return dict(_items(load_data().get("tramites",[])))

def get_tramite(tid):
    t=get_tramites().get(str(tid))
    if not isinstance(t,dict):
        raise HTTPException(404,"Trámite no encontrado.")
    return t

def get_modalidades(tid):
    return dict(_items(get_tramite(tid).get("modalidades",[])))

def get_modalidad(tid,mid):
    m=get_modalidades(tid).get(str(mid))
    if not isinstance(m,dict):
        raise HTTPException(404,"Modalidad no encontrada.")
    return m

def get_blocks(mod):
    if not isinstance(mod,dict):return []
    x=mod.get("bloques_documentales",mod.get("bloques",[]))
    if isinstance(x,dict):
        return [dict(v, id=v.get("id",k)) if isinstance(v,dict) else {} for k,v in x.items()]
    return x if isinstance(x,list) else []

def get_questions(mod):
    if not isinstance(mod,dict):return []
    x=mod.get("preguntas") or mod.get("preguntas_situacion") or mod.get("preguntas_especificas") or []
    return x if isinstance(x,list) else []

def get_docs(mod):
    out=[]
    for b in get_blocks(mod):
        if not isinstance(b,dict):continue
        arr=b.get("documentos",[])
        if isinstance(arr,dict):arr=list(arr.values())
        if not isinstance(arr,list):continue
        for d in arr:
            if isinstance(d,dict):
                x=dict(d)
                x["_bloque_id"]=b.get("id",b.get("codigo",""))
                x["_bloque_seccion"]=b.get("seccion",b.get("nombre",""))
                out.append(x)
    if not out:
        x=mod.get("documentos",[]) if isinstance(mod,dict) else []
        if isinstance(x,dict):x=list(x.values())
        if isinstance(x,list):
            out.extend([dict(d) for d in x if isinstance(d,dict)])
    return out

# ============================================================
# ACCESO
# ============================================================

def new_token(store):
    token=secrets.token_urlsafe(32)
    store.add(token)
    return token

def cookie_access(request):
    a=request.cookies.get("save_admin_token")
    p=request.cookies.get("save_access_token")
    return a in ADMIN_TOKENS,p in ACCESS_TOKENS

def require_access(request):
    admin,paid=cookie_access(request)
    if not(admin or paid):
        raise HTTPException(401,"Se requiere acceso autorizado.")
    return True

@app.post("/api/admin-login")
async def admin_login(data:Login):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(503,"El acceso administrativo no está configurado.")
    if not secrets.compare_digest(str(data.username),str(ADMIN_USERNAME)) or not secrets.compare_digest(str(data.password),str(ADMIN_PASSWORD)):
        raise HTTPException(401,"Usuario o contraseña incorrectos.")
    token=new_token(ADMIN_TOKENS)
    r=JSONResponse({"ok":True,"access":True,"admin":True,"message":"Acceso administrativo autorizado."})
    r.set_cookie("save_admin_token",token,httponly=True,secure=True,samesite="lax",max_age=86400)
    return r

@app.post("/api/logout")
async def logout(request:Request):
    ADMIN_TOKENS.discard(request.cookies.get("save_admin_token"))
    ACCESS_TOKENS.discard(request.cookies.get("save_access_token"))
    r=JSONResponse({"ok":True})
    r.delete_cookie("save_admin_token")
    r.delete_cookie("save_access_token")
    return r

@app.get("/api/check-access")
async def check_access(request:Request):
    admin,paid=cookie_access(request)
    return {"ok":True,"access":bool(admin or paid),"admin":admin,"paid":paid}

# ============================================================
# STRIPE
# ============================================================

def price_for(plan):
    p=str(plan or "").lower().strip()
    if p in ("daily","1","price1"):
        return PRICE_DAILY,"daily"
    if p in ("monthly","2","price2"):
        return PRICE_MONTHLY,"monthly"
    if p in ("annual","yearly","3","price3"):
        return PRICE_ANNUAL,"annual"
    raise HTTPException(400,"Plan no válido.")

@app.post("/api/create-checkout-session")
async def create_checkout(data:Checkout,request:Request):
    admin,paid=cookie_access(request)
    if admin:
        return {"ok":True,"admin":True,"access":True}
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503,"Stripe no está configurado.")
    price,plan=price_for(data.plan)
    if not price:
        raise HTTPException(503,"El Price ID solicitado no está configurado.")
    try:
        mode="subscription" if plan in ("monthly","annual") else "payment"
        s=stripe.checkout.Session.create(
            mode=mode,
            line_items=[{"price":price,"quantity":1}],
            success_url=f"{APP_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?payment=cancel",
            metadata={"app":"SAVE_MEXICO_AYUDAR","plan":plan}
        )
        return {"ok":True,"url":s.url,"id":s.id,"plan":plan}
    except Exception as e:
        raise HTTPException(500,f"No se pudo crear el pago: {e}")

@app.get("/api/verify-payment")
async def verify_payment(session_id:str,request:Request):
    admin,paid=cookie_access(request)
    if admin:
        return {"ok":True,"access":True,"admin":True}
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503,"Stripe no está configurado.")
    if not session_id:
        raise HTTPException(400,"Falta session_id.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        mode=str(getattr(s,"mode",""))
        payment_status=str(getattr(s,"payment_status",""))
        if payment_status!="paid":
            if mode=="subscription":
                sub_id=getattr(s,"subscription",None)
                if not sub_id:
                    return {"ok":False,"access":False,"message":"La suscripción aún no está confirmada."}
                try:
                    sub=stripe.Subscription.retrieve(sub_id)
                    if str(getattr(sub,"status","")) not in ("active","trialing"):
                        return {"ok":False,"access":False,"message":"La suscripción aún no está activa."}
                except Exception:
                    return {"ok":False,"access":False,"message":"La suscripción aún no está confirmada."}
            else:
                return {"ok":False,"access":False,"message":"El pago aún no está confirmado."}
        token=new_token(ACCESS_TOKENS)
        plan=(getattr(s,"metadata",{}) or {}).get("plan","")
        PAYMENTS[session_id]={"created":datetime.utcnow().isoformat(),"plan":plan,"status":"paid"}
        r=JSONResponse({"ok":True,"access":True,"paid":True,"plan":plan})
        r.set_cookie("save_access_token",token,httponly=True,secure=True,samesite="lax",max_age=31536000)
        return r
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/stripe-webhook")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature","")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
        else:
            event=json.loads(payload.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400,f"Webhook inválido: {e}")
    typ=event.get("type","")
    obj=event.get("data",{}).get("object",{}) or {}
    sid=obj.get("id")
    if sid:
        meta=obj.get("metadata") or {}
        if typ in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
            PAYMENTS[sid]={"created":datetime.utcnow().isoformat(),"plan":meta.get("plan",""),"status":"paid"}
        elif typ in ("checkout.session.async_payment_failed","checkout.session.expired"):
            PAYMENTS[sid]={"created":datetime.utcnow().isoformat(),"plan":meta.get("plan",""),"status":"failed"}
    return {"received":True}

# ============================================================
# TRÁMITES
# ============================================================

@app.get("/api/tramites")
async def tramites(request:Request):
    require_access(request)
    data=load_data()
    ts=get_tramites()
    return {
        "version":data.get("version",""),
        "actualizado":data.get("actualizado",""),
        "tramites":[
            {
                "id":tid,
                "seccion":t.get("seccion",""),
                "nombre":t.get("nombre",tid),
                "nombre_corto":t.get("nombre_corto",t.get("nombre",tid)),
                "institucion":t.get("institucion",t.get("autoridad","")),
                "autoridad":t.get("autoridad",""),
                "descripcion":t.get("descripcion",""),
                "modalidades":[
                    {
                        "id":mid,
                        "seccion":m.get("seccion",""),
                        "nombre":m.get("nombre",mid),
                        "objetivo":m.get("objetivo",""),
                        "descripcion":m.get("descripcion","")
                    } for mid,m in get_modalidades(tid).items()
                ]
            } for tid,t in ts.items()
        ]
    }

@app.get("/api/modalidades")
async def modalidades(tramite:str,request:Request):
    require_access(request)
    return {
        "tramite":tramite,
        "modalidades":[
            {
                "id":mid,
                "seccion":m.get("seccion",""),
                "nombre":m.get("nombre",mid),
                "objetivo":m.get("objetivo",""),
                "descripcion":m.get("descripcion",""),
                "preguntas":len(get_questions(m)),
                "bloques_documentales":len(get_blocks(m))
            } for mid,m in get_modalidades(tramite).items()
        ]
    }

@app.get("/api/ficha-tramite")
async def ficha_tramite(tramite:str,request:Request,modalidad:Optional[str]=None):
    require_access(request)
    t=get_tramite(tramite)
    if modalidad:
        m=get_modalidad(tramite,modalidad)
        return {
            "tramite":tramite,
            "seccion":t.get("seccion",""),
            "nombre":t.get("nombre",tramite),
            "institucion":t.get("institucion",t.get("autoridad","")),
            "autoridad":t.get("autoridad",""),
            "descripcion":t.get("descripcion",""),
            "modalidad":modalidad,
            "ficha":m,
            "fuentes":t.get("fuentes",[])
        }
    return {
        "tramite":tramite,
        "seccion":t.get("seccion",""),
        "nombre":t.get("nombre",tramite),
        "institucion":t.get("institucion",t.get("autoridad","")),
        "autoridad":t.get("autoridad",""),
        "descripcion":t.get("descripcion",""),
        "modalidades":{
            k:{
                "seccion":v.get("seccion",""),
                "nombre":v.get("nombre",k),
                "objetivo":v.get("objetivo",""),
                "descripcion":v.get("descripcion","")
            } for k,v in get_modalidades(tramite).items()
        },
        "fuentes":t.get("fuentes",[])
    }

@app.get("/api/datos-personales")
async def datos_personales(request:Request):
    require_access(request)
    d=load_data().get("datos_personales",[])
    return {"datos_personales":d if isinstance(d,list) else d}

# ============================================================
# MOTOR DE CONDICIONES
# ============================================================

def values(v):
    if v is None:return []
    return v if isinstance(v,list) else [v]

def answer(data,qid):
    return data.get(qid)

def _eq(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return a==b
    if isinstance(a,(int,float)) or isinstance(b,(int,float)):
        try:return float(a)==float(b)
        except Exception:pass
    return str(a)==str(b)

def condition_match(cond,res):
    if cond is None:return True
    if isinstance(cond,bool):return cond
    if isinstance(cond,list):return all(condition_match(x,res) for x in cond)
    if not isinstance(cond,dict):return True
    if "respuesta" in cond:
        v=answer(res,cond["respuesta"])
        if "es" in cond and not _eq(v,cond["es"]):return False
        if "igual_a" in cond and not _eq(v,cond["igual_a"]):return False
        if "distinto_de" in cond and _eq(v,cond["distinto_de"]):return False
        if "no_es" in cond and _eq(v,cond["no_es"]):return False
        if "incluye" in cond and not any(_eq(x,cond["incluye"]) for x in values(v)):return False
        if "no_incluye" in cond and any(_eq(x,cond["no_incluye"]) for x in values(v)):return False
        if "en" in cond and not any(_eq(x,e) for x in values(v) for e in values(cond["en"])):return False
        if "alguno_de" in cond and not any(_eq(x,e) for x in values(v) for e in values(cond["alguno_de"])):return False
        if "todos_de" in cond and not all(any(_eq(x,e) for x in values(v)) for e in values(cond["todos_de"])):return False
        if "cantidad_mayor_que" in cond:
            if len(values(v))<=int(cond["cantidad_mayor_que"]):return False
        if "cantidad_igual_a" in cond:
            if len(values(v))!=int(cond["cantidad_igual_a"]):return False
        if "cantidad_menor_que" in cond:
            if len(values(v))>=int(cond["cantidad_menor_que"]):return False
        if "existe" in cond:
            exists=v is not None and v!="" and v!=[] and v!={}
            if bool(cond["existe"])!=exists:return False
    if "y" in cond and not condition_match(cond["y"],res):return False
    if "and" in cond:
        a=cond["and"]
        if not isinstance(a,list):a=[a]
        if not all(condition_match(x,res) for x in a):return False
    if "o" in cond and not condition_match(cond["o"],res):return False
    if "or" in cond:
        a=cond["or"]
        if not isinstance(a,list):a=[a]
        if not any(condition_match(x,res) for x in a):return False
    return True

def question_visible(q,res):
    if not isinstance(q,dict):return False
    for key in ("mostrar_si","cuando","condicion"):
        c=q.get(key)
        if c is not None and not condition_match(c,res):return False
    return True

def visible_questions(mod,res):
    return [q for q in get_questions(mod) if question_visible(q,res)]

# ============================================================
# DOCUMENTOS
# ============================================================

def document_visible(doc,res):
    for key in ("cuando","condicion","mostrar_si"):
        if key in doc and doc.get(key) is not None:
            if not condition_match(doc.get(key),res):return False
    return True

def document_items(mod,res):
    out=[]
    for b in get_blocks(mod):
        if not isinstance(b,dict):continue
        arr=b.get("documentos",[])
        if isinstance(arr,dict):arr=list(arr.values())
        if not isinstance(arr,list):continue
        for d in arr:
            if isinstance(d,dict) and document_visible(d,res):
                x=dict(d)
                x["_bloque_id"]=b.get("id",b.get("codigo",""))
                x["_bloque_seccion"]=b.get("seccion",b.get("nombre",""))
                out.append(x)
    if not out:
        for d in get_docs(mod):
            if document_visible(d,res):out.append(d)
    return out

def normalize_doc_state(v):
    s=str(v or "").strip().upper()
    return {
        "HAVE":"LO_TENGO",
        "LO_TENGO":"LO_TENGO",
        "MISSING":"NO_LO_TENGO",
        "NO_LO_TENGO":"NO_LO_TENGO",
        "UNSURE":"NO_ESTOY_SEGURO",
        "NO_ESTOY_SEGURO":"NO_ESTOY_SEGURO",
        "NA":"NO_APLICA",
        "NO_APLICA":"NO_APLICA",
        "":""
    }.get(s,s)

def document_status_map(payload):
    src=payload or {}
    if isinstance(src,dict) and "documentos" in src:src=src["documentos"]
    out={}
    if isinstance(src,dict):
        for k,v in src.items():
            if isinstance(v,dict):v=v.get("estado","")
            out[str(k)]=normalize_doc_state(v)
    elif isinstance(src,list):
        for x in src:
            if isinstance(x,dict):
                did=x.get("id") or x.get("codigo")
                if did:out[str(did)]=normalize_doc_state(x.get("estado",""))
    return out

# ============================================================
# REGLAS DEL CASO
# ============================================================

def rule_condition(rule,res):
    if not isinstance(rule,dict):return False
    for key in ("si","y","cuando","condicion"):
        if key in rule and not condition_match(rule[key],res):return False
    return True

def dynamic_situations(mod,res):
    arr=[]
    rules=mod.get("reglas",[]) if isinstance(mod,dict) else []
    if isinstance(rules,dict):rules=list(rules.values())
    for r in rules or []:
        if rule_condition(r,res):
            arr.append({"id":r.get("id",""),"accion":r.get("accion",""),"mensaje":r.get("mensaje","")})
    return arr

def unanswered_required(mod,res):
    missing=[]
    for q in visible_questions(mod,res):
        if q.get("obligatoria") is not True and q.get("required") is not True:continue
        qid=str(q.get("id",""))
        v=res.get(qid)
        if v is None or v=="" or v==[]:
            missing.append(qid)
            continue
        if isinstance(v,list) and "__OTRO__" in v and not res.get(qid+"_otro"):
            missing.append(qid)
        elif v=="__OTRO__" and not res.get(qid+"_otro"):
            missing.append(qid)
    return missing

def evaluate_case(tid,mid,res,docs_payload=None,consulado=None):
    t=get_tramite(tid)
    m=get_modalidad(tid,mid)
    res=res if isinstance(res,dict) else {}
    missing_q=unanswered_required(m,res)
    situations=dynamic_situations(m,res)
    status=document_status_map(docs_payload)
    applicable=document_items(m,res)
    faltantes=[]
    dudosos=[]
    inconsistencias=[]
    confirmar=[]

    for d in applicable:
        did=str(d.get("id") or d.get("codigo") or "")
        if not did:continue
        st=status.get(did,"")
        required=bool(d.get("obligatorio_base",d.get("obligatorio",d.get("required",False))))
        if required and st=="":
            confirmar.append({"id":did,"nombre":f"Debe indicar el estado de: {d.get('nombre',did)}"})
        if st=="NO_LO_TENGO" and required:faltantes.append(d)
        if st=="NO_ESTOY_SEGURO":dudosos.append(d)
        if d.get("confirmar") is True:confirmar.append(d)
        if st not in ("","LO_TENGO","NO_LO_TENGO","NO_ESTOY_SEGURO","NO_APLICA"):
            inconsistencias.append({"id":did,"mensaje":"Estado documental no reconocido."})

    rules=m.get("reglas",[]) if isinstance(m,dict) else []
    if isinstance(rules,dict):rules=list(rules.values())
    for r in rules or []:
        if not isinstance(r,dict) or not rule_condition(r,res):continue
        a=str(r.get("accion","")).upper()
        msg=r.get("mensaje","")
        if a=="FALTAN_DOCUMENTOS":
            if msg:faltantes.append({"id":r.get("id","REGLA"),"nombre":msg,"categoria":"REGLA","obligatorio":True})
        elif a=="HAY_INCONSISTENCIAS":
            inconsistencias.append({"id":r.get("id","REGLA"),"mensaje":msg or a})
        elif a=="REQUIERE_CONFIRMACION":
            confirmar.append({"id":r.get("id","REGLA"),"nombre":msg or "Confirmar con la autoridad."})
        elif a in ("EXIGIR_DETALLE","EXIGIR_ACLARACION"):
            inconsistencias.append({"id":r.get("id","REGLA"),"mensaje":msg or "Se requiere detalle."})

    for k,x in res.items():
        vals=values(x)
        if "NO_SE" in [str(v).upper() for v in vals]:
            confirmar.append({"id":k,"nombre":"Esta respuesta requiere confirmación."})
        if "__OTRO__" in vals or "OTRO" in [str(v).upper() for v in vals]:
            if not res.get(f"{k}_otro"):
                confirmar.append({"id":k,"nombre":"Debe explicar la opción OTRO."})

    c=consulado if isinstance(consulado,dict) else {}
    if not c.get("estado") or not c.get("ciudad") or not c.get("consulado"):
        confirmar.append({"id":"CONSULADO","nombre":"Estado, ciudad y consulado u oficina deben identificarse o confirmarse."})

    if missing_q:
        result="REQUIERE_CONFIRMACION"
    elif inconsistencias:
        result="HAY_INCONSISTENCIAS"
    elif faltantes:
        result="FALTAN_DOCUMENTOS"
    elif dudosos or confirmar:
        result="REQUIERE_CONFIRMACION"
    else:
        result="LISTO_PARA_CONFIRMAR"

    return {
        "ok":True,
        "tramite":tid,
        "modalidad":mid,
        "nombre_tramite":t.get("nombre",tid),
        "nombre_modalidad":m.get("nombre",mid),
        "resultado":result,
        "preguntas_faltantes":missing_q,
        "situaciones":situations,
        "documentos_aplicables":applicable,
        "documentos_faltantes":faltantes,
        "documentos_dudosos":dudosos,
        "inconsistencias":inconsistencias,
        "confirmaciones":confirmar,
        "consulado":c,
        "respuestas":res,
        "resultado_configurado":m.get("resultado",{})
    }

@app.post("/api/resultado-tramite")
async def resultado_tramite(data:dict,request:Request):
    require_access(request)
    tid=data.get("tramite","")
    mid=data.get("modalidad","")
    if not tid or not mid:raise HTTPException(400,"Falta trámite o modalidad.")
    res=data.get("respuestas") or data.get("datos_especificos") or {}
    docs=data.get("documentos") or {}
    return evaluate_case(tid,mid,res,docs,data.get("consulado") or {})

# ============================================================
# PDF
# ============================================================

def safe_text(v):
    if v is None:return ""
    if isinstance(v,list):return ", ".join(str(x) for x in v)
    if isinstance(v,dict):return ", ".join(f"{k}: {safe_text(x)}" for k,x in v.items())
    return str(v)

def make_pdf(data,path):
    tid=data.get("tramite","")
    mid=data.get("modalidad","")
    res=data.get("respuestas") or data.get("datos_especificos") or {}
    if not isinstance(res,dict):res={}
    docs=data.get("documentos") or []
    cons=data.get("consulado") or {}
    evaluation=evaluate_case(tid,mid,res,docs,cons)
    t=get_tramite(tid)
    m=get_modalidad(tid,mid)

    c=canvas.Canvas(str(path),pagesize=LETTER)
    width,height=LETTER
    y=height-50

    def text(txt,size=10,bold=False,space=15):
        nonlocal y
        txt=safe_text(txt)
        if not txt:return
        font="Helvetica-Bold" if bold else "Helvetica"
        for s in simpleSplit(txt,font,width-100):
            if y<55:
                c.showPage()
                y=height-50
            c.setFont(font,size)
            c.drawString(50,y,s)
            y-=space

    def title(txt):
        text(txt,12,True,18)

    text("SAVE MÉXICO AYUDAR",17,True,23)
    text("GUÍA PERSONAL DE PREPARACIÓN",13,True,20)
    text("Preparación documental individual para trámite mexicano",10,False,18)
    text(f"Fecha de preparación: {datetime.now().strftime('%Y-%m-%d %H:%M')}",9)
    text("",9,False,6)

    title("IDENTIFICACIÓN DEL TRÁMITE")
    text(f"Trámite: {t.get('nombre',tid)}")
    text(f"Modalidad: {m.get('nombre',mid)}")
    text(f"Institución: {t.get('institucion',t.get('autoridad',''))}")
    if t.get("autoridad"):text(f"Autoridad: {t.get('autoridad')}")
    if t.get("descripcion"):text(f"Descripción: {t.get('descripcion')}",9)
    text("",9,False,6)

    title("DATOS DE LA PERSONA")
    dp=data.get("datos_personales") or {}
    if dp:
        for k,v in dp.items():
            if v not in ("",None,[]):
                text(f"{k}: {safe_text(v)}",9,False,13)
    else:
        text("No se proporcionaron datos personales.",9)
    text("",9,False,6)

    title("CONSULADO U OFICINA")
    text(f"País: {cons.get('pais','Estados Unidos')}")
    text(f"Estado: {cons.get('estado','') or 'POR CONFIRMAR'}")
    text(f"Ciudad: {cons.get('ciudad','') or 'POR CONFIRMAR'}")
    text(f"Consulado u oficina: {cons.get('consulado','') or 'POR CONFIRMAR'}")
    if cons.get("direccion"):text(f"Dirección: {cons.get('direccion')}")
    text("",9,False,6)

    title("RESPUESTAS DEL CASO")
    if res:
        for k,v in res.items():
            if v not in ("",None,[]):
                text(f"{k}: {safe_text(v)}",9,False,13)
    else:
        text("No se registraron respuestas.",9)
    text("",9,False,6)

    title("DOCUMENTOS APLICABLES")
    groups={}
    for d in evaluation["documentos_aplicables"]:
        section=d.get("_bloque_seccion") or d.get("_bloque_id") or "DOCUMENTOS"
        groups.setdefault(section,[]).append(d)

    docs_status=document_status_map(docs)
    if not groups:
        text("No se encontraron documentos aplicables para esta modalidad.",9)
    else:
        for section,items in groups.items():
            text(section,11,True,17)
            for d in items:
                did=str(d.get("id") or d.get("codigo") or "")
                st=docs_status.get(did,"NO DEFINIDO")
                if st=="LO_TENGO":estado="LO TENGO"
                elif st=="NO_LO_TENGO":estado="NO LO TENGO"
                elif st=="NO_ESTOY_SEGURO":estado="NO ESTOY SEGURO"
                elif st=="NO_APLICA":estado="NO APLICA"
                else:estado="NO INDICADO"
                text(f"Documento: {did}",10,True,14)
                text(f"Nombre: {d.get('nombre',d.get('name',did))}",9,False,13)
                text(f"Categoría: {d.get('categoria','')}",9,False,13)
                text(f"Estado: {estado}",9,False,13)
                text(f"Obligatorio: {'SÍ' if d.get('obligatorio_base',d.get('obligatorio',d.get('required',False))) else 'NO'}",9,False,13)
                if d.get("motivo"):text(f"Motivo: {d.get('motivo')}",9,False,13)
                if d.get("descripcion"):text(f"Descripción: {d.get('descripcion')}",9,False,13)
                if d.get("nota"):text(f"Nota: {d.get('nota')}",9,False,13)
                if d.get("confirmar") is True:text("POR CONFIRMAR CON LA AUTORIDAD.",9,True,13)
                text("",9,False,4)

    if evaluation["documentos_faltantes"]:
        title("DOCUMENTOS FALTANTES")
        for d in evaluation["documentos_faltantes"]:
            text(f"{d.get('id','')}: {d.get('nombre',d.get('mensaje',''))}",9)
        text("",9,False,6)

    if evaluation["documentos_dudosos"]:
        title("DOCUMENTOS SOBRE LOS QUE EXISTE DUDA")
        for d in evaluation["documentos_dudosos"]:
            text(f"{d.get('id','')}: {d.get('nombre',d.get('mensaje',''))}",9)
        text("",9,False,6)

    if evaluation["inconsistencias"]:
        title("INCONSISTENCIAS")
        for x in evaluation["inconsistencias"]:
            text(f"{x.get('id','')}: {x.get('mensaje','')}",9)
        text("",9,False,6)

    if evaluation["confirmaciones"]:
        title("PUNTOS POR CONFIRMAR")
        seen=set()
        for x in evaluation["confirmaciones"]:
            key=(x.get("id",""),x.get("nombre",x.get("mensaje","")))
            if key in seen:continue
            seen.add(key)
            text(f"{x.get('id','')}: {x.get('nombre',x.get('mensaje',''))}",9)
        text("",9,False,6)

    title("RESULTADO FINAL")
    text(evaluation["resultado"],11,True,17)
    if evaluation["preguntas_faltantes"]:
        text("Preguntas obligatorias pendientes: "+", ".join(evaluation["preguntas_faltantes"]),9)
    rc=m.get("resultado",{})
    if isinstance(rc,dict):
        for k,v in rc.items():
            if v not in ("",None,[]):
                text(f"{k}: {safe_text(v)}",9,False,13)

    text("",9,False,6)
    title("AVISO IMPORTANTE")
    text("SAVE MÉXICO AYUDAR no es una oficina del Gobierno de México, la SRE ni el INE.",9)
    text("Esta guía es un servicio privado de preparación y organización de información.",9)
    text("Los requisitos, documentos aceptados, citas, tarifas, horarios y procedimientos pueden cambiar.",9)
    text("La información debe confirmarse con la autoridad competente antes de acudir.",9)

    c.save()
    return path

@app.post("/api/generar-guia-consular")
async def generar_guia(data:Guide,request:Request):
    require_access(request)
    if not data.tramite or not data.modalidad:
        raise HTTPException(400,"Debe indicar trámite y modalidad.")

    res=data.respuestas or data.datos_especificos or {}
    docs=data.documentos or []
    result=evaluate_case(data.tramite,data.modalidad,res,docs,data.consulado or {})

    if result["preguntas_faltantes"]:
        raise HTTPException(400,"Faltan respuestas obligatorias antes de generar la guía.")

    if result["resultado"]=="HAY_INCONSISTENCIAS":
        raise HTTPException(400,"Existen inconsistencias que deben aclararse antes de generar la guía.")

    name=f"guia_{uuid.uuid4().hex}.pdf"
    path=OUT/name
    payload=data.model_dump() if hasattr(data,"model_dump") else data.dict()
    payload["respuestas"]=res
    payload["documentos"]=docs
    payload["resultado_evaluacion"]=result

    try:
        make_pdf(payload,path)
    except Exception as e:
        if path.exists():
            path.unlink(missing_ok=True)
        raise HTTPException(500,f"No se pudo generar el PDF: {e}")

    if not path.exists():
        raise HTTPException(500,"El PDF no fue creado correctamente.")

    return {
        "ok":True,
        "filename":name,
        "archivo":name,
        "file":name,
        "pdf":name,
        "url":f"/descargar/{name}",
        "resultado":result["resultado"]
    }

@app.get("/descargar/{name}")
async def descargar(name:str,request:Request):
    require_access(request)
    name=Path(name).name
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400,"Archivo inválido.")
    p=OUT/name
    if not p.exists() or not p.is_file():
        raise HTTPException(404,"Archivo PDF no encontrado.")
    return FileResponse(str(p),media_type="application/pdf",filename="SAVE_MEXICO_AYUDAR_GUIA.pdf")

# ============================================================
# SUBIR DOCUMENTOS
# ============================================================

@app.post("/api/subir-documento")
async def subir_documento(request:Request,file:UploadFile=File(...)):
    require_access(request)
    if not file.filename:
        raise HTTPException(400,"Archivo no válido.")
    ext=Path(file.filename).suffix.lower()
    if ext not in (".pdf",".jpg",".jpeg",".png"):
        raise HTTPException(400,"Solo se permiten PDF, JPG, JPEG o PNG.")
    raw=await file.read()
    if len(raw)>15*1024*1024:
        raise HTTPException(400,"El archivo supera 15 MB.")
    name=f"{uuid.uuid4().hex}{ext}"
    path=OUT/name
    path.write_bytes(raw)
    pages=None
    if ext==".pdf":
        try:pages=len(PdfReader(str(path)).pages)
        except Exception:pages=None
    return {"ok":True,"archivo":name,"filename":name,"paginas":pages}

# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    data=load_data()
    ts=get_tramites()
    return {
        "ok":True,
        "app":"SAVE MÉXICO AYUDAR",
        "version":"5.1.0",
        "datos_version":data.get("version",""),
        "datos_actualizado":data.get("actualizado",""),
        "estructura_tramites":type(data.get("tramites")).__name__,
        "cantidad_tramites":len(ts),
        "tramites":list(ts.keys()),
        "modalidades":{tid:list(get_modalidades(tid).keys()) for tid in ts},
        "stripe":bool(STRIPE_SECRET_KEY),
        "stripe_webhook":bool(STRIPE_WEBHOOK_SECRET),
        "admin_configured":bool(ADMIN_USERNAME and ADMIN_PASSWORD),
        "price_daily":bool(PRICE_DAILY),
        "price_monthly":bool(PRICE_MONTHLY),
        "price_annual":bool(PRICE_ANNUAL)
    }

# ============================================================
# INICIO
# ============================================================

@app.get("/")
async def index():
    p=STATIC/"index.html"
    if not p.exists():
        raise HTTPException(404,"No existe static/index.html.")
    return FileResponse(str(p),media_type="text/html")

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
