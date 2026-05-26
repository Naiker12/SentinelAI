# AgenteAnalisis en n8n

Este workflow recibe eventos del `AgentePercepcion`, calcula el riesgo y responde con una accion recomendada.

## Importar

1. Abre n8n.
2. Ve a `Workflows`.
3. Selecciona `Import from File`.
4. Importa `n8n/AgenteAnalisis.workflow.json`.
5. Activa el workflow para usar la URL de produccion.

## URLs

Cuando el workflow esta activo:

```text
http://localhost:5678/webhook/sentinel-analysis
```

Cuando pruebas desde el editor de n8n con `Listen for test event`:

```text
http://localhost:5678/webhook-test/sentinel-analysis
```

## Payload de entrada

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

## Respuesta esperada

```json
{
  "status": "procesado",
  "agente": "AgenteAnalisis",
  "version": "0.1.0",
  "entrada": {
    "objeto": "knife",
    "confianza": 0.91,
    "camara": "PC-01",
    "hora": "2026-05-26T20:30:00.000000+00:00",
    "box": [10, 20, 200, 300],
    "imagen": null
  },
  "resultado": {
    "riesgo": "ALTO",
    "accion": "ENVIAR_ALERTA",
    "prioridad": 10,
    "motivo": "Objeto peligroso detectado: knife."
  },
  "procesado_en": "2026-05-26T20:31:00.000Z"
}
```

## Reglas actuales

- `knife`, `gun`, `scissors`: riesgo `ALTO` si la confianza es mayor o igual a `0.6`.
- `person`, `car`, `truck`, `backpack`, `cell phone`: riesgo `MEDIO` si la confianza es mayor o igual a `0.5`.
- Confianza menor a `0.5`: accion `IGNORAR_BAJA_CONFIANZA`.
- Payload sin `objeto`: accion `REVISAR_PAYLOAD`.
