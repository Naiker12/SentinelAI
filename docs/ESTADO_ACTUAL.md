# SentinelAI - Estado Actual y Siguiente Paso

Este documento resume lo que ya existe en el proyecto, como probarlo y que sigue.

## Vision

SentinelAI ya no es solo una camara con deteccion. La direccion actual es:

```text
Sistema inteligente preventivo
basado en vision artificial
analisis contextual
arquitectura multiagente
automatizacion
memoria historica
```

## Arquitectura Actual

```text
Webcam
  -> AgentePercepcion
  -> Supabase
  -> n8n / AgenteAnalisis workflow
  -> API Central AgenteAnalisis
  -> Dataset propio
```

Arquitectura objetivo:

```text
Camara
  -> AgentePercepcion
  -> AgenteTracking
  -> AgenteAnalisis
  -> AgenteRiesgo
  -> AgenteAccion
  -> AgenteMemoria / Supabase
  -> n8n
  -> Dashboard + Alertas
```

## Componentes Implementados

### 1. AgentePercepcion

Ubicacion:

```text
agente_percepcion/
```

Responsabilidad:

- Abrir camara.
- Detectar objetos con YOLOv8.
- Dibujar bounding boxes.
- Generar eventos JSON.
- Guardar eventos en Supabase.
- Enviar eventos a n8n.

Archivos clave:

```text
agente_percepcion/main.py
agente_percepcion/detector.py
agente_percepcion/camera.py
agente_percepcion/events.py
agente_percepcion/api.py
agente_percepcion/config.py
```

Mejoras actuales:

- Bounding box con etiqueta y confianza.
- Colores por tipo de objeto/riesgo.
- Camara robusta en Windows usando backends `directshow`, `msmf` y `any`.
- Envio a n8n con respuesta visible en consola.
- Guardado en Supabase.

Ejecutar:

```powershell
python -m agente_percepcion.main
```

Si la camara falla en Windows:

```env
SENTINEL_CAMERA_BACKEND=directshow
SENTINEL_CAMERA_INDEX=0
```

Probar API:

```powershell
uvicorn agente_percepcion.api:app --reload
```

Endpoints:

```text
GET  http://localhost:8000/health
GET  http://localhost:8000/events
POST http://localhost:8000/detect-once
```

### 2. Supabase

Supabase reemplazo a SQLite como base principal.

Tablas creadas:

```text
camaras
detection_events
```

Prisma:

```text
prisma/schema.prisma
prisma/migrations/20260526120000_init_supabase_schema/migration.sql
```

Notas:

- `.env` no se sube a Git.
- `.env.example` queda sin secretos.
- `SUPABASE_SERVICE_ROLE_KEY` solo debe usarse en backend local/servidor.
- Si la key se comparte por error, debe rotarse en Supabase.

### 3. n8n / AgenteAnalisis Workflow

Ubicacion:

```text
n8n/
```

Workflow:

```text
n8n/AgenteAnalisis.workflow.json
```

Flujo:

```text
Webhook - Evento Percepcion
  -> Normalizar Evento
  -> AgenteRiesgo - Score Hibrido
  -> AgenteAccion - Preparar Respuesta
  -> Responder a AgentePercepcion
```

Que hace:

- Recibe evento de Python.
- Normaliza objeto, confianza, camara, hora, box e imagen.
- Acepta contexto futuro:
  - zona
  - iluminacion
  - tracking
  - memoria
- Calcula score de riesgo.
- Decide accion:
  - `REGISTRAR_EVENTO`
  - `MONITOREAR`
  - `ENVIAR_ALERTA`
  - `ALERTA_CRITICA`

Probar n8n sin camara:

```powershell
python tools/test_n8n_webhook.py --payload n8n/test_payload_knife.json
```

Si el workflow esta activo:

```powershell
python tools/test_n8n_webhook.py --url http://localhost:5678/webhook/sentinel-analysis --payload n8n/test_payload_knife.json
```

Importante:

- `/webhook-test/sentinel-analysis` requiere `Listen for test event`.
- `/webhook/sentinel-analysis` requiere workflow activo.

### 4. API Central AgenteAnalisis

Ubicacion:

```text
agente_analisis/
```

Responsabilidad:

- Recibir percepcion + contexto + tracking + memoria.
- Calcular score de riesgo.
- Clasificar riesgo.
- Decidir accion.

Archivos:

```text
agente_analisis/api.py
agente_analisis/schemas.py
agente_analisis/risk_engine.py
```

Ejecutar:

```powershell
uvicorn agente_analisis.api:app --reload --port 8010
```

Endpoints:

```text
GET  http://localhost:8010/health
POST http://localhost:8010/analyze
```

El motor actual es deterministico y testeable. Mas adelante se puede sumar LLM contextual, pero no como decisor final.

### 5. Dataset Propio

Ubicacion:

```text
dataset/
tools/capture_dataset.py
```

Estructura:

```text
dataset/
  raw/
    normal/
    objeto_sospechoso/
    objeto_no_sospechoso/
    pelea/
    robo/
  yolo/
    images/train
    images/val
    images/test
    labels/train
    labels/val
    labels/test
  classes.txt
  data.yaml
```

Clases iniciales:

```text
person
knife
gun
backpack
cell_phone
```

Capturar imagenes:

```powershell
python tools/capture_dataset.py --scenario objeto_sospechoso --label knife --backend directshow
```

Controles:

```text
s = guardar frame
a = captura automatica
q = salir
```

Idea clave:

- `knife`, `gun`, `person` son clases YOLO.
- `robo`, `pelea`, `normal` son escenarios/contextos, no clases YOLO iniciales.

## Variables Importantes

Archivo local:

```text
.env
```

No se sube a Git.

Variables principales:

```env
SENTINEL_CAMERA_INDEX=0
SENTINEL_CAMERA_BACKEND=auto
SENTINEL_CAMERA_NAME=PC-01
SENTINEL_MODEL=yolov8n.pt
SENTINEL_CONFIDENCE=0.5
SENTINEL_CLASSES=person,knife,scissors,backpack,cell phone
SENTINEL_EVENT_COOLDOWN_SECONDS=5
SENTINEL_N8N_WEBHOOK_URL=http://localhost:5678/webhook/sentinel-analysis
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DETECTION_EVENTS_TABLE=detection_events
DATABASE_URL=
DIRECT_URL=
```

## Como Probar Todo por Capas

### 1. Pruebas automaticas

```powershell
python -m pytest
```

Estado actual esperado:

```text
12 passed
```

### 2. Probar n8n sin camara

En n8n:

```text
Open workflow -> Listen for test event
```

En terminal:

```powershell
python tools/test_n8n_webhook.py --payload n8n/test_payload_knife.json
```

### 3. Probar API de analisis

```powershell
uvicorn agente_analisis.api:app --reload --port 8010
```

Abrir:

```text
http://localhost:8010/health
```

### 4. Probar percepcion real

```powershell
python -m agente_percepcion.main
```

Debe ocurrir:

```text
camara abre
YOLO detecta
se dibuja bounding box
se guarda evento en Supabase
se envia evento a n8n
Python imprime respuesta de n8n
```

## Problemas Conocidos y Soluciones

### Camara no lee frames en Windows

Solucion:

```env
SENTINEL_CAMERA_BACKEND=directshow
```

Probar otro indice:

```env
SENTINEL_CAMERA_INDEX=1
```

### n8n no responde

Revisar:

- n8n esta corriendo en `localhost:5678`.
- workflow activo si usas `/webhook`.
- `Listen for test event` activo si usas `/webhook-test`.
- URL correcta en `.env`.

### Prisma migrate deploy falla

Ya se aplico el SQL inicial usando:

```powershell
npx prisma db execute --file prisma/migrations/20260526120000_init_supabase_schema/migration.sql --schema prisma/schema.prisma
```

## Lo Que Sigue

El gap analysis y roadmap priorizado estan en `docs/ROADMAP_COMPLETO.md`.

### Paso 1 - Prueba End-to-End

Objetivo:

```text
camara detecta persona
-> evento en Supabase
-> n8n responde
-> consola muestra decision
```

### Paso 2 - Capturar Dataset Real

Meta inicial:

```text
20-30 imagenes por clase para prueba
despues 200-500 imagenes balanceadas
```

Clases:

```text
person
knife
gun
backpack
cell_phone
```

### Paso 3 - Etiquetado YOLO

Herramienta recomendada:

```powershell
pip install labelImg
labelImg
```

Formato:

```text
YOLO
```

### Paso 4 - Entrenar Modelo Propio

Entrenar en Google Colab con GPU:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.train(data="dataset/data.yaml", epochs=50, imgsz=640)
```

Resultado:

```text
best.pt
```

Luego:

```env
SENTINEL_MODEL=agente_percepcion/model/best.pt
```

### Paso 5 - AgenteTracking

Agregar ByteTrack o DeepSORT.

Objetivo:

- IDs de personas.
- permanencia.
- velocidad.
- movimiento repetitivo.
- comportamiento anomalo.

### Paso 6 - Memoria Real

Consultar Supabase para:

- eventos previos 24h.
- alertas previas 24h.
- historial por camara/zona.

### Paso 7 - Alertas

n8n puede enviar:

- Telegram.
- Discord.
- Email.
- dashboard realtime.

### Paso 8 - Dashboard

Dashboard futuro:

- eventos recientes.
- camaras.
- alertas.
- score de riesgo.
- imagenes.
- historico.

## Regla de Oro

No construir "IA policial perfecta".

Construir:

```text
Sistema inteligente preventivo
basado en vision artificial
y analisis contextual multiagente
```

Eso es realista, escalable y defendible.
