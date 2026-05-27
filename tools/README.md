# Herramientas

## Captura de dataset

```powershell
python tools/capture_dataset.py --scenario objeto_sospechoso --label knife
```

Controles:

- `s`: guarda el frame actual.
- `a`: activa o desactiva captura automatica.
- `q`: cierra la camara.

## Probar n8n sin camara

Con `Listen for test event` activo en n8n:

```powershell
python tools/test_n8n_webhook.py --payload ruta\al\payload_analizado.json
```

Con el workflow activo:

```powershell
python tools/test_n8n_webhook.py --url http://localhost:5678/webhook/sentinel-analysis --payload ruta\al\payload_analizado.json
```

El payload debe venir enriquecido por `agente_analisis.risk_engine` con
`resultado` y `decision`. Los eventos crudos se rechazan por diseno.
