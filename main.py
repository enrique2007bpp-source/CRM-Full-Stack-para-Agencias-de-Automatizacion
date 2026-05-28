from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sqlite3, json, re
from datetime import datetime, date
import uuid

app = FastAPI(title="FlowCRM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "flowcrm.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        company TEXT,
        position TEXT,
        stage TEXT DEFAULT 'lead',
        source TEXT DEFAULT 'manual',
        notes TEXT DEFAULT '',
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS deals (
        id TEXT PRIMARY KEY,
        contact_id TEXT,
        title TEXT NOT NULL,
        value REAL DEFAULT 0,
        stage TEXT DEFAULT 'lead',
        description TEXT DEFAULT '',
        close_date TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(contact_id) REFERENCES contacts(id)
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        contact_id TEXT,
        deal_id TEXT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        due_date TEXT,
        priority TEXT DEFAULT 'medium',
        done INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        contact_id TEXT,
        deal_id TEXT,
        content TEXT NOT NULL,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT
    );
    """)
    # Seed demo data
    existing = c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    if existing == 0:
        now = datetime.now().isoformat()
        contacts = [
            ("c1","María Rodríguez","maria@mediatica.es","612345678","Mediatica SL","Directora de Marketing","negotiation","referral","Cliente potencial muy interesado en la suite completa.",now,now),
            ("c2","Carlos López","carlos@retailmax.es","623456789","RetailMax","CEO","proposal","linkedin","Reunión inicial muy positiva.",now,now),
            ("c3","Sara Tomás","sara@saastech.io","634567890","SaasTech","CTO","won","referral","Deal cerrado. Muy satisfecha con el servicio.",now,now),
            ("c4","Ana Fernández","ana@finanzasdk.es","645678901","Finanzas DK","COO","negotiation","web","Interesada en bots de IA para automatizar reportes.",now,now),
            ("c5","Pablo Herrero","pablo@gruponexus.es","656789012","Grupo Nexus","Fundador","lead","cold_email","Primer contacto por email.",now,now),
            ("c6","Laura Díez","laura@estudioKraken.es","667890123","Estudio Kraken","Product Manager","lead","referral","Referida por Sara Tomás.",now,now),
        ]
        c.executemany("INSERT INTO contacts VALUES (?,?,?,?,?,?,?,?,?,?,?)", contacts)
        deals = [
            ("d1","c1","Suite completa Mediatica",8500,"proposal","Automatización completa de marketing y ventas","2025-05-15",now,now),
            ("d2","c2","Integraciones RetailMax",4200,"proposal","Integración con ERP y ecommerce","2025-05-20",now,now),
            ("d3","c3","Onboarding SaasTech",3200,"won","Deal cerrado. Implementación en curso","2025-03-10",now,now),
            ("d4","c4","Bots IA Finanzas DK",12000,"negotiation","Sistema de bots para reportes automáticos","2025-05-30",now,now),
            ("d5","c5","Automatización web Nexus",1800,"lead","Automación de captación de leads web","2025-06-10",now,now),
            ("d6","c6","CRM custom Kraken",2400,"lead","CRM personalizado para agencia creativa","2025-06-20",now,now),
        ]
        c.executemany("INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?)", deals)
        tasks = [
            ("t1","c4","d4","Follow-up Finanzas DK","Llamar para confirmar propuesta final",str(date.today()),"high",0,now,now),
            ("t2","c2","d2","Demo RetailMax","Preparar demo de integraciones","2025-04-21","medium",0,now,now),
            ("t3","c1","d1","Revisar contrato Mediatica","Revisar cláusulas con asesoría","2025-04-22","high",0,now,now),
            ("t4","c3",None,"Onboarding SaasTech","Llamada de onboarding inicial","2025-04-23","medium",0,now,now),
            ("t5","c2","d1","Reunión Carlos López","Reunión de seguimiento",str(date.today()),"medium",1,now,now),
            ("t6","c3","d3","Cerrar deal SaasTech","Firma de contrato","2025-03-16","high",1,now,now),
        ]
        c.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)", tasks)
        notes_data = [
            ("n1","c1","d1","Primera reunión muy positiva. María quiere automatizar toda la estrategia de contenido.",now),
            ("n2","c4","d4","Ana mencionó que tienen un presupuesto aprobado de hasta €15.000.",now),
            ("n3","c3","d3","Deal cerrado. Sara muy contenta con la propuesta técnica.",now),
        ]
        c.executemany("INSERT INTO notes VALUES (?,?,?,?,?)", notes_data)
    conn.commit()
    conn.close()

init_db()

# ─── MODELS ───────────────────────────────────────────────
class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    stage: Optional[str] = "lead"
    source: Optional[str] = "manual"
    notes: Optional[str] = ""

class DealCreate(BaseModel):
    contact_id: Optional[str] = None
    title: str
    value: Optional[float] = 0
    stage: Optional[str] = "lead"
    description: Optional[str] = ""
    close_date: Optional[str] = None

class TaskCreate(BaseModel):
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    due_date: Optional[str] = None
    priority: Optional[str] = "medium"
    done: Optional[bool] = False

class NoteCreate(BaseModel):
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    content: str

class ChatMessage(BaseModel):
    message: str

# ─── HELPERS ──────────────────────────────────────────────
def new_id():
    return str(uuid.uuid4())[:8]

def now():
    return datetime.now().isoformat()

def row_to_dict(row):
    return dict(row) if row else None

# ─── CONTACTS ─────────────────────────────────────────────
@app.get("/contacts")
def list_contacts(search: Optional[str] = None, stage: Optional[str] = None):
    conn = get_db()
    q = "SELECT * FROM contacts WHERE 1=1"
    params = []
    if search:
        q += " AND (name LIKE ? OR company LIKE ? OR email LIKE ?)"
        s = f"%{search}%"
        params += [s, s, s]
    if stage:
        q += " AND stage = ?"
        params.append(stage)
    q += " ORDER BY created_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/contacts")
def create_contact(c: ContactCreate):
    conn = get_db()
    cid = new_id()
    n = now()
    conn.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (cid, c.name, c.email, c.phone, c.company, c.position, c.stage, c.source, c.notes, n, n))
    conn.commit()
    row = conn.execute("SELECT * FROM contacts WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(row)

@app.get("/contacts/{cid}")
def get_contact(cid: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM contacts WHERE id=?", (cid,)).fetchone()
    if not row: raise HTTPException(404, "Not found")
    contact = dict(row)
    contact["deals"] = [dict(r) for r in conn.execute("SELECT * FROM deals WHERE contact_id=?", (cid,)).fetchall()]
    contact["tasks"] = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE contact_id=?", (cid,)).fetchall()]
    contact["notes"] = [dict(r) for r in conn.execute("SELECT * FROM notes WHERE contact_id=?", (cid,)).fetchall()]
    conn.close()
    return contact

@app.put("/contacts/{cid}")
def update_contact(cid: str, c: ContactCreate):
    conn = get_db()
    n = now()
    conn.execute("UPDATE contacts SET name=?,email=?,phone=?,company=?,position=?,stage=?,source=?,notes=?,updated_at=? WHERE id=?",
        (c.name, c.email, c.phone, c.company, c.position, c.stage, c.source, c.notes, n, cid))
    conn.commit()
    row = conn.execute("SELECT * FROM contacts WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/contacts/{cid}")
def delete_contact(cid: str):
    conn = get_db()
    conn.execute("DELETE FROM contacts WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ─── DEALS ────────────────────────────────────────────────
@app.get("/deals")
def list_deals(stage: Optional[str] = None):
    conn = get_db()
    q = "SELECT d.*, c.name as contact_name, c.company FROM deals d LEFT JOIN contacts c ON d.contact_id=c.id WHERE 1=1"
    params = []
    if stage:
        q += " AND d.stage=?"
        params.append(stage)
    q += " ORDER BY d.created_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/deals")
def create_deal(d: DealCreate):
    conn = get_db()
    did = new_id()
    n = now()
    conn.execute("INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?)",
        (did, d.contact_id, d.title, d.value, d.stage, d.description, d.close_date, n, n))
    conn.commit()
    row = conn.execute("SELECT d.*, c.name as contact_name FROM deals d LEFT JOIN contacts c ON d.contact_id=c.id WHERE d.id=?", (did,)).fetchone()
    conn.close()
    return dict(row)

@app.put("/deals/{did}")
def update_deal(did: str, d: DealCreate):
    conn = get_db()
    n = now()
    conn.execute("UPDATE deals SET contact_id=?,title=?,value=?,stage=?,description=?,close_date=?,updated_at=? WHERE id=?",
        (d.contact_id, d.title, d.value, d.stage, d.description, d.close_date, n, did))
    conn.commit()
    row = conn.execute("SELECT d.*, c.name as contact_name FROM deals d LEFT JOIN contacts c ON d.contact_id=c.id WHERE d.id=?", (did,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/deals/{did}")
def delete_deal(did: str):
    conn = get_db()
    conn.execute("DELETE FROM deals WHERE id=?", (did,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ─── TASKS ────────────────────────────────────────────────
@app.get("/tasks")
def list_tasks(done: Optional[bool] = None):
    conn = get_db()
    q = "SELECT t.*, c.name as contact_name FROM tasks t LEFT JOIN contacts c ON t.contact_id=c.id WHERE 1=1"
    params = []
    if done is not None:
        q += " AND t.done=?"
        params.append(1 if done else 0)
    q += " ORDER BY t.due_date ASC, t.priority DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/tasks")
def create_task(t: TaskCreate):
    conn = get_db()
    tid = new_id()
    n = now()
    conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tid, t.contact_id, t.deal_id, t.title, t.description, t.due_date, t.priority, 1 if t.done else 0, n, n))
    conn.commit()
    row = conn.execute("SELECT t.*, c.name as contact_name FROM tasks t LEFT JOIN contacts c ON t.contact_id=c.id WHERE t.id=?", (tid,)).fetchone()
    conn.close()
    return dict(row)

@app.put("/tasks/{tid}")
def update_task(tid: str, t: TaskCreate):
    conn = get_db()
    n = now()
    conn.execute("UPDATE tasks SET contact_id=?,deal_id=?,title=?,description=?,due_date=?,priority=?,done=?,updated_at=? WHERE id=?",
        (t.contact_id, t.deal_id, t.title, t.description, t.due_date, t.priority, 1 if t.done else 0, n, tid))
    conn.commit()
    row = conn.execute("SELECT t.*, c.name as contact_name FROM tasks t LEFT JOIN contacts c ON t.contact_id=c.id WHERE t.id=?", (tid,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/tasks/{tid}")
def delete_task(tid: str):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ─── NOTES ────────────────────────────────────────────────
@app.post("/notes")
def create_note(n: NoteCreate):
    conn = get_db()
    nid = new_id()
    conn.execute("INSERT INTO notes VALUES (?,?,?,?,?)", (nid, n.contact_id, n.deal_id, n.content, now()))
    conn.commit()
    row = conn.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/notes/{nid}")
def delete_note(nid: str):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ─── DASHBOARD ────────────────────────────────────────────
@app.get("/dashboard")
def dashboard():
    conn = get_db()
    total_contacts = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    active_contacts = conn.execute("SELECT COUNT(*) FROM contacts WHERE stage NOT IN ('won','lost')").fetchone()[0]
    pipeline_value = conn.execute("SELECT COALESCE(SUM(value),0) FROM deals WHERE stage NOT IN ('won','lost')").fetchone()[0]
    won_value = conn.execute("SELECT COALESCE(SUM(value),0) FROM deals WHERE stage='won'").fetchone()[0]
    pending_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE done=0").fetchone()[0]
    overdue_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE done=0 AND due_date < date('now')").fetchone()[0]
    deals_by_stage = conn.execute("SELECT stage, COUNT(*) as count, COALESCE(SUM(value),0) as total FROM deals GROUP BY stage").fetchall()
    sources = conn.execute("SELECT source, COUNT(*) as count FROM contacts GROUP BY source ORDER BY count DESC").fetchall()
    recent_activity = conn.execute("""
        SELECT * FROM (
            SELECT 'note' as type, n.content as title, n.created_at, c.name as contact_name
            FROM notes n LEFT JOIN contacts c ON n.contact_id=c.id
            UNION ALL
            SELECT 'deal' as type, d.title, d.updated_at as created_at, c.name as contact_name
            FROM deals d LEFT JOIN contacts c ON d.contact_id=c.id
            UNION ALL
            SELECT 'task' as type, t.title, t.updated_at as created_at, c.name as contact_name
            FROM tasks t LEFT JOIN contacts c ON t.contact_id=c.id
        ) ORDER BY created_at DESC LIMIT 8
    """).fetchall()
    conn.close()
    return {
        "total_contacts": total_contacts,
        "active_contacts": active_contacts,
        "pipeline_value": round(pipeline_value, 2),
        "won_value": round(won_value, 2),
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "deals_by_stage": [dict(r) for r in deals_by_stage],
        "sources": [dict(r) for r in sources],
        "recent_activity": [dict(r) for r in recent_activity],
    }

# ─── AI CHATBOT (100% local, no paid APIs) ────────────────
def get_crm_context():
    conn = get_db()
    contacts = conn.execute("SELECT name, company, stage, email FROM contacts ORDER BY updated_at DESC LIMIT 20").fetchall()
    deals = conn.execute("SELECT title, value, stage, contact_id FROM deals ORDER BY value DESC LIMIT 20").fetchall()
    tasks = conn.execute("SELECT title, due_date, priority, done FROM tasks WHERE done=0 ORDER BY due_date ASC LIMIT 10").fetchall()
    stats = conn.execute("SELECT COUNT(*) as c, COALESCE(SUM(value),0) as v FROM deals WHERE stage='won'").fetchone()
    pipeline = conn.execute("SELECT COALESCE(SUM(value),0) as v FROM deals WHERE stage NOT IN ('won','lost')").fetchone()
    conn.close()
    ctx = f"Tienes {len(contacts)} contactos recientes. "
    ctx += f"Pipeline activo: €{round(pipeline['v'],0):,.0f}. "
    ctx += f"Deals ganados: €{round(stats['v'],0):,.0f}. "
    ctx += f"Tareas pendientes: {len(tasks)}.\n"
    ctx += "Contactos: " + ", ".join([f"{r['name']} ({r['company']}, {r['stage']})" for r in contacts[:8]]) + ".\n"
    ctx += "Deals top: " + ", ".join([f"{r['title']} €{r['value']} ({r['stage']})" for r in deals[:6]]) + ".\n"
    if tasks:
        ctx += "Tareas urgentes: " + ", ".join([f"{r['title']} ({r['due_date']})" for r in tasks[:5]]) + "."
    return ctx

def local_ai_respond(message: str, history: list) -> str:
    """
    Rule-based + template AI that answers CRM questions without any external API.
    Covers the most common use cases for a CRM assistant.
    """
    msg = message.lower().strip()
    ctx = get_crm_context()

    conn = get_db()
    contacts = [dict(r) for r in conn.execute("SELECT * FROM contacts").fetchall()]
    deals = [dict(r) for r in conn.execute("SELECT * FROM deals").fetchall()]
    tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE done=0").fetchall()]
    conn.close()

    # Pipeline / ventas
    if any(w in msg for w in ["pipeline","valor","ventas","cuánto","dinero","revenue","factur"]):
        total = sum(d["value"] for d in deals if d["stage"] not in ["won","lost"])
        won = sum(d["value"] for d in deals if d["stage"] == "won")
        by_stage = {}
        for d in deals:
            by_stage[d["stage"]] = by_stage.get(d["stage"], 0) + d["value"]
        lines = "\n".join([f"  • {s.capitalize()}: €{v:,.0f}" for s, v in by_stage.items()])
        return f"📊 **Resumen del pipeline:**\n\n**Pipeline activo:** €{total:,.0f}\n**Deals ganados:** €{won:,.0f}\n\nPor etapa:\n{lines}\n\n¿Quieres que profundice en alguna etapa concreta?"

    # Tareas
    if any(w in msg for w in ["tarea","pendiente","hacer","urgente","vencid","próxim"]):
        if not tasks:
            return "✅ ¡No tienes tareas pendientes! Estás al día."
        urgent = [t for t in tasks if t["priority"] == "high"]
        lines = "\n".join([f"  • {t['title']} — {t['due_date'] or 'sin fecha'} ({t['priority']})" for t in tasks[:6]])
        return f"📋 **Tienes {len(tasks)} tareas pendientes:**\n\n{lines}\n\n{'⚠️ ' + str(len(urgent)) + ' son de alta prioridad.' if urgent else ''}\n\n¿Quieres crear una nueva tarea o ver los detalles de alguna?"

    # Contactos
    if any(w in msg for w in ["contacto","cliente","lead","quien","cuántos contact"]):
        by_stage = {}
        for c in contacts:
            by_stage[c["stage"]] = by_stage.get(c["stage"], 0) + 1
        lines = "\n".join([f"  • {s.capitalize()}: {v}" for s, v in by_stage.items()])
        return f"👥 **Tienes {len(contacts)} contactos en total:**\n\n{lines}\n\nLos más recientes: {', '.join([c['name'] for c in contacts[:4]])}.\n\n¿Buscas algún contacto en concreto?"

    # Buscar contacto específico
    for c in contacts:
        if c["name"].lower().split()[0] in msg or c["company"].lower().split()[0] in msg:
            c_deals = [d for d in deals if d.get("contact_id") == c["id"]]
            deal_info = f"Deal activo: {c_deals[0]['title']} (€{c_deals[0]['value']:,.0f}, {c_deals[0]['stage']})" if c_deals else "Sin deals activos."
            return f"👤 **{c['name']}**\n\n🏢 {c['company']} — {c['position'] or 'Sin cargo'}\n📧 {c['email'] or 'Sin email'}\n📱 {c['phone'] or 'Sin teléfono'}\n🏷️ Etapa: {c['stage'].capitalize()}\n💼 {deal_info}\n📝 {c['notes'] or 'Sin notas.'}\n\n¿Qué quieres hacer con este contacto?"

    # Consejos / qué hacer
    if any(w in msg for w in ["consejo","recomiend","qué hago","qué debo","ayuda","suger","priorid"]):
        urgent_tasks = [t for t in tasks if t.get("priority") == "high"]
        neg_deals = [d for d in deals if d["stage"] == "negotiation"]
        tips = []
        if urgent_tasks:
            tips.append(f"🔴 Tienes {len(urgent_tasks)} tarea(s) urgente(s): **{urgent_tasks[0]['title']}**. Atiéndelas primero.")
        if neg_deals:
            total_neg = sum(d["value"] for d in neg_deals)
            tips.append(f"💰 Tienes €{total_neg:,.0f} en negociación. Haz seguimiento activo para cerrar estos deals.")
        leads = [c for c in contacts if c["stage"] == "lead"]
        if leads:
            tips.append(f"📬 Hay {len(leads)} leads sin cualificar. Considera contactarlos esta semana.")
        if not tips:
            tips.append("✅ Todo parece estar en orden. Revisa el pipeline y asegúrate de tener seguimientos programados.")
        return "💡 **Mis recomendaciones:**\n\n" + "\n\n".join(tips) + "\n\n¿Quieres que te ayude con alguna de estas acciones?"

    # Crear contacto
    if any(w in msg for w in ["crear contacto","añadir contacto","nuevo contacto","agregar contacto"]):
        return "➕ Para crear un nuevo contacto, haz clic en el botón **+ Nuevo** en la esquina superior derecha y selecciona 'Contacto', o dime los datos del contacto y lo creo por aquí:\n\n**Nombre, empresa, email, teléfono y etapa (lead/propuesta/negociación)**."

    # Crear tarea
    if any(w in msg for w in ["crear tarea","añadir tarea","nueva tarea","recordatorio"]):
        return "✅ Para crear una tarea, ve a la sección **Tareas** y haz clic en **+ Nueva tarea**, o dime:\n\n- ¿Qué tarea es?\n- ¿Para qué fecha?\n- ¿Prioridad? (alta/media/baja)\n- ¿Asociada a algún contacto?"

    # Resumen general
    if any(w in msg for w in ["resumen","estado","cómo va","overview","general","hola","buenos"]):
        total_pipeline = sum(d["value"] for d in deals if d["stage"] not in ["won","lost"])
        overdue = [t for t in tasks if t.get("due_date") and t["due_date"] < str(date.today())]
        return f"👋 ¡Hola! Aquí tienes un resumen rápido de tu CRM:\n\n📊 **Pipeline activo:** €{total_pipeline:,.0f}\n👥 **Contactos:** {len(contacts)} ({len([c for c in contacts if c['stage']=='lead'])} leads nuevos)\n📋 **Tareas pendientes:** {len(tasks)}{' (' + str(len(overdue)) + ' vencidas ⚠️)' if overdue else ''}\n💼 **Deals en negociación:** {len([d for d in deals if d['stage']=='negotiation'])}\n\n¿En qué te puedo ayudar hoy?"

    # Etapas / stages
    if any(w in msg for w in ["etapa","stage","kanban","embudo","funnel"]):
        stage_map = {"lead":"Lead","proposal":"Propuesta","negotiation":"Negociación","won":"Cerrado ganado","lost":"Perdido"}
        by_s = {}
        for d in deals:
            s = d["stage"]
            if s not in by_s: by_s[s] = {"count":0,"value":0}
            by_s[s]["count"] += 1
            by_s[s]["value"] += d["value"]
        lines = "\n".join([f"  • **{stage_map.get(s,s)}**: {v['count']} deals (€{v['value']:,.0f})" for s,v in by_s.items()])
        return f"🗂️ **Distribución del pipeline por etapa:**\n\n{lines}\n\nEl embudo ideal tiene más leads que propuestas, y más propuestas que negociaciones. ¿Quieres analizar alguna etapa específica?"

    # Fallback inteligente
    fallback_responses = [
        f"Entendido. Puedo ayudarte con:\n\n• 📊 **Análisis del pipeline** — cuánto vale, por etapas\n• 👥 **Buscar contactos** — info, deals y notas\n• 📋 **Gestionar tareas** — pendientes, urgentes\n• 💡 **Recomendaciones** — qué priorizar hoy\n\n¿Qué necesitas?",
        f"No he entendido del todo tu pregunta. Puedo consultarte el estado de cualquier contacto, deal o tarea. También puedo darte recomendaciones. ¿Qué quieres saber?",
        f"Hmm, no estoy seguro de lo que buscas. Prueba con preguntas como: *¿Cuánto vale mi pipeline?*, *¿Qué tareas tengo pendientes?*, o *¿Cómo va María Rodríguez?*"
    ]
    import random
    return random.choice(fallback_responses)

@app.post("/chat")
def chat(msg: ChatMessage):
    conn = get_db()
    history = [dict(r) for r in conn.execute("SELECT role, content FROM chat_messages ORDER BY created_at DESC LIMIT 10").fetchall()]
    history.reverse()

    user_id = new_id()
    conn.execute("INSERT INTO chat_messages VALUES (?,?,?,?)", (user_id, "user", msg.message, now()))

    response = local_ai_respond(msg.message, history)

    bot_id = new_id()
    conn.execute("INSERT INTO chat_messages VALUES (?,?,?,?)", (bot_id, "assistant", response, now()))
    conn.commit()
    conn.close()
    return {"response": response, "id": bot_id}

@app.get("/chat/history")
def chat_history():
    conn = get_db()
    rows = conn.execute("SELECT * FROM chat_messages ORDER BY created_at ASC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.delete("/chat/history")
def clear_chat():
    conn = get_db()
    conn.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
