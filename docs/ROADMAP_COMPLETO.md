# SentinelAI - Analisis Completo y Hoja de Ruta

Fecha de analisis: 2026-05-26

Este documento complementa `docs/ESTADO_ACTUAL.md` y sirve como gap analysis profesional del proyecto.

## 1. Estado Real del Proyecto

| Componente | Estado | Notas |
|---|---|---|
| AgentePercepcion | Implementado | YOLOv8, OpenCV, bounding boxes, Supabase y n8n |
| Supabase | Implementado | `camaras`, `detection_events` |
| n8n workflow | Implementado | Normaliza evento, calcula score y responde accion |
| API AgenteAnalisis | Implementado | FastAPI, motor deterministico |
| Dataset propio | Preparado | Captura manual/automatica y estructura YOLO |
| Tests automaticos | Implementado | Suite pytest |
| AgenteTracking | Pendiente | ByteTrack o DeepSORT |
| AgenteMemoria real | Pendiente | Consultas historicas a Supabase |
| Alertas Telegram/Discord | Pendiente | Variables y flujo documentados |
| Dashboard | Pendiente | Eventos, alertas, score, imagenes |
| Modelo propio | Pendiente | Actualmente `yolov8n.pt` generico |

## 2. Brecha Actual

El documento academico puede describir muchos agentes, pero el codigo debe crecer por fases. Hoy tenemos una base funcional de percepcion, analisis deterministico, Supabase, n8n y dataset. Lo correcto es fortalecer esa base antes de agregar drones, dashboard avanzado o prediccion.

## 3. Flujo n8n Objetivo

```text
Webhook - AgentePercepcion
  -> Normalizar & Validar Evento
  -> AgenteMemoria - Consultar Historial
  -> AgenteContexto - Enriquecer Evento
  -> AgenteRiesgo - Score Hibrido
  -> AgenteAccion - Decidir Protocolo
  -> AgenteMemoria - Guardar Evento Procesado
  -> Responder a AgentePercepcion
```

## 4. Schema Supabase Enriquecido

Se agregan columnas opcionales a `detection_events` sin romper el flujo actual:

```text
score_riesgo
nivel_riesgo
accion_tomada
alertas_previas_24h
hora_dia
contexto
```

Nota: usamos `detected_at`, no `timestamp`, porque esa es la columna real del proyecto.

Migracion:

```text
prisma/migrations/20260526123000_add_enriched_detection_fields/migration.sql
```

Aplicar cuando quieras actualizar Supabase:

```powershell
npx prisma db execute --file prisma/migrations/20260526123000_add_enriched_detection_fields/migration.sql --schema prisma/schema.prisma
```

## 5. Variables Nuevas

```env
SENTINEL_TELEGRAM_BOT_TOKEN=
SENTINEL_TELEGRAM_CHAT_ID=
SENTINEL_RISK_THRESHOLD_MEDIO=0.35
SENTINEL_RISK_THRESHOLD_ALTO=0.60
SENTINEL_RISK_THRESHOLD_CRITICO=0.80
SENTINEL_HISTORIAL_HORAS=24
```

## 6. Prioridades

### Corto plazo

1. Aplicar migracion enriquecida a Supabase.
2. Probar n8n con `tools/test_n8n_webhook.py`.
3. Conectar alerta Telegram en ramas `ALTO` y `CRITICO`.
4. Prueba end-to-end: camara -> deteccion -> n8n -> Supabase -> alerta.

### Mediano plazo

5. Capturar dataset real.
6. Etiquetar con LabelImg.
7. Entrenar modelo propio en Colab.
8. Integrar AgenteTracking.

### Largo plazo

9. AgenteMemoria real con consultas historicas.
10. Dashboard.
11. Revision humana para eventos criticos.
12. Agentes academicos adicionales: Drone, ReporteCiudadano, InterfazHumana.

## 7. Regla de Oro

No construir una IA policial perfecta.

Construir un sistema inteligente preventivo basado en vision artificial y analisis contextual multiagente.
