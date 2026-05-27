# SentinelAI - Arquitectura Multiagente

SentinelAI es un sistema inteligente de monitoreo preventivo basado en vision artificial, analisis contextual y arquitectura multiagente.

## Principios

- `AgentePercepcion` detecta objetos, no toma decisiones.
- `AgenteAnalisis` interpreta contexto y prepara evidencia.
- `AgenteRiesgo` calcula puntaje y nivel de riesgo.
- `AgenteAccion` decide notificaciones y flujos.
- `AgenteMemoria` persiste eventos e historial en Supabase.
- `AgenteInterfazHumana` valida alertas con supervisor por Telegram/Dashboard.
- n8n orquesta acciones, no hace IA pesada.

## Flujo Actual Recomendado

```text
Camara/Webcam/RTSP
  -> Servicio Python IA
     -> YOLO
     -> AgenteAnalisis
     -> AgenteRiesgo
     -> JSON limpio
  -> n8n
     -> Webhook
     -> historial / memoria externa
     -> Groq solo para explicacion
     -> Telegram / Dashboard / Supabase
```

## Estado Actual

```text
AgentePercepcion
  -> YOLOv8 + OpenCV
  -> bounding boxes
  -> cooldown por camara/objeto
  -> eventos JSON
  -> Supabase
  -> n8n

AgenteAnalisis
  -> FastAPI /analyze
  -> score matematico
  -> decision de accion

n8n
  -> Webhook sentinel-analysis
  -> acepta resultado precomputado de Python
  -> mantiene fallback de normalizacion y score simple
  -> orquesta alertas y persistencia
```

El contrato preferido ahora es `Python calcula, n8n orquesta`. Si el payload ya trae
`entrada`, `resultado`, `decision` y `persistencia`, el workflow no debe recalcular
el riesgo. Los nodos de riesgo en n8n quedan como fallback para pruebas manuales o
payloads antiguos.

## Contrato del AgenteAnalisis

Entrada:

```json
{
  "evento": {
    "objeto": "arma_blanca",
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
  "tracking": {},
  "memoria": {
    "eventos_previos_24h": 12,
    "alertas_previas_24h": 2
  }
}
```

## Contrato Enviado a n8n

`AgentePercepcion` ejecuta el motor Python antes del webhook y envia un objeto listo
para orquestacion:

```json
{
  "entrada": {
    "objeto": "arma",
    "confianza": 0.94,
    "camara": "PC-01",
    "hora": "2026-05-26T23:40:00Z",
    "box": [10, 20, 200, 300],
    "imagen": null
  },
  "tracking": {},
  "resultado": {
    "nivel_riesgo": "CRITICO",
    "score": 120,
    "score_riesgo": 1.2,
    "algoritmo": "risk_rules_v5_seguridad_multiclase"
  },
  "decision": {
    "accion_tomada": "ALERTA_CRITICA",
    "notificar": true,
    "canales": ["telegram", "dashboard_realtime"]
  },
  "persistencia": {
    "camara_id": "PC-01",
    "objeto": "arma",
    "nivel_riesgo": "CRITICO"
  }
}
```

Groq puede enriquecer `resultado.resumen_ia`, pero no debe reemplazar el score ni
la decision final del motor de reglas.

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
3. Modelo propio `best.pt` entrenado con dataset real.
4. AgenteAnalisis + AgenteRiesgo.
5. Memoria real en Supabase.
6. n8n para alertas y automatizacion.
7. Prediccion ML con scikit-learn cuando haya datos.
8. Dashboard.

## Nota Sobre LLM

Un LLM como OpenAI o Grok no debe detectar objetos ni tomar decisiones finales. Su rol futuro sera interpretar contexto y generar razonamiento auxiliar. La decision final debe combinar reglas, score, historial y revision humana cuando el riesgo sea alto.
