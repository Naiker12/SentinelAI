# SentinelAI - Estado Actual

Fecha: 2026-05-27

## Estado Actual

SentinelAI queda configurado para trabajar con el modelo propio `best.pt` entrenado en Google Colab para violencia/no violencia.

Flujo activo:

```text
Camara
  -> AgentePercepcion
  -> AgenteAnalisis
  -> AgenteRiesgo
  -> AgenteAccion
  -> AgenteMemoria
  -> n8n
  -> AgenteInterfazHumana
  -> Dashboard / Supabase / Telegram
```

## Cambios Aplicados

- Se elimino `agente_percepcion/tracking.py`.
- Se movio la memoria temporal a `agente_percepcion/memory.py`.
- `main.py` usa cooldown por camara+objeto.
- `SENTINEL_MODEL` apunta a `agente_percepcion/model/best.pt`.
- El campo `tracking` queda solo como compatibilidad y normalmente viaja vacio.
- El dashboard reemplaza `AgenteTracking` por `Interfaz Humana`.
- n8n queda preparado para `review_id`, botones de Telegram y feedback de supervisor.

## Agentes Activos

| Agente | Estado | Funcion |
|---|---|---|
| AgentePercepcion | Activo | Camara, YOLO, eventos, Supabase, n8n |
| AgenteAnalisis | Activo | Normaliza evento y aplica reglas |
| AgenteRiesgo | Activo | Score deterministico 0-100 |
| AgenteAccion | Activo | Decide notificacion/revision humana |
| AgenteMemoria | Parcial | RAM temporal + Supabase |
| AgenteInterfazHumana | Activo | Telegram supervisor + dashboard |

## Modelo

Ruta esperada:

```env
SENTINEL_MODEL=agente_percepcion/model/best.pt
SENTINEL_CLASSES=violence,nonviolence
```

El modelo reporta `NonViolence` y `Violence`; el detector normaliza esas clases a `nonviolence` y `violence`.
