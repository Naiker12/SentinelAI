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
python tools/test_n8n_webhook.py --payload n8n/test_payload_knife.json
```

Con el workflow activo:

```powershell
python tools/test_n8n_webhook.py --url http://localhost:5678/webhook/sentinel-analysis --payload n8n/test_payload_normal.json
```
