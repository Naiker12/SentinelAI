# Flujo IA + AgenteRiesgo en n8n

Este flujo usa IA como analista contextual, pero la decision final la valida
`Calcular_Riesgo_Code` con reglas, historial y limites.

## Orden recomendado

```text
AgentePercepcion_Webhook
  -> Preparar_Datos
  -> AgenteAnalisis_IA
  -> Parsear_JSON_LLM
  -> Umbral_Confianza_IF
    true  -> Consultar_Historial_Sheets -> Calcular_Riesgo_Code
    false -> Solicitar_Validacion_Telegram -> Wait_Timeout -> Consultar_Historial_Sheets
  -> Nivel_Riesgo_Switch
    CRITICO -> Alerta_Final_Telegram -> Simular_Envio_Accion -> Registrar_Memoria_Sheets -> Respond_to_Webhook
    ALTO    -> Alerta_Final_Telegram -> Simular_Envio_Accion -> Registrar_Memoria_Sheets -> Respond_to_Webhook
    MEDIO   -> Registrar_Memoria_Sheets -> Respond_to_Webhook
    BAJO    -> Registrar_Memoria_Sheets -> Respond_to_Webhook
```

## Codigo por nodo

- `Preparar_Datos`: `n8n/code/Preparar_Datos_IA.js`
- `AgenteAnalisis_IA`: prompt de sistema `n8n/code/SYSTEM_PROMPT_AGENTE_ANALISIS_IA.md`
- `Parsear_JSON_LLM`: `n8n/code/Parsear_JSON_LLM.js`
- `Calcular_Riesgo_Code`: `n8n/code/Calcular_Riesgo_Code.js`
- Antes de `Alerta_Final_Telegram`: `n8n/code/Preparar_Alerta_Telegram.js`
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

- `CRITICO`: Telegram + accion + memoria + respuesta.
- `ALTO`: Telegram + accion + memoria + respuesta.
- `MEDIO`: memoria + respuesta.
- `BAJO`: memoria + respuesta.

## Respuesta final al webhook

El `Respond to Webhook` debe responder con el JSON que sale de
`Responder_Webhook_Final.js`. Ese JSON es el que Python guarda luego en Supabase.
