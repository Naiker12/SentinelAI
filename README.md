# SentinelAI

MVP inicial de `AgentePercepcion`: camara local, deteccion con YOLOv8, eventos JSON, envio opcional a n8n y almacenamiento en Supabase.

## Stack

- Python
- OpenCV
- YOLO/Ultralytics con modelo entrenado `yolo_percepcion/entrenamiento_seguridad/weights/best.pt`
- FastAPI
- Supabase/Postgres
- Prisma para migraciones
- n8n mediante webhook

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
Copy-Item .env.example .env
```

Edita `.env` y coloca tus variables de n8n y Supabase:

```env
SENTINEL_N8N_WEBHOOK_URL=http://localhost:5678/webhook/sentinel-analysis
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=SERVICE_ROLE_KEY
DATABASE_URL=postgres://prisma.PROJECT_REF:PRISMA_PASSWORD@REGION.pooler.supabase.com:5432/postgres
DIRECT_URL=postgres://postgres.PROJECT_REF:DB_PASSWORD@REGION.pooler.supabase.com:5432/postgres
```

Usa `/webhook/sentinel-analysis` con el workflow activo en n8n. La ruta
`/webhook-test/sentinel-analysis` solo responde cuando el nodo Webhook esta en
`Listen for test event`.

Antes de ejecutar el agente contra Supabase, crea las tablas con Prisma:

```powershell
npx prisma migrate dev --name init_supabase_schema
npx prisma generate
```

## Ejecutar camara en tiempo real

```powershell
python -m agente_percepcion.main
```

Presiona `q` para cerrar la ventana de camara.

## Crear dataset propio

Captura imagenes reales con la webcam:

```powershell
python tools/capture_dataset.py --scenario objeto_sospechoso --label arma_blanca
```

Controles:

- `s`: guardar frame actual.
- `a`: activar/desactivar captura automatica.
- `q`: salir.

La estructura del dataset vive en:

```text
dataset/
  raw/
  yolo/images/
  yolo/labels/
  data.yaml
  classes.txt
```

El modelo activo de seguridad usa estas clases:

```text
arma
arma_blanca
fusil
multitud
no_violencia
persona
persona_sospechosa
undefined
violencia
```

Las reglas de riesgo consumen esas clases directamente. `undefined` queda registrada como clase del entrenamiento, pero no se considera peligrosa por defecto.

## Ejecutar dashboard local

```powershell
streamlit run dashboard/sentinel_dashboard.py
```

Desde la carpeta `dashboard/` tambien funciona:

```powershell
streamlit run
```

Si `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` estan configuradas, el dashboard lee `detection_events`.
Si no puede conectarse, usa datos simulados realistas.

## Diagnosticar camara

Si la ventana de la camara muestra ruido, lineas de colores o imagen corrupta,
prueba backends y formatos antes de ejecutar todo el agente:

```powershell
python tools/check_camera.py --indices 0,1,2 --backends directshow,msmf,any --fourcc MJPG
```

Si `directshow` se ve mal, prueba:

```env
SENTINEL_CAMERA_BACKEND=msmf
SENTINEL_CAMERA_WIDTH=640
SENTINEL_CAMERA_HEIGHT=480
SENTINEL_CAMERA_FPS=30
SENTINEL_CAMERA_FOURCC=MJPG
```

Si sigue corrupta, cambia `SENTINEL_CAMERA_INDEX=1` o usa `SENTINEL_CAMERA_FOURCC=YUY2`.

## Ejecutar API local

```powershell
uvicorn agente_percepcion.api:app --reload
```

Endpoints:

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/events`
- `POST http://localhost:8000/detect-once`

## Ejecutar API central de analisis

```powershell
uvicorn agente_analisis.api:app --reload --port 8010
```

Endpoints:

- `GET http://localhost:8010/health`
- `POST http://localhost:8010/analyze`

La arquitectura completa esta documentada en `docs/ARCHITECTURE.md`.
El estado actual y roadmap estan en `docs/ESTADO_ACTUAL.md`.

## Configuracion importante

La variable `SENTINEL_CLASSES` controla que clases generan eventos. Con el modelo nuevo debe quedar:

```env
SENTINEL_MODEL=yolo_percepcion/entrenamiento_seguridad/weights/best.pt
SENTINEL_CLASSES=arma,arma_blanca,fusil,multitud,no_violencia,persona,persona_sospechosa,violencia
```

El modelo reporta clases en espanol; el sistema tambien acepta alias antiguos como `Violence`, `NonViolence`, `gun`, `knife` y `person`, normalizandolos al vocabulario nuevo.

## n8n

En n8n crea un workflow simple:

1. Importa `n8n/AgenteAnalisis.workflow.json` o crea un nodo `Webhook`.
2. Metodo `POST`.
3. Ruta `sentinel-analysis`.
4. Nodos de analisis, almacenamiento o alerta.

El agente enviara un JSON similar a:

```json
{
  "objeto": "persona",
  "confianza": 0.91,
  "hora": "2026-05-26T20:30:00.000000+00:00",
  "camara": "PC-01",
  "riesgo": "bajo",
  "box": [10, 20, 200, 300],
  "imagen": null,
  "contexto": {
    "zona": "sin_zona",
    "iluminacion": "desconocida",
    "cantidad_personas": 1
  },
  "tracking": {},
  "memoria": {
    "eventos_previos_24h": 0,
    "alertas_previas_24h": 0
  }
}
```

## Estructura

```text
SentinelAI/
  agente_percepcion/
    api.py
    camera.py
    config.py
    detector.py
    events.py
    main.py
    memory.py
  prisma/
  .env.example
  .gitignore
  README.md
  requirements.txt
```
