# SentinelAI - Arquitectura Multiagente

SentinelAI es un sistema inteligente de monitoreo preventivo basado en vision artificial, analisis contextual y arquitectura multiagente.

## Principios

- `AgentePercepcion` detecta objetos, no toma decisiones.
- `AgenteTracking` asigna IDs y calcula comportamiento temporal.
- `AgenteAnalisis` interpreta contexto y prepara evidencia.
- `AgenteRiesgo` calcula puntaje y nivel de riesgo.
- `AgenteAccion` decide notificaciones y flujos.
- `AgenteMemoria` persiste eventos e historial en Supabase.
- n8n orquesta acciones, no hace IA pesada.

## Flujo Objetivo

```text
Camara/Webcam
  -> AgentePercepcion
  -> AgenteTracking
  -> AgenteAnalisis
  -> AgenteRiesgo
  -> AgenteAccion
  -> Supabase
  -> n8n
  -> Dashboard + Alertas
```

## Estado Actual

```text
AgentePercepcion
  -> YOLOv8 + OpenCV
  -> bounding boxes
  -> eventos JSON
  -> Supabase
  -> n8n

AgenteAnalisis
  -> FastAPI /analyze
  -> score matematico
  -> decision de accion

n8n
  -> Webhook sentinel-analysis
  -> normalizacion
  -> score hibrido
  -> decision para alertas
```

## Contrato del AgenteAnalisis

Entrada:

```json
{
  "evento": {
    "objeto": "knife",
    "confianza": 0.91,
    "hora": "2026-05-26T23:40:00Z",
    "camara": "PC-01",
    "box": [10, 20, 200, 300],
    "imagen": null
  },
  "contexto": {
    "zona": "entrada_principal",
    "iluminacion": "baja",
    "cantidad_personas": 1
  },
  "tracking": {
    "person_id": "track_14",
    "velocidad": 8.2,
    "permanencia_segundos": 420,
    "movimiento_erratico": true
  },
  "memoria": {
    "eventos_previos_24h": 12,
    "alertas_previas_24h": 2
  }
}
```

Salida:

```json
{
  "status": "procesado",
  "result": {
    "risk_level": "CRITICO",
    "risk_score": 120,
    "possible_behavior": "posible_amenaza_con_objeto_peligroso"
  },
  "decision": {
    "action": "ALERTA_CRITICA",
    "priority": 10,
    "notify": true,
    "channels": ["telegram", "dashboard_realtime"]
  }
}
```

## Fases

1. YOLO funcionando con webcam.
2. Dataset propio y etiquetado.
3. Tracking con ByteTrack o DeepSORT.
4. AgenteAnalisis + AgenteRiesgo.
5. Memoria real en Supabase.
6. n8n para alertas y automatizacion.
7. Prediccion ML con scikit-learn cuando haya datos.
8. Dashboard.

## Nota Sobre LLM

Un LLM como OpenAI o Grok no debe detectar objetos ni tomar decisiones finales. Su rol futuro sera interpretar contexto y generar razonamiento auxiliar. La decision final debe combinar reglas, score, historial y revision humana cuando el riesgo sea alto.
