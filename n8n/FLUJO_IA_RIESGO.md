# Flujo IA + AgenteRiesgo + Supervisor Humano en n8n

Este flujo usa IA como analista contextual, pero la decision final la valida
el motor Python `agente_analisis.risk_engine`. n8n no recalcula riesgo: valida
el resultado recibido, notifica, procesa botones y orquesta la respuesta.

El vocabulario activo del modelo `yolo_percepcion` es:

```text
arma, arma_blanca, fusil, multitud, no_violencia, persona,
persona_sospechosa, undefined, violencia
```

Las reglas aceptan alias del modelo viejo (`Violence`, `NonViolence`) y de objetos
en ingles (`gun`, `knife`, `person`), pero normalizan todo a las clases nuevas.

## Flujo importable actual

```text
Webhook - Evento Percepcion
  -> Normalizar Evento
  -> AgenteRiesgo - Validar Analisis Python
  -> AgenteAccion - Preparar Respuesta
  -> Requiere Revision Humana?
      true:
        -> Responder a AgentePercepcion
        -> AgenteInterfazHumana - Preparar Telegram
        -> Telegram Supervisor - Enviar Validacion
      false:
        -> Responder a AgentePercepcion

Webhook - Callback Telegram Supervisor
  -> AgenteInterfazHumana - Procesar Callback
  -> Responder Callback Telegram

Telegram Trigger - Callback Supervisor
  -> AgenteInterfazHumana - Procesar Callback
  -> Responder Callback Telegram
  -> Telegram Supervisor - Responder Callback
```

El workflow `n8n/AgenteAnalisis.workflow.json` ya contiene estos nodos. Python recibe
respuesta rapido por `Responder a AgentePercepcion`; la validacion por Telegram queda
como rama paralela/asincrona cuando `decision.requiere_revision_humana=true`.

Si llega un payload crudo sin `entrada`, `resultado` y `decision`, n8n responde
`RECHAZAR_EVENTO_SIN_ANALISIS`. Eso es intencional: hay un solo AgenteRiesgo
oficial y vive en Python.

## Evidencia visual en Supabase Storage

La tabla `detection_events` ya tiene la columna `imagen_url` desde la migracion
inicial, por eso no se crea una migracion nueva para ese campo. El flujo actual
guarda la captura anotada en Supabase Storage y reemplaza `entrada.imagen` por la
URL publica antes de enviar el evento a n8n y antes de guardar el registro en
Supabase.

Variables usadas por Python:

```text
SENTINEL_UPLOAD_EVIDENCE=true
SUPABASE_STORAGE_BUCKET=imagen
```

El bucket `imagen` debe existir en Supabase Storage. Si el bucket es publico,
Telegram y el dashboard pueden abrir la URL guardada en `detection_events.imagen_url`.

## Flujo IA extendido opcional

Si quieres activar LLM/Groq y memoria externa, usa los snippets de `n8n/code/`
como expansion del flujo anterior:

```text
Webhook - Evento Percepcion
  -> Preparar_Datos
  -> AgenteAnalisis_IA
  -> Parsear_JSON_LLM
  -> Consultar_Historial
  -> Calcular_Riesgo_Code
  -> AgenteInterfazHumana / Telegram
  -> Responder a AgentePercepcion
```

## Codigo por nodo

- `Preparar_Datos`: `n8n/code/Preparar_Datos_IA.js`
- `AgenteAnalisis_IA`: prompt de sistema `n8n/code/SYSTEM_PROMPT_AGENTE_ANALISIS_IA.md`
- `Parsear_JSON_LLM`: `n8n/code/Parsear_JSON_LLM.js`
- `Calcular_Riesgo_Code`: `n8n/code/Calcular_Riesgo_Code.js`
- Antes de `Alerta_Final_Telegram`: `n8n/code/Preparar_Alerta_Telegram.js`
- En el webhook de callback de Telegram: `n8n/code/Procesar_Respuesta_Supervisor_Telegram.js`
- Antes de `Registrar_Memoria_Sheets`: `n8n/code/Preparar_Memoria_Sheets.js`
- Antes de `Respond_to_Webhook`: `n8n/code/Responder_Webhook_Final.js`

## AgenteAnalisis_IA

Entrada del usuario:

```text
{{$json.prompt_ia}}
```

Salida esperada:

```json
{
  "nivel_riesgo": "BAJO",
  "score_sugerido": 20,
  "confianza_analisis": 0.7,
  "resumen": "Persona detectada sin objeto peligroso.",
  "factores_ia": [],
  "recomendar_subir_riesgo": false,
  "requiere_revision_humana": false
}
```

## Umbral_Confianza_IF

Usa un nodo `IF`.

Condicion principal:

```text
{{$json.resultado.ia_confianza >= 0.55 || $json.entrada.confianza >= 0.75}}
```

Rama `true`: continua al historial y calculo de riesgo.

Rama `false`: manda Telegram de validacion humana y luego continua despues del
timeout. Esta rama evita que una deteccion dudosa dispare una alerta automatica.

## Consultar_Historial_Sheets

Configura Google Sheets para traer las filas recientes de memoria. Columnas
recomendadas:

```text
detected_at
camara_id
objeto
confianza
score_riesgo
nivel_riesgo
accion_tomada
track_id
person_id
velocidad
permanencia_segundos
movimiento_erratico
eventos_previos_24h
alertas_previas_24h
resumen_ia
requiere_revision_humana
estado_revision_humana
automatizacion_bloqueada
factores
factores_ia
mensaje
procesado_en
```

Si todavia no tienes Sheets listo, puedes saltar este nodo y conectar
`Parsear_JSON_LLM` directo a `Calcular_Riesgo_Code`; el calculo funciona sin
historial, solo con menor contexto.

## Nivel_Riesgo_Switch

Usa `Switch` en modo Rules sobre:

```text
{{$json.resultado.nivel_riesgo}}
```

Reglas:

```text
CRITICO
ALTO
MEDIO
BAJO
```

Rutas recomendadas:

- `CRITICO`: Telegram urgente con botones + esperar supervisor + accion final.
- `ALTO`: Telegram supervisor con botones + esperar supervisor + accion final.
- `MEDIO`: Telegram supervisor con botones + esperar supervisor o timeout.
- `BAJO`: memoria + respuesta.

## Telegram Supervisor

`Preparar_Alerta_Telegram.js` genera `reply_markup.inline_keyboard` con:

```json
{
  "inline_keyboard": [
    [
      {"text": "Confirmar amenaza", "callback_data": "sentinel:confirm:REVIEW_ID"},
      {"text": "Falso positivo", "callback_data": "sentinel:false:REVIEW_ID"}
    ],
    [
      {"text": "Mas revision", "callback_data": "sentinel:review:REVIEW_ID"}
    ]
  ]
}
```

El workflow ya incluye un segundo webhook para callbacks de Telegram:

```text
http://localhost:5678/webhook/sentinel-telegram-callback
```

Ese webhook usa
`Procesar_Respuesta_Supervisor_Telegram.js` y devuelve:

```json
{
  "source": "telegram_supervisor",
  "review_id": "PC01_knife_20260527",
  "supervisor": {
    "human_label": "real_threat",
    "estado_revision_humana": "CONFIRMADA",
    "accion_final": "ACTIVAR_PROTOCOLO",
    "alimentar_entrenamiento": true
  }
}
```

## Configuracion del bot de Telegram en n8n

El workflow importable usa nodos nativos de Telegram:

- `Telegram Supervisor - Enviar Validacion`
- `Telegram Trigger - Callback Supervisor`

Pasos:

1. Crea un bot en Telegram con `@BotFather`.
2. Copia el token del bot.
3. En n8n crea una credencial de tipo `Telegram API`.
4. Pega el token en esa credencial.
5. Asigna esa credencial a los dos nodos de Telegram.
6. Define `SENTINEL_TELEGRAM_CHAT_ID` en el entorno donde corre n8n.
7. Activa el workflow para que `Telegram Trigger - Callback Supervisor` registre el webhook del bot.

El envio de mensajes usa el `chatId` desde:

```text
{{$env.SENTINEL_TELEGRAM_CHAT_ID}}
```

El token del bot no debe ir en el JSON del workflow ni en codigo; debe vivir en
la credencial segura de n8n.

El webhook `sentinel-telegram-callback` queda como respaldo manual si decides
configurar el callback del bot por URL externa en vez de usar `Telegram Trigger`.

Reglas de accion final:

- `CONFIRMADA`: registrar incidente, guardar evidencia y activar protocolo definido.
- `FALSO_POSITIVO`: cerrar evento y guardar muestra para entrenamiento.
- `REQUIERE_MAS_REVISION`: solicitar mas frames/contexto y reanalizar.

La IA y Groq pueden recomendar o explicar, pero no deben cambiar
`accion_final` sin respuesta humana.

## Respuesta final al webhook

El `Respond to Webhook` debe responder con el JSON que sale de
`Responder_Webhook_Final.js`. Ese JSON es el que Python guarda luego en Supabase.

