# AgenteAnalisis en n8n

Este workflow recibe eventos del `AgentePercepcion`, normaliza el payload, calcula un score de riesgo y responde con una accion recomendada.

n8n no hace IA pesada. En esta arquitectura n8n orquesta, decide acciones y conecta alertas. La vision artificial, tracking y prediccion pesada deben vivir en Python/FastAPI.

## Flujo

```text
Webhook - Evento Percepcion
  -> Normalizar Evento
  -> AgenteRiesgo - Score Hibrido
  -> AgenteAccion - Preparar Respuesta
  -> Responder a AgentePercepcion
```

## Importar

1. Abre n8n.
2. Ve a `Workflows`.
3. Selecciona `Import from File`.
4. Importa `n8n/AgenteAnalisis.workflow.json`.
5. Activa el workflow para usar la URL de produccion.

## URLs

Workflow activo:

```text
http://localhost:5678/webhook/sentinel-analysis
```

Prueba desde el editor con `Listen for test event`:

```text
http://localhost:5678/webhook-test/sentinel-analysis
```

## Payload minimo

```json
{
  "objeto": "knife",
  "confianza": 0.91,
  "hora": "2026-05-26T20:30:00.000000+00:00",
  "camara": "PC-01",
  "box": [10, 20, 200, 300],
  "imagen": null
}
```

## Payload profesional opcional

```json
{
  "objeto": "knife",
  "confianza": 0.91,
  "hora": "2026-05-26T23:30:00.000000+00:00",
  "camara": "PC-01",
  "box": [10, 20, 200, 300],
  "imagen": null,
  "contexto": {
    "zona": "entrada_principal",
    "iluminacion": "baja"
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

## Respuesta esperada

```json
{
  "status": "procesado",
  "pipeline": [
    "AgentePercepcion",
    "AgenteAnalisis",
    "AgenteRiesgo",
    "AgenteAccion",
    "AgenteMemoria"
  ],
  "resultado": {
    "riesgo": "ALTO",
    "severidad": "CRITICA",
    "score": 100,
    "algoritmo": "risk_rules_v1"
  },
  "decision": {
    "accion": "ALERTA_CRITICA",
    "prioridad": 10,
    "notificar": true,
    "canales": ["telegram", "dashboard_realtime"],
    "guardar_en_supabase": true,
    "requiere_revision_humana": true
  }
}
```

## Reglas actuales

El score va de `0` a `100`.

- `knife`, `gun`, `scissors`: suman riesgo alto.
- `person`, `car`, `truck`, `motorcycle`, `backpack`, `cell_phone`: suman riesgo medio.
- Confianza alta suma puntos.
- Confianza baja resta puntos.
- Horario nocturno suma puntos.
- Baja iluminacion suma puntos.
- Velocidad alta suma puntos.
- Movimiento erratico suma puntos.
- Permanencia mayor a 5 o 15 minutos suma puntos.
- Historial reciente de eventos o alertas suma puntos.

Niveles:

- `0-24`: `BAJO`
- `25-49`: `MEDIO`
- `50-100`: `ALTO`

## Pruebas con curl

Alto riesgo:

```powershell
curl.exe -X POST http://localhost:5678/webhook-test/sentinel-analysis -H "Content-Type: application/json" --data-binary "@n8n/test_payload_knife.json"
```

Caso normal:

```powershell
curl.exe -X POST http://localhost:5678/webhook-test/sentinel-analysis -H "Content-Type: application/json" --data-binary "@n8n/test_payload_normal.json"
```

## Siguientes fases

- `AgenteTracking`: ByteTrack/DeepSORT en Python.
- `AgenteMemoria`: consultas a Supabase para historial real.
- `AgentePrediccion`: modelo ML con scikit-learn cuando exista dataset suficiente.
- `AgenteAccion`: Telegram, Discord, email y dashboard realtime.
