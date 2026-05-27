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
  -> score matematico + KNN local de apoyo
  -> decision de accion

n8n
  -> Webhook sentinel-analysis
  -> acepta resultado precomputado de Python
  -> orquesta alertas y persistencia
```

El contrato preferido ahora es `Python calcula, n8n orquesta`. Si el payload ya trae
`entrada`, `resultado`, `decision` y `persistencia`, el workflow no debe recalcular
el riesgo. Si llega un payload crudo, n8n responde `RECHAZAR_EVENTO_SIN_ANALISIS`
para evitar dos fuentes de verdad.

## Contrato del AgenteAnalisis

Entrada: evento detectado, contexto de escena, tracking y memoria real disponible.

## Contrato Enviado a n8n

`AgentePercepcion` ejecuta el motor Python antes del webhook y envia un objeto listo
para orquestacion. El contrato debe incluir `entrada`, `tracking`, `memoria`,
`resultado`, `decision` y `persistencia`.

Groq puede enriquecer `resultado.resumen_ia`, pero no debe reemplazar el score ni
la decision final del motor de reglas.

El KNN local compara el evento actual contra prototipos internos de bajo, medio,
alto y critico usando distancia euclidiana. Solo ajusta el score como factor
explicable; no reemplaza la deteccion YOLO ni la validacion humana.

Salida: resultado normalizado, decision final, factores explicables y datos de
persistencia para Supabase.

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
