# AgenteAnalisis en n8n

Este workflow recibe eventos ya analizados por `AgentePercepcion`/`AgenteRiesgo`
en Python y orquesta la respuesta. n8n no calcula el score de riesgo para evitar
duplicar logica.

n8n no hace IA pesada. En esta arquitectura n8n orquesta, decide acciones y conecta alertas. La vision artificial y la prediccion pesada deben vivir en Python/FastAPI.

## Flujo

```text
Webhook - Evento Percepcion
  -> Normalizar Evento
  -> AgenteRiesgo - Validar Analisis Python
  -> AgenteAccion - Preparar Respuesta
  -> Responder a AgentePercepcion
```

## Flujo IA recomendado

Si usas el flujo visual con Groq como en tu captura, dejalo asi:

```text
AgentePercepcion_Webhook
  -> Preparar_Datos
  -> AgenteAnalisis_IA
  -> Parsear_JSON_LLM
  -> guardar / alerta / respuesta

Groq_Chat_Model
  -> AgenteAnalisis_IA
```

Codigo para cada nodo:

- `Preparar_Datos`: pega `n8n/code/Preparar_Datos_IA.js`.
- `AgenteAnalisis_IA`: usa el prompt de sistema de `n8n/code/SYSTEM_PROMPT_AGENTE_ANALISIS_IA.md`.
- En el campo de entrada del agente IA, envia `{{$json.prompt_ia}}`.
- `Parsear_JSON_LLM`: pega `n8n/code/Parsear_JSON_LLM.js`.

El nodo IA solo recomienda y explica. El resultado final de riesgo debe venir de
Python; cualquier flujo visual con IA debe conservar `resultado` y `decision` del
AgenteRiesgo oficial.

Para el flujo completo con historial, switch de riesgo, Telegram y memoria, usa
la guia `n8n/FLUJO_IA_RIESGO.md`.

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

## Contrato recibido desde la camara real

La camara real debe enviar el contrato enriquecido que produce
`agente_analisis.risk_engine`. Si n8n recibe un evento crudo sin `resultado` y
`decision`, lo rechaza con `RECHAZAR_EVENTO_SIN_ANALISIS`.

## Respuesta esperada

n8n devuelve el mismo analisis oficial de Python, enriquecido con estado de
orquestacion y datos listos para persistencia/notificacion.

El objeto `persistencia` ya viene preparado para guardar el evento enriquecido en Supabase.

## Reglas actuales

Las reglas viven solo en `agente_analisis/risk_engine.py`. El algoritmo oficial es
`risk_rules_v2_knn_temporal`: reglas deterministicas, tracking temporal, memoria y
KNN historico. n8n solo valida que esos campos existan y orquesta notificaciones.

## Como debe quedar en n8n para camara real

1. Importa `n8n/AgenteAnalisis.workflow.json`.
2. Abre el nodo `Webhook - Evento Percepcion`.
3. Confirma metodo `POST` y path `sentinel-analysis`.
4. Guarda el workflow.
5. Activa el workflow.
6. En `.env`, usa `SENTINEL_N8N_WEBHOOK_URL=http://localhost:5678/webhook/sentinel-analysis`.
7. Ejecuta la camara con `python -m agente_percepcion.main`.

No uses `/webhook-test/sentinel-analysis` con la camara real salvo que tengas el
editor de n8n abierto esperando un unico evento de prueba.

## Pruebas

La prueba real recomendada es ejecutar la camara, porque Python genera el JSON
enriquecido con `resultado` y `decision`:

```powershell
python -m agente_percepcion.main
```

Si quieres probar con `curl`, usa un payload capturado del agente real y ya
analizado por Python. Los eventos crudos seran rechazados por diseno.

## Prueba recomendada desde Python

Antes de abrir la camara, prueba n8n asi:

```powershell
python tools/test_n8n_webhook.py --payload ruta\al\payload_analizado.json
```

Si el workflow esta activo, usa la URL productiva:

```powershell
python tools/test_n8n_webhook.py --url http://localhost:5678/webhook/sentinel-analysis --payload ruta\al\payload_analizado.json
```

## Si parece que no pasa nada

- Para `/webhook-test/sentinel-analysis`, n8n debe estar en `Listen for test event`.
- Para `/webhook/sentinel-analysis`, el workflow debe estar activo.
- Si Python muestra `connection refused`, n8n no esta corriendo en `localhost:5678`.
- Si Python muestra `404`, estas usando la URL equivocada o el workflow no esta activo.
- Si Python detecta objetos pero no envia eventos seguido, revisa `SENTINEL_EVENT_COOLDOWN_SECONDS`.

## Siguientes fases

- `AgenteInterfazHumana`: Telegram + tabla `human_reviews` para validacion de supervisor.
- `AgenteMemoria`: consultas a Supabase para historial real.
- `AgentePrediccion`: modelo ML con scikit-learn cuando exista dataset suficiente.
- `AgenteAccion`: Telegram, Discord, email y dashboard realtime.
