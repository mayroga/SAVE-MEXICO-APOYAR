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
PRICE_ANNUAL=os.getenv("STRIPE_PRICE_ID_ANNUAL","")

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
    documentos:dict=Field(default_factory=dict)
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
        return list(value.items())
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
    data=load_data()
    return dict(_items(data.get("tramites",[])))

def get_tramite(tid):
    t=get_tramites().get(tid)
    if not isinstance(t,dict):
        raise HTTPException(404,"Trámite no encontrado.")
    return t

def get_modalidades(tid):
    t=get_tramite(tid)
    return dict(_items(t.get("modalidades",[])))

def get_modalidad(tid,mid):
    m=get_modalidades(tid).get(mid)
    if not isinstance(m,dict):
        raise HTTPException(404,"Modalidad no encontrada.")
    return m

def get_blocks(mod):
    return mod.get("bloques_documentales",[]) if isinstance(mod,dict) else []

def get_questions(mod):
    return mod.get("preguntas",[]) if isinstance(mod,dict) else []

def get_docs(mod):
    out=[]
    for b in get_blocks(mod):
        if not isinstance(b,dict): continue
        for d in b.get("documentos",[]) or []:
            if isinstance(d,dict):
                x=dict(d)
                x["_bloque_id"]=b.get("id","")
                x["_bloque_seccion"]=b.get("seccion","")
                out.append(x)
    return out

# ============================================================
# AUTENTICACIÓN / ACCESO
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
    if not secrets.compare_digest(data.username,ADMIN_USERNAME) or not secrets.compare_digest(data.password,ADMIN_PASSWORD):
        raise HTTPException(401,"Usuario o contraseña incorrectos.")
    token=new_token(ADMIN_TOKENS)
    r=JSONResponse({"ok":True,"access":True,"admin":True,"message":"Acceso administrativo autorizado."})
    r.set_cookie("save_admin_token",token,httponly=True,secure=True,samesite="lax",max_age=86400)
    return r

@app.post("/api/logout")
async def logout(request:Request):
    a=request.cookies.get("save_admin_token")
    p=request.cookies.get("save_access_token")
    ADMIN_TOKENS.discard(a)
    ACCESS_TOKENS.discard(p)
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
    p=str(plan or "").lower()
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
        session=stripe.checkout.Session.create(
            mode="subscription" if plan=="monthly" else "payment",
            line_items=[{"price":price,"quantity":1}],
            success_url=f"{APP_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?payment=cancel",
            metadata={"app":"SAVE_MEXICO_AYUDAR","plan":plan}
        )
        return {"ok":True,"url":session.url,"id":session.id}
    except Exception as e:
        raise HTTPException(500,f"No se pudo crear el pago: {e}")

@app.get("/api/verify-payment")
async def verify_payment(session_id:str,request:Request):
    admin,paid=cookie_access(request)
    if admin:
        return {"ok":True,"access":True,"admin":True}
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503,"Stripe no está configurado.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        if s.payment_status!="paid" and s.mode!="subscription":
            return {"ok":False,"access":False,"message":"El pago aún no está confirmado."}
        token=new_token(ACCESS_TOKENS)
        r=JSONResponse({"ok":True,"access":True,"paid":True})
        r.set_cookie("save_access_token",token,httponly=True,secure=True,samesite="lax",max_age=31536000)
        PAYMENTS[session_id]={"created":datetime.utcnow().isoformat(),"plan":(s.metadata or {}).get("plan","")}
        return r
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/stripe-webhook")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature","")
    if STRIPE_WEBHOOK_SECRET:
        try:
            event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            raise HTTPException(400,f"Webhook inválido: {e}")
    else:
        try:
            event=json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(400,"Webhook inválido.")
    typ=event.get("type","")
    obj=event.get("data",{}).get("object",{})
    if typ in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        sid=obj.get("id")
        if sid:
            PAYMENTS[sid]={"created":datetime.utcnow().isoformat(),"plan":(obj.get("metadata") or {}).get("plan","")}
    return {"received":True}

# ============================================================
# TRÁMITES
# ============================================================

@app.get("/api/tramites")
async def tramites(request:Request):
    require_access(request)
    ts=get_tramites()
    return {
        "version":load_data().get("version",""),
        "actualizado":load_data().get("actualizado",""),
        "tramites":[
            {
                "id":tid,
                "seccion":t.get("seccion",""),
                "nombre":t.get("nombre",tid),
                "nombre_corto":t.get("nombre_corto",t.get("nombre",tid)),
                "institucion":t.get("institucion",""),
                "descripcion":t.get("descripcion",""),
                "modalidades":[
                    {
                        "id":mid,
                        "seccion":m.get("seccion",""),
                        "nombre":m.get("nombre",mid),
                        "objetivo":m.get("objetivo",""),
                        "descripcion":m.get("descripcion","")
                    }
                    for mid,m in get_modalidades(tid).items()
                ]
            }
            for tid,t in ts.items()
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
            }
            for mid,m in get_modalidades(tramite).items()
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
            "institucion":t.get("institucion",""),
            "descripcion":t.get("descripcion",""),
            "modalidad":modalidad,
            "ficha":m
        }
    return {
        "tramite":tramite,
        "seccion":t.get("seccion",""),
        "nombre":t.get("nombre",tramite),
        "institucion":t.get("institucion",""),
        "descripcion":t.get("descripcion",""),
        "modalidades":{
            k:{
                "seccion":v.get("seccion",""),
                "nombre":v.get("nombre",k),
                "objetivo":v.get("objetivo",""),
                "descripcion":v.get("descripcion","")
            }
            for k,v in get_modalidades(tramite).items()
        }
    }

# ============================================================
# MOTOR DE CONDICIONES
# ============================================================

def values(v):
    if v is None:return []
    return v if isinstance(v,list) else [v]

def answer(data,qid):
    return data.get(qid)

def condition_match(cond,res):
    if cond is None:return True
    if isinstance(cond,bool):return cond
    if isinstance(cond,list):return all(condition_match(x,res) for x in cond)
    if not isinstance(cond,dict):return True

    if "respuesta" in cond:
        v=answer(res,cond["respuesta"])
        if "es" in cond and v!=cond["es"]:return False
        if "igual_a" in cond and v!=cond["igual_a"]:return False
        if "distinto_de" in cond and v==cond["distinto_de"]:return False
        if "no_es" in cond and v==cond["no_es"]:return False
        if "incluye" in cond and cond["incluye"] not in values(v):return False
        if "no_incluye" in cond and cond["no_incluye"] in values(v):return False
        if "en" in cond and not any(x in cond["en"] for x in values(v)):return False
        if "alguno_de" in cond and not any(x in cond["alguno_de"] for x in values(v)):return False
        if "todos_de" in cond and not all(x in values(v) for x in cond["todos_de"]):return False
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
    if "and" in cond and not all(condition_match(x,res) for x in cond["and"]):return False
    if "o" in cond and not condition_match(cond["o"],res):return False
    if "or" in cond and not any(condition_match(x,res) for x in cond["or"]):return False
    return True

def question_visible(q,res):
    c=q.get("mostrar_si")
    if c is not None and not condition_match(c,res):return False
    c=q.get("cuando")
    if c is not None and not condition_match(c,res):return False
    return True

def visible_questions(mod,res):
    return [q for q in get_questions(mod) if question_visible(q,res)]

# ============================================================
# DOCUMENTOS
# ============================================================

def document_visible(doc,res):
    c=doc.get("cuando",doc.get("condicion",True))
    return condition_match(c,res)

def document_items(mod,res):
    out=[]
    for b in get_blocks(mod):
        if not isinstance(b,dict):continue
        for d in b.get("documentos",[]) or []:
            if not isinstance(d,dict):continue
            if document_visible(d,res):
                x=dict(d)
                x["_bloque_id"]=b.get("id","")
                x["_bloque_seccion"]=b.get("seccion","")
                out.append(x)
    return out

def document_status_map(payload):
    src=payload or {}
    if isinstance(src,dict) and "documentos" in src:
        src=src["documentos"]
    out={}
    if isinstance(src,dict):
        for k,v in src.items():
            if isinstance(v,dict):
                out[str(k)]=str(v.get("estado",""))
            else:
                out[str(k)]=str(v)
    elif isinstance(src,list):
        for x in src:
            if isinstance(x,dict) and x.get("id"):
                out[str(x["id"])]=str(x.get("estado",""))
    return out

# ============================================================
# REGLAS DEL CASO
# ============================================================

def rule_condition(rule,res):
    if not isinstance(rule,dict):return False
    ok=True
    if "si" in rule:ok=ok and condition_match(rule["si"],res)
    if "y" in rule:ok=ok and condition_match(rule["y"],res)
    if "cuando" in rule:ok=ok and condition_match(rule["cuando"],res)
    return ok

def dynamic_situations(mod,res):
    arr=[]
    for r in mod.get("reglas",[]) or []:
        if rule_condition(r,res):
            arr.append({
                "id":r.get("id",""),
                "accion":r.get("accion",""),
                "mensaje":r.get("mensaje","")
            })
    return arr

def unanswered_required(mod,res):
    missing=[]
    for q in visible_questions(mod,res):
        if q.get("obligatoria") is True:
            v=res.get(q.get("id"))
            if v is None or v=="" or v==[]:
                missing.append(q.get("id"))
            elif isinstance(v,list) and "__OTRO__" in v and not res.get(q.get("id")+"_otro"):
                missing.append(q.get("id"))
            elif v=="__OTRO__" and not res.get(q.get("id")+"_otro"):
                missing.append(q.get("id"))
    return missing

def evaluate_case(tid,mid,res,docs_payload=None,consulado=None):
    t=get_tramite(tid)
    m=get_modalidad(tid,mid)
    missing_q=unanswered_required(m,res)
    situations=dynamic_situations(m,res)
    status=document_status_map(docs_payload)
    applicable=document_items(m,res)

    faltantes=[]
    dudosos=[]
    inconsistencias=[]
    confirmar=[]

    for d in applicable:
        did=d.get("id","")
        st=status.get(did,"")
        required=bool(d.get("obligatorio_base",False))
        if st=="NO_LO_TENGO" and required:
            faltantes.append(d)
        if st=="NO_ESTOY_SEGURO":
            dudosos.append(d)
        if d.get("confirmar") is True:
            confirmar.append(d)
        if st not in ("LO_TENGO","NO_LO_TENGO","NO_ESTOY_SEGURO","NO_APLICA",""):
            inconsistencias.append({
                "id":did,
                "mensaje":"Estado documental no reconocido."
            })

    for r in m.get("reglas",[]) or []:
        if not rule_condition(r,res):continue
        a=r.get("accion","")
        msg=r.get("mensaje","")
        if a=="FALTAN_DOCUMENTOS":
            if msg: faltantes.append({"id":r.get("id","REGLA"),"nombre":msg,"categoria":"REGLA"})
        elif a=="HAY_INCONSISTENCIAS":
            inconsistencias.append({"id":r.get("id","REGLA"),"mensaje":msg or a})
        elif a=="REQUIERE_CONFIRMACION":
            confirmar.append({"id":r.get("id","REGLA"),"nombre":msg or "Confirmar con la autoridad"})
        elif a=="EXIGIR_DETALLE":
            inconsistencias.append({"id":r.get("id","REGLA"),"mensaje":msg or "Se requiere detalle."})

    for x in res.values():
        if isinstance(x,list) and "NO_SE" in x:
            confirmar.append({"id":"RESPUESTA","nombre":"Existe una respuesta NO_SE que requiere aclaración."})
        elif x=="NO_SE":
            confirmar.append({"id":"RESPUESTA","nombre":"Existe una respuesta NO_SE que requiere aclaración."})

    if any(isinstance(x,list) and "OTRO" in x for x in res.values()):
        confirmar.append({"id":"OTRO","nombre":"Debe explicarse la opción OTRO."})

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

    c=consulado or {}
    if not c.get("estado") or not c.get("ciudad") or not c.get("consulado"):
        confirmar.append({
            "id":"CONSULADO",
            "nombre":"Estado, ciudad y consulado u oficina deben quedar identificados o confirmarse."
        })
        if result=="LISTO_PARA_CONFIRMAR":
            result="REQUIERE_CONFIRMACION"

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
    if not tid or not mid:
        raise HTTPException(400,"Falta trámite o modalidad.")
    res=data.get("respuestas") or data.get("datos_especificos") or {}
    docs=data.get("documentos") or {}
    return evaluate_case(tid,mid,res,docs,data.get("consulado") or {})

# ============================================================
# PDF
# ============================================================

def pdf_document(c,d):
    y=c["y"]
    page=c["page"]
    width=c["width"]
    def line(txt,size=10,bold=False,space=15):
        nonlocal y
        if y<55:
            c["c"].showPage()
            y=LETTER[1]-55
        c["c"].setFont("Helvetica-Bold" if bold else "Helvetica",size)
        for s in simpleSplit(str(txt), "Helvetica-Bold" if bold else "Helvetica", width-100):
            c["c"].drawString(50,y,s)
            y-=space
        return y
    line(f"DOCUMENTO: {d.get('id','')}",11,True,16)
    line(f"Nombre: {d.get('nombre','')}",10)
    line(f"Categoría: {d.get('categoria','')}",10)
    line(f"Sección: {d.get('_bloque_seccion','')}",10)
    line(f"Estado: {d.get('estado','NO DEFINIDO')}",10)
    line(f"Obligatorio: {'SÍ' if d.get('obligatorio') else 'NO'}",10)
    if d.get("motivo"):line(f"Motivo: {d['motivo']}",10)
    if d.get("nota"):line(f"Nota: {d['nota']}",10)
    if d.get("confirmar"):line("POR CONFIRMAR CON LA AUTORIDAD.",10,True)
    line("",10,False,8)
    return y

def make_pdf(data,path):
    tid=data.get("tramite","")
    mid=data.get("modalidad","")
    res=data.get("respuestas") or data.get("datos_especificos") or {}
    docs_status=document_status_map(data.get("documentos") or {})
    cons=data.get("consulado") or {}
    evaluation=evaluate_case(tid,mid,res,data.get("documentos") or {},cons)
    t=get_tramite(tid)
    m=get_modalidad(tid,mid)

    c=canvas.Canvas(str(path),pagesize=LETTER)
    width,height=LETTER
    y=height-50

    def text(txt,size=10,bold=False,space=15):
        nonlocal y
        font="Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font,size)
        for s in simpleSplit(str(txt),font,width-100):
            if y<55:
                c.showPage()
                y=height-50
                c.setFont(font,size)
            c.drawString(50,y,s)
            y-=space

    text("SAVE MÉXICO AYUDAR",17,True,23)
    text("GUÍA PERSONAL DE PREPARACIÓN",13,True,20)
    text("Preparación documental individual para trámite mexicano",10,False,18)
    text(f"Fecha de preparación: {datetime.now().strftime('%Y-%m-%d %H:%M')}",9)
    text("",9,False,8)

    text("IDENTIFICACIÓN DEL TRÁMITE",12,True,18)
    text(f"Trámite: {t.get('nombre',tid)}")
    text(f"Modalidad: {m.get('nombre',mid)}")
    text(f"Institución: {t.get('institucion','')}")
    text("",9,False,8)

    text("SITUACIÓN DE LA PERSONA",12,True,18)
    dp=data.get("datos_personales") or {}
    for k,v in dp.items():
        if v not in ("",None,[]):
            text(f"{k}: {', '.join(map(str,v)) if isinstance(v,list) else v}",9)
    text("",9,False,8)

    text("CONSULADO U OFICINA",12,True,18)
    text(f"País: {cons.get('pais','Estados Unidos')}")
    text(f"Estado: {cons.get('estado','')}")
    text(f"Ciudad: {cons.get('ciudad','')}")
    text(f"Consulado u oficina: {cons.get('consulado','')}")
    text("",9,False,8)

    text("RESPUESTAS RELEVANTES",12,True,18)
    for k,v in res.items():
        if v not in ("",None,[]):
            val=", ".join(map(str,v)) if isinstance(v,list) else str(v)
            text(f"{k}: {val}",9,False,13)

    text("",9,False,8)
    text("DOCUMENTOS APLICABLES",12,True,18)

    groups={}
    for d in evaluation["documentos_aplicables"]:
        b=d.get("_bloque_seccion","")
        groups.setdefault(b,[]).append(d)

    for section,items in groups.items():
        text(section,11,True,17)
        for d in items:
            did=d.get("id","")
            estado=docs_status.get(did,"NO DEFINIDO")
            x=dict(d)
            x["estado"]=estado
            x["obligatorio"]=bool(d.get("obligatorio_base",False))
            pdf_document({"c":c,"y":y,"width":width,"page":None},x)
            y=height-50 if y<55 else y
        text("",9,False,5)

    if evaluation["documentos_faltantes"]:
        text("DOCUMENTOS FALTANTES",12,True,18)
        for d in evaluation["documentos_faltantes"]:
            text(f"{d.get('id','')}: {d.get('nombre',d.get('mensaje',''))}",10)
        text("",9,False,7)

    if evaluation["documentos_dudosos"]:
        text("DOCUMENTOS DUDOSOS",12,True,18)
        for d in evaluation["documentos_dudosos"]:
            text(f"{d.get('id','')}: {d.get('nombre','')}",10)
        text("",9,False,7)

    if evaluation["inconsistencias"]:
        text("INCONSISTENCIAS",12,True,18)
        for x in evaluation["inconsistencias"]:
            text(f"{x.get('id','')}: {x.get('mensaje','')}",10)
        text("",9,False,7)

    if evaluation["confirmaciones"]:
        text("PUNTOS POR CONFIRMAR",12,True,18)
        for x in evaluation["confirmaciones"]:
            text(f"{x.get('id','')}: {x.get('nombre',x.get('mensaje',''))}",10)
        text("",9,False,7)

    text("RESULTADO FINAL",12,True,18)
    text(evaluation["resultado"],11,True)
    rc=m.get("resultado",{})
    if isinstance(rc,dict):
        for k,v in rc.items():
            if v not in ("",None):
                text(f"{k}: {v}",9)

    text("",9,False,8)
    text("AVISO",12,True,18)
    text("SAVE MÉXICO AYUDAR no es una oficina del Gobierno de México, la SRE ni el INE.",9)
    text("Esta guía es una preparación privada. Los requisitos, documentos aceptados, citas, tarifas y procedimientos pueden cambiar.",9)
    text("La información debe confirmarse con la autoridad competente antes de acudir.",9)

    c.save()
    return path

@app.post("/api/generar-guia-consular")
async def generar_guia(data:Guide,request:Request):
    require_access(request)
    if not data.tramite or not data.modalidad:
        raise HTTPException(400,"Debe indicar trámite y modalidad.")

    result=evaluate_case(
        data.tramite,
        data.modalidad,
        data.respuestas or data.datos_especificos,
        data.documentos,
        data.consulado
    )

    if result["preguntas_faltantes"]:
        raise HTTPException(400,"Faltan respuestas obligatorias.")
    if result["resultado"]=="HAY_INCONSISTENCIAS":
        raise HTTPException(400,"Existen inconsistencias que deben aclararse antes de generar la guía.")

    name=f"guia_{uuid.uuid4().hex}.pdf"
    path=OUT/name
    payload=data.model_dump()
    payload["resultado_evaluacion"]=result
    make_pdf(payload,path)

    return {
        "ok":True,
        "archivo":name,
        "url":f"/descargar/{name}",
        "resultado":result["resultado"]
    }

@app.get("/descargar/{name}")
async def descargar(name:str,request:Request):
    require_access(request)
    if Path(name).name!=name:
        raise HTTPException(400,"Archivo inválido.")
    p=OUT/name
    if not p.exists():
        raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(
        str(p),
        media_type="application/pdf",
        filename="SAVE_MEXICO_AYUDAR_GUIA.pdf"
    )

# ============================================================
# CARGA / LECTURA DE DOCUMENTOS DEL USUARIO
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
        try:
            pages=len(PdfReader(str(path)).pages)
        except Exception:
            pages=None
    return {"ok":True,"archivo":name,"paginas":pages}

# ============================================================
# SALUD DEL SISTEMA
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
        "modalidades":{
            tid:list(get_modalidades(tid).keys())
            for tid in ts
        },
        "stripe":bool(STRIPE_SECRET_KEY),
        "stripe_webhook":bool(STRIPE_WEBHOOK_SECRET),
        "admin_configured":bool(ADMIN_USERNAME and ADMIN_PASSWORD)
    }

# ============================================================
# INICIO
# ============================================================

@app.get("/")
async def index():
    p=STATIC/"index.html"
    if not p.exists():
        raise HTTPException(404,"No existe static/index.html.")
    return FileResponse(str(p))

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
