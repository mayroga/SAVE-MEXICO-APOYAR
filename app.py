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

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="5.1.1")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")

ADMIN_TOKENS=set()
ACCESS_TOKENS=set()
PAYMENTS={}

# ============================================================
# MODELOS
# ============================================================

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
    documentos:list[Any]=Field(default_factory=list)
    documentos_disponibles:list[Any]=Field(default_factory=list)
    documentos_faltantes:list[Any]=Field(default_factory=list)
    documentos_dudosos:list[Any]=Field(default_factory=list)
    situaciones:list[Any]=Field(default_factory=list)
    aclaraciones:list[Any]=Field(default_factory=list)
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
    x=mod.get("bloques_documentales",mod.get("bloques",[]))
    return x if isinstance(x,list) else list(x.values()) if isinstance(x,dict) else []

def get_questions(mod):
    x=mod.get("preguntas",mod.get("preguntas_situacion",mod.get("preguntas_especificas",[])))
    return x if isinstance(x,list) else list(x.values()) if isinstance(x,dict) else []

def get_docs(mod):
    out=[]
    for b in get_blocks(mod):
        if not isinstance(b,dict):continue
        arr=b.get("documentos",[])
        if isinstance(arr,dict):arr=list(arr.values())
        for d in arr if isinstance(arr,list) else []:
            if isinstance(d,dict):
                x=dict(d)
                x["_bloque_id"]=b.get("id",b.get("codigo",""))
                x["_bloque_seccion"]=b.get("seccion",b.get("nombre",""))
                out.append(x)
    if not out:
        arr=mod.get("documentos",[])
        if isinstance(arr,dict):arr=list(arr.values())
        for d in arr if isinstance(arr,list) else []:
            if isinstance(d,dict):out.append(dict(d))
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
    if not secrets.compare_digest(data.username,ADMIN_USERNAME) or not secrets.compare_digest(data.password,ADMIN_PASSWORD):
        raise HTTPException(401,"Usuario o contraseña incorrectos.")
    token=new_token(ADMIN_TOKENS)
    r=JSONResponse({"ok":True,"access":True,"admin":True})
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
        return PRICE_DAILY,"daily","payment"
    if p in ("monthly","2","price2"):
        return PRICE_MONTHLY,"monthly","subscription"
    if p in ("annual","yearly","3","price3"):
        return PRICE_ANNUAL,"annual","subscription"
    raise HTTPException(400,"Plan no válido.")

@app.post("/api/create-checkout-session")
async def create_checkout(data:Checkout,request:Request):
    admin,paid=cookie_access(request)
    if admin:
        return {"ok":True,"admin":True,"access":True}
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503,"Stripe no está configurado.")
    price,plan,mode=price_for(data.plan)
    if not price:
        raise HTTPException(503,"El Price ID solicitado no está configurado.")
    try:
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
        payment_ok=(s.payment_status=="paid")
        if not payment_ok:
            return {"ok":False,"access":False,"message":"El pago aún no está confirmado."}

        plan=(s.metadata or {}).get("plan","")
        sid=str(s.id)

        PAYMENTS[sid]={
            "created":datetime.utcnow().isoformat(),
            "plan":plan,
            "payment_status":s.payment_status,
            "status":s.status
        }

        if sid not in PAYMENTS:
            raise HTTPException(400,"Pago no confirmado.")

        token=new_token(ACCESS_TOKENS)
        r=JSONResponse({
            "ok":True,
            "access":True,
            "paid":True,
            "plan":plan
        })
        r.set_cookie(
            "save_access_token",
            token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=31536000
        )
        return r
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/stripe-webhook")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature","")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event=stripe.Webhook.construct_event(
                payload,sig,STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            raise HTTPException(400,f"Webhook inválido: {e}")
    else:
        try:
            event=json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(400,"Webhook inválido.")

    typ=event.get("type","")
    obj=event.get("data",{}).get("object",{})

    if typ in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded"
    ):
        sid=obj.get("id")
        if sid:
            PAYMENTS[sid]={
                "created":datetime.utcnow().isoformat(),
                "plan":(obj.get("metadata") or {}).get("plan",""),
                "payment_status":obj.get("payment_status",""),
                "status":obj.get("status","")
            }

    if typ in ("checkout.session.async_payment_failed",):
        sid=obj.get("id")
        if sid:
            PAYMENTS[sid]={
                "created":datetime.utcnow().isoformat(),
                "plan":(obj.get("metadata") or {}).get("plan",""),
                "payment_status":"failed",
                "status":obj.get("status","")
            }

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
async def ficha_tramite(
    tramite:str,
    request:Request,
    modalidad:Optional[str]=None
):
    require_access(request)
    t=get_tramite(tramite)

    if modalidad:
        m=get_modalidad(tramite,modalidad)
        return {
            "tramite":tramite,
            "seccion":t.get("seccion",""),
            "nombre":t.get("nombre",tramite),
            "institucion":t.get("institucion",t.get("autoridad","")),
            "descripcion":t.get("descripcion",""),
            "modalidad":modalidad,
            "ficha":m
        }

    return {
        "tramite":tramite,
        "seccion":t.get("seccion",""),
        "nombre":t.get("nombre",tramite),
        "institucion":t.get("institucion",t.get("autoridad","")),
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

@app.get("/api/datos-personales")
async def datos_personales(request:Request):
    require_access(request)
    d=load_data().get("datos_personales",[])
    return {"datos_personales":d}

# ============================================================
# CONDICIONES
# ============================================================

def values(v):
    if v is None:return []
    return v if isinstance(v,list) else [v]

def answer(data,qid):
    return data.get(qid)

def condition_match(cond,res):
    if cond is None:return True
    if isinstance(cond,bool):return cond
    if isinstance(cond,list):
        return all(condition_match(x,res) for x in cond)
    if not isinstance(cond,dict):return True

    if "respuesta" in cond:
        v=answer(res,cond["respuesta"])
        vals=values(v)

        if "es" in cond and v!=cond["es"]:return False
        if "igual_a" in cond and v!=cond["igual_a"]:return False
        if "distinto_de" in cond and v==cond["distinto_de"]:return False
        if "no_es" in cond and v==cond["no_es"]:return False
        if "incluye" in cond and cond["incluye"] not in vals:return False
        if "no_incluye" in cond and cond["no_incluye"] in vals:return False
        if "en" in cond and not any(x in cond["en"] for x in vals):return False
        if "alguno_de" in cond and not any(x in cond["alguno_de"] for x in vals):return False
        if "todos_de" in cond and not all(x in vals for x in cond["todos_de"]):return False

        if "cantidad_mayor_que" in cond:
            if len(vals)<=int(cond["cantidad_mayor_que"]):return False
        if "cantidad_igual_a" in cond:
            if len(vals)!=int(cond["cantidad_igual_a"]):return False
        if "cantidad_menor_que" in cond:
            if len(vals)>=int(cond["cantidad_menor_que"]):return False

        if "existe" in cond:
            exists=v is not None and v!="" and v!=[] and v!={}
            if bool(cond["existe"])!=exists:return False

    if "y" in cond and not condition_match(cond["y"],res):
        return False
    if "and" in cond:
        arr=cond["and"] if isinstance(cond["and"],list) else [cond["and"]]
        if not all(condition_match(x,res) for x in arr):return False
    if "o" in cond and not condition_match(cond["o"],res):
        return False
    if "or" in cond:
        arr=cond["or"] if isinstance(cond["or"],list) else [cond["or"]]
        if not any(condition_match(x,res) for x in arr):return False

    return True

def question_visible(q,res):
    if not isinstance(q,dict):return False
    for key in ("mostrar_si","cuando","condicion"):
        if key in q and not condition_match(q[key],res):
            return False
    return True

def visible_questions(mod,res):
    return [q for q in get_questions(mod) if question_visible(q,res)]

# ============================================================
# DOCUMENTOS
# ============================================================

def document_visible(doc,res):
    c=doc.get("cuando",doc.get("mostrar_si",doc.get("condicion",True)))
    return condition_match(c,res)

def document_items(mod,res):
    out=[]
    for b in get_blocks(mod):
        if not isinstance(b,dict):continue
        arr=b.get("documentos",[])
        if isinstance(arr,dict):arr=list(arr.values())
        if not isinstance(arr,list):continue

        for d in arr:
            if not isinstance(d,dict) or not document_visible(d,res):
                continue
            x=dict(d)
            x["_bloque_id"]=b.get("id",b.get("codigo",""))
            x["_bloque_seccion"]=b.get("seccion",b.get("nombre",""))
            out.append(x)

    if not out:
        arr=mod.get("documentos",[])
        if isinstance(arr,dict):arr=list(arr.values())
        for d in arr if isinstance(arr,list) else []:
            if isinstance(d,dict) and document_visible(d,res):
                out.append(dict(d))

    return out

def canonical_doc_state(v):
    s=str(v or "").strip().upper()
    return {
        "HAVE":"LO_TENGO",
        "MISSING":"NO_LO_TENGO",
        "UNSURE":"NO_ESTOY_SEGURO",
        "NA":"NO_APLICA",
        "LO_TENGO":"LO_TENGO",
        "NO_LO_TENGO":"NO_LO_TENGO",
        "NO_ESTOY_SEGURO":"NO_ESTOY_SEGURO",
        "NO_APLICA":"NO_APLICA",
        "LO TENGO":"LO_TENGO",
        "NO LO TENGO":"NO_LO_TENGO",
        "NO ESTOY SEGURO":"NO_ESTOY_SEGURO",
        "NO APLICA":"NO_APLICA"
    }.get(s,s)

def document_status_map(payload):
    src=payload or {}

    if isinstance(src,dict) and "documentos" in src:
        src=src["documentos"]

    out={}

    if isinstance(src,dict):
        for k,v in src.items():
            if isinstance(v,dict):
                out[str(k)]=canonical_doc_state(v.get("estado",""))
            else:
                out[str(k)]=canonical_doc_state(v)

    elif isinstance(src,list):
        for x in src:
            if isinstance(x,dict):
                did=x.get("id") or x.get("codigo")
                if did:
                    out[str(did)]=canonical_doc_state(x.get("estado",""))

    return out

# ============================================================
# REGLAS
# ============================================================

def rule_condition(rule,res):
    if not isinstance(rule,dict):return False
    for key in ("si","y","cuando"):
        if key in rule and not condition_match(rule[key],res):
            return False
    return True

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
        if q.get("obligatoria",q.get("required",False)) is not True:
            continue

        qid=str(q.get("id",""))
        v=res.get(qid)

        if v is None or v=="" or v==[]:
            missing.append(qid)
            continue

        if isinstance(v,list) and "__OTRO__" in v:
            if not str(res.get(qid+"_otro","")).strip():
                missing.append(qid)
                continue

        if v=="__OTRO__" and not str(res.get(qid+"_otro","")).strip():
            missing.append(qid)

    return missing

def answer_has(res,value):
    for x in res.values():
        if isinstance(x,list) and value in x:return True
        if x==value:return True
    return False

def evaluate_case(tid,mid,res,docs_payload=None,consulado=None):
    t=get_tramite(tid)
    m=get_modalidad(tid,mid)

    res=res if isinstance(res,dict) else {}
    consulado=consulado if isinstance(consulado,dict) else {}

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
        required=bool(
            d.get("obligatorio_base") is True or
            d.get("obligatorio") is True or
            d.get("required") is True
        )

        if required and st=="":
            confirmar.append({
                "id":did,
                "nombre":f"Debe indicar el estado de: {d.get('nombre',did)}"
            })

        if st=="NO_LO_TENGO" and required:
            faltantes.append(d)

        if st=="NO_ESTOY_SEGURO":
            dudosos.append(d)

        if d.get("confirmar") is True:
            confirmar.append({
                "id":did,
                "nombre":d.get("nombre",did)
            })

        if st not in (
            "","LO_TENGO","NO_LO_TENGO",
            "NO_ESTOY_SEGURO","NO_APLICA"
        ):
            inconsistencias.append({
                "id":did,
                "mensaje":"Estado documental no reconocido."
            })

    for r in m.get("reglas",[]) or []:
        if not rule_condition(r,res):continue

        action=str(r.get("accion","")).upper()
        msg=r.get("mensaje","")
        rid=r.get("id","REGLA")

        if action=="FALTAN_DOCUMENTOS":
            faltantes.append({
                "id":rid,
                "nombre":msg or "Documento requerido por la regla."
            })

        elif action=="HAY_INCONSISTENCIAS":
            inconsistencias.append({
                "id":rid,
                "mensaje":msg or "Debe aclararse esta situación."
            })

        elif action=="REQUIERE_CONFIRMACION":
            confirmar.append({
                "id":rid,
                "nombre":msg or "Confirmar con la autoridad."
            })

        elif action=="EXIGIR_DETALLE":
            inconsistencias.append({
                "id":rid,
                "mensaje":msg or "Se requiere información adicional."
            })

    if answer_has(res,"NO_SE"):
        confirmar.append({
            "id":"RESPUESTA_NO_SE",
            "nombre":"Existe una respuesta que no se pudo confirmar."
        })

    if answer_has(res,"__OTRO__"):
        confirmar.append({
            "id":"OTRO",
            "nombre":"Debe explicarse la opción OTRO."
        })

    # Prioridad oficial:
    # 1 inconsistencias
    # 2 documentos faltantes
    # 3 confirmación
    # 4 listo
    if inconsistencias:
        result="HAY_INCONSISTENCIAS"
    elif faltantes:
        result="FALTAN_DOCUMENTOS"
    elif missing_q or dudosos or confirmar:
        result="REQUIERE_CONFIRMACION"
    else:
        result="LISTO_PARA_CONFIRMAR"

    # Si el frontend no envía consulado, no se inventa.
    # Solo se marca como punto de confirmación.
    if not consulado.get("estado") or not consulado.get("ciudad") or not consulado.get("consulado"):
        confirmar.append({
            "id":"CONSULADO",
            "nombre":"Estado, ciudad y consulado u oficina deben identificarse o confirmarse."
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
        "consulado":consulado,
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

    return evaluate_case(
        tid,mid,res,docs,
        data.get("consulado") or {}
    )

# ============================================================
# PDF
# ============================================================

def safe_filename(name):
    name=Path(str(name)).name
    if not re.fullmatch(r"[A-Za-z0-9_.-]+",name):
        raise HTTPException(400,"Nombre de archivo inválido.")
    return name

def format_value(v):
    if isinstance(v,list):
        return ", ".join(str(x) for x in v)
    if isinstance(v,dict):
        return ", ".join(f"{k}: {v2}" for k,v2 in v.items())
    return str(v)

def question_labels(mod):
    out={}
    for q in get_questions(mod):
        if isinstance(q,dict) and q.get("id"):
            out[str(q["id"])]=(
                q.get("pregunta") or
                q.get("texto") or
                q.get("label") or
                q.get("nombre") or
                str(q["id"])
            )
    return out

def pdf_document(c,d):
    y=c["y"]
    width=c["width"]
    height=c["height"]

    def line(txt,size=10,bold=False,space=14):
        nonlocal y
        font="Helvetica-Bold" if bold else "Helvetica"

        if y<60:
            c["c"].showPage()
            y=height-50

        c["c"].setFont(font,size)

        lines=simpleSplit(
            str(txt),
            font,
            width-100
        ) or [""]

        for s in lines:
            if y<60:
                c["c"].showPage()
                y=height-50
                c["c"].setFont(font,size)
            c["c"].drawString(50,y,s)
            y-=space

        return y

    line(f"DOCUMENTO: {d.get('id','')}",11,True,16)
    line(f"Nombre: {d.get('nombre',d.get('name',''))}")
    line(f"Categoría: {d.get('categoria','')}")
    if d.get("_bloque_seccion"):
        line(f"Sección: {d['_bloque_seccion']}")
    line(f"Estado: {d.get('estado','NO DEFINIDO')}")
    line(f"Obligatorio: {'SÍ' if d.get('obligatorio') else 'NO'}")

    if d.get("motivo"):
        line(f"Motivo: {d['motivo']}")

    if d.get("nota"):
        line(f"Nota: {d['nota']}")

    if d.get("confirmar"):
        line("POR CONFIRMAR CON LA AUTORIDAD.",10,True)

    y-=5
    return y

def make_pdf(data,path):
    tid=data.get("tramite","")
    mid=data.get("modalidad","")

    res=data.get("respuestas") or data.get("datos_especificos") or {}
    dp=data.get("datos_personales") or {}
    cons=data.get("consulado") or {}

    evaluation=evaluate_case(
        tid,
        mid,
        res,
        data.get("documentos") or {},
        cons
    )

    t=get_tramite(tid)
    m=get_modalidad(tid,mid)
    labels=question_labels(m)

    c=canvas.Canvas(str(path),pagesize=LETTER)
    width,height=LETTER
    y=height-50

    def text(txt,size=10,bold=False,space=14):
        nonlocal y

        font="Helvetica-Bold" if bold else "Helvetica"
        lines=simpleSplit(str(txt),font,width-100) or [""]

        for s in lines:
            if y<60:
                c.showPage()
                y=height-50
            c.setFont(font,size)
            c.drawString(50,y,s)
            y-=space

    # --------------------------------------------------------
    # ENCABEZADO
    # --------------------------------------------------------

    text("SAVE MÉXICO AYUDAR",17,True,23)
    text("GUÍA PERSONAL DE PREPARACIÓN",13,True,20)
    text("Preparación privada para trámite mexicano",10,False,17)
    text(
        f"Fecha de preparación: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
       9,False,13
    )

    y-=5

    # --------------------------------------------------------
    # TRÁMITE
    # --------------------------------------------------------

    text("1. TRÁMITE",12,True,18)
    text(f"Trámite: {t.get('nombre',tid)}")
    text(f"Modalidad: {m.get('nombre',mid)}")

    if t.get("institucion") or t.get("autoridad"):
        text(
            f"Institución: {t.get('institucion',t.get('autoridad',''))}"
        )

    if t.get("descripcion"):
        text(f"Descripción: {t['descripcion']}",9)

    y-=5

    # --------------------------------------------------------
    # DATOS PERSONALES
    # --------------------------------------------------------

    text("2. DATOS PERSONALES",12,True,18)

    for k,v in dp.items():
        if v in ("",None,[]):
            continue
        text(f"{k}: {format_value(v)}",9)

    y-=5

    # --------------------------------------------------------
    # CONSULADO
    # --------------------------------------------------------

    text("3. CONSULADO U OFICINA",12,True,18)

    text(f"País: {cons.get('pais','México / Estados Unidos')}")
    text(f"Estado: {cons.get('estado','')}")
    text(f"Ciudad: {cons.get('ciudad','')}")
    text(f"Consulado u oficina: {cons.get('consulado','')}")

    y-=5

    # --------------------------------------------------------
    # RESPUESTAS
    # --------------------------------------------------------

    text("4. RESPUESTAS DE LA PERSONA",12,True,18)

    for k,v in res.items():
        if k.endswith("_otro"):
            continue
        if v in ("",None,[]):
            continue

        label=labels.get(str(k),str(k))
        text(f"{label}: {format_value(v)}",9,False,13)

        otro=res.get(f"{k}_otro")
        if otro:
            text(f"Detalle de OTRO: {otro}",9,False,13)

    y-=5

    # --------------------------------------------------------
    # SITUACIONES
    # --------------------------------------------------------

    if evaluation["situaciones"]:
        text("5. SITUACIONES DETECTADAS",12,True,18)
        for x in evaluation["situaciones"]:
            if x.get("mensaje"):
                text(x["mensaje"],9)
        y-=5

    # --------------------------------------------------------
    # DOCUMENTOS
    # --------------------------------------------------------

    text("6. DOCUMENTOS APLICABLES",12,True,18)

    docs_status=document_status_map(data.get("documentos") or {})

    groups={}
    for d in evaluation["documentos_aplicables"]:
        section=d.get(
            "_bloque_seccion",
            d.get("categoria","DOCUMENTOS")
        )
        groups.setdefault(section,[]).append(d)

    for section,items in groups.items():
        if section:
            text(section,11,True,17)

        for d in items:
            did=str(d.get("id") or d.get("codigo") or "")
            x=dict(d)
            x["estado"]=docs_status.get(did,"NO DEFINIDO")
            x["obligatorio"]=bool(
                d.get("obligatorio_base") is True or
                d.get("obligatorio") is True or
                d.get("required") is True
            )
            y=pdf_document({
                "c":c,
                "y":y,
                "width":width,
                "height":height
            },x)

        y-=4

    # --------------------------------------------------------
    # FALTANTES
    # --------------------------------------------------------

    if evaluation["documentos_faltantes"]:
        text("7. DOCUMENTOS FALTANTES",12,True,18)
        for d in evaluation["documentos_faltantes"]:
            text(
                f"{d.get('id','')}: "
                f"{d.get('nombre',d.get('mensaje',''))}",
               10
            )
        y-=5

    # --------------------------------------------------------
    # DUDOSOS
    # --------------------------------------------------------

    if evaluation["documentos_dudosos"]:
        text("8. DOCUMENTOS POR CONFIRMAR",12,True,18)
        for d in evaluation["documentos_dudosos"]:
            text(
                f"{d.get('id','')}: "
                f"{d.get('nombre',d.get('name',''))}",
               10
            )
        y-=5

    # --------------------------------------------------------
    # INCONSISTENCIAS
    # --------------------------------------------------------

    if evaluation["inconsistencias"]:
        text("9. INCONSISTENCIAS",12,True,18)
        for x in evaluation["inconsistencias"]:
            text(
                f"{x.get('id','')}: "
                f"{x.get('mensaje','')}",
               10
            )
        y-=5

    # --------------------------------------------------------
    # CONFIRMACIONES
    # --------------------------------------------------------

    if evaluation["confirmaciones"]:
        text("10. PUNTOS POR CONFIRMAR",12,True,18)

        seen=set()

        for x in evaluation["confirmaciones"]:
            ident=(
                str(x.get("id",""))+
                str(x.get("nombre",x.get("mensaje","")))
            )

            if ident in seen:
                continue

            seen.add(ident)

            text(
                f"{x.get('id','')}: "
                f"{x.get('nombre',x.get('mensaje',''))}",
               10
            )

        y-=5

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    text("11. RESULTADO FINAL",12,True,18)
    text(evaluation["resultado"],11,True,17)

    rc=m.get("resultado",{})

    if isinstance(rc,dict):
        for k,v in rc.items():
            if v not in ("",None,[]):
                text(f"{k}: {format_value(v)}",9)

    y-=5

    # --------------------------------------------------------
    # AVISO
    # --------------------------------------------------------

    text("AVISO IMPORTANTE",12,True,18)
    text(
        "SAVE MÉXICO AYUDAR no es una oficina del Gobierno de México, "
        "la SRE ni el INE.",
       9
    )
    text(
        "Esta guía es un servicio privado de preparación documental.",
       9
    )
    text(
        "Los requisitos, documentos aceptados, citas, tarifas y "
        "procedimientos pueden cambiar.",
       9
    )
    text(
        "Confirma la información con la autoridad competente antes "
        "de acudir.",
       9
    )

    c.save()
    return path

# ============================================================
# GENERAR PDF
# ============================================================

@app.post("/api/generar-guia-consular")
async def generar_guia(data:Guide,request:Request):
    require_access(request)

    if not data.tramite:
        raise HTTPException(400,"Debe indicar el trámite.")

    if not data.modalidad:
        raise HTTPException(400,"Debe indicar la modalidad.")

    # Acepta el formato actual del index.html:
    # documentos = lista de objetos.
    respuestas=data.respuestas or data.datos_especificos or {}

    result=evaluate_case(
        data.tramite,
        data.modalidad,
        respuestas,
        data.documentos,
        data.consulado
    )

    if result["preguntas_faltantes"]:
        raise HTTPException(
            400,
            "Faltan respuestas obligatorias: "+
            ", ".join(result["preguntas_faltantes"])
        )

    if result["resultado"]=="HAY_INCONSISTENCIAS":
        raise HTTPException(
            400,
            "Existen inconsistencias que deben aclararse antes de generar la guía."
        )

    name=f"guia_{uuid.uuid4().hex}.pdf"
    path=OUT/name

    payload=data.model_dump()
    payload["respuestas"]=respuestas
    payload["datos_especificos"]=respuestas
    payload["resultado_evaluacion"]=result

    try:
        make_pdf(payload,path)
    except Exception as e:
        if path.exists():
            try:path.unlink()
            except Exception:pass
        raise HTTPException(
            500,
            f"No se pudo generar el PDF: {e}"
        )

    if not path.exists() or path.stat().st_size<100:
        raise HTTPException(
            500,
            "El PDF no pudo crearse correctamente."
        )

    return {
        "ok":True,
        "filename":name,
        "archivo":name,
        "file":name,
        "pdf":name,
        "url":f"/descargar/{name}",
        "resultado":result["resultado"],
        "resultado_evaluacion":result
    }

# ============================================================
# DESCARGA PDF
# ============================================================

@app.get("/descargar/{name}")
async def descargar(name:str,request:Request):
    require_access(request)

    try:
        name=safe_filename(name)
    except Exception:
        raise HTTPException(400,"Archivo inválido.")

    if not name.lower().endswith(".pdf"):
        raise HTTPException(400,"Solo se pueden descargar archivos PDF.")

    p=(OUT/name).resolve()

    try:
        p.relative_to(OUT.resolve())
    except ValueError:
        raise HTTPException(400,"Archivo inválido.")

    if not p.exists() or not p.is_file():
        raise HTTPException(
            404,
            "El archivo PDF no existe o ya no está disponible."
        )

    return FileResponse(
        str(p),
        media_type="application/pdf",
        filename="SAVE_MEXICO_AYUDAR_GUIA.pdf"
    )

# ============================================================
# SUBIR DOCUMENTO
# ============================================================

@app.post("/api/subir-documento")
async def subir_documento(
    request:Request,
    file:UploadFile=File(...)
):
    require_access(request)

    if not file.filename:
        raise HTTPException(400,"Archivo no válido.")

    ext=Path(file.filename).suffix.lower()

    if ext not in (".pdf",".jpg",".jpeg",".png"):
        raise HTTPException(
            400,
            "Solo se permiten PDF, JPG, JPEG o PNG."
        )

    raw=await file.read()

    if len(raw)>15*1024*1024:
        raise HTTPException(
            400,
            "El archivo supera 15 MB."
        )

    name=f"{uuid.uuid4().hex}{ext}"
    path=OUT/name
    path.write_bytes(raw)

    pages=None

    if ext==".pdf":
        try:
            pages=len(PdfReader(str(path)).pages)
        except Exception:
            pages=None

    return {
        "ok":True,
        "archivo":name,
        "paginas":pages
    }

# ============================================================
# SALUD
# ============================================================

@app.get("/health")
async def health():
    data=load_data()
    ts=get_tramites()

    return {
        "ok":True,
        "app":"SAVE MÉXICO AYUDAR",
        "version":"5.1.1",
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
        "admin_configured":bool(
            ADMIN_USERNAME and ADMIN_PASSWORD
        )
    }

# ============================================================
# INICIO
# ============================================================

@app.get("/")
async def index():
    p=STATIC/"index.html"

    if not p.exists():
        raise HTTPException(
            404,
            "No existe static/index.html."
        )

    return FileResponse(str(p))

if __name__=="__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT","8000"))
    )
