# SentinelAI

MVP inicial de `AgentePercepcion`: cámara local, detección con YOLOv8, eventos JSON, envío opcional a n8n y almacenamiento en SQLite.

## Stack

- Python
- OpenCV
- YOLOv8 con `ultralytics`
- FastAPI
- SQLite
- n8n mediante webhook

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y coloca tu webhook de n8n si ya lo tienes:

```env
SENTINEL_N8N_WEBHOOK_URL=http://localhost:5678/webhook/sentinel-event
```

## Ejecutar cámara en tiempo real

```powershell
python -m agente_percepcion.main
```

Presiona `q` para cerrar la ventana de cámara.

## Ejecutar API local

```powershell
uvicorn agente_percepcion.api:app --reload
```

Endpoints:

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/events`
- `POST http://localhost:8000/detect-once`

## Configuración importante

La variable `SENTINEL_CLASSES` controla qué objetos generan eventos. Para el primer MVP se recomienda dejar solo:

```env
SENTINEL_CLASSES=person
```

Luego puedes ampliar:

```env
SENTINEL_CLASSES=person,car,backpack,cell phone,knife
```

## n8n

En n8n crea un workflow simple:

1. Nodo `Webhook`.
2. Método `POST`.
3. Ruta `sentinel-event`.
4. Nodo de almacenamiento o alerta.

El agente enviará un JSON similar a:

```json
{
  "objeto": "person",
  "confianza": 0.91,
  "hora": "2026-05-26T20:30:00.000000+00:00",
  "camara": "PC-01",
  "riesgo": "medio",
  "box": [10, 20, 200, 300],
  "imagen": null
}
```

## Estructura

```text
SentinelAI/
├── agente_percepcion/
│   ├── api.py
│   ├── camera.py
│   ├── config.py
│   ├── detector.py
│   ├── events.py
│   └── main.py
├── database/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```
