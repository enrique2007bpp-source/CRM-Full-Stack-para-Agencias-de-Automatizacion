# FlowCRM — Agencia de Automatizaciones

CRM completo con IA local para agencias de automatización. Sin APIs externas de pago.

## Stack

- **Backend**: Python + FastAPI + SQLite (base de datos embebida, sin configuración)
- **Frontend**: HTML/CSS/React (un solo archivo, sin build tools)
- **IA**: Motor de respuestas local basado en reglas + contexto CRM en tiempo real

## Estructura

```
flowcrm/
├── backend/
│   ├── main.py          ← API completa (contactos, deals, tareas, notas, chat)
│   ├── requirements.txt
│   └── flowcrm.db       ← Se crea automáticamente con datos demo
└── frontend/
    └── index.html       ← App completa (sin build, abrir directamente)
```

## Instalación y arranque

### 1. Backend (Python)

```bash
cd backend
pip install -r requirements.txt
python main.py
# → API disponible en http://localhost:8000
# → Docs en http://localhost:8000/docs
```

### 2. Frontend

Abre `frontend/index.html` directamente en el navegador.
O sirve con cualquier servidor estático:

```bash
cd frontend
python -m http.server 3000
# → http://localhost:3000
```

## Funcionalidades

### CRM
- ✅ Contactos: crear, editar, eliminar, buscar, filtrar por etapa
- ✅ Pipeline kanban: Lead → Propuesta → Negociación → Cerrado
- ✅ Deals con valor, fecha de cierre, contacto asociado
- ✅ Tareas: prioridad, fecha límite, completar, filtrar
- ✅ Notas por contacto/deal
- ✅ Panel detalle lateral de contacto
- ✅ Dashboard con métricas, actividad reciente, fuente de leads

### IA Chatbot (100% local)
El chatbot consulta la base de datos en tiempo real y responde sobre:
- Estado del pipeline y valor por etapa
- Tareas pendientes y urgentes
- Información de contactos específicos
- Recomendaciones de priorización
- Resumen general del CRM

**Sin costes externos**: No usa OpenAI, Anthropic ni ninguna API de pago.

## API Endpoints

```
GET    /dashboard          → métricas generales
GET    /contacts           → lista (búsqueda + filtros)
POST   /contacts           → crear
GET    /contacts/:id       → detalle + deals + notas
PUT    /contacts/:id       → actualizar
DELETE /contacts/:id       → eliminar
GET    /deals              → lista (filtro por etapa)
POST   /deals              → crear
PUT    /deals/:id          → actualizar
DELETE /deals/:id          → eliminar
GET    /tasks              → lista (filtro done)
POST   /tasks              → crear
PUT    /tasks/:id          → actualizar
DELETE /tasks/:id          → eliminar
POST   /notes              → crear
DELETE /notes/:id          → eliminar
POST   /chat               → chatbot IA
GET    /chat/history       → historial de chat
DELETE /chat/history       → limpiar historial
```
