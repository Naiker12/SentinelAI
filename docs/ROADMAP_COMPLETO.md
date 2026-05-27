# SentinelAI - Roadmap Actualizado

Fecha: 2026-05-27

## Prioridad Inmediata

1. Usar el modelo propio entrenado en Google Colab.
2. Confirmar que `SENTINEL_MODEL` apunte a `D:\SentinelAI\proyecto_violence_v4\entrenamiento_violence-3\weights\best.pt`.
3. Probar camara real con `python -m agente_percepcion.main`.
4. Importar workflow actualizado de n8n.
5. Configurar Telegram supervisor.
6. Validar dashboard `Interfaz Humana`.

## Arquitectura Objetivo

```text
AgentePercepcion
  -> YOLO best.pt
  -> cooldown camara/objeto
  -> AgenteAnalisis/Riesgo/Accion
  -> Supabase
  -> n8n
  -> Telegram supervisor
  -> Dashboard
```

## Pendientes Tecnicos

| Prioridad | Tarea | Resultado esperado |
|---|---|---|
| Alta | Probar `best.pt` de violencia | Detectar `Violence` y `NonViolence` en camara real |
| Alta | Configurar Telegram | Botones de confirmar/falso positivo/mas revision |
| Alta | Guardar feedback humano | Tabla `human_reviews` con trazabilidad |
| Media | Memoria real Supabase | Historial por camara/zona antes del analisis |
| Media | Dashboard realtime | Cola de supervisor y eventos recientes |
| Baja | AgentePrediccion | Baseline estadistico, luego Isolation Forest |

## AgentePrediccion Futuro

Primera fase recomendada:

- Z-score por ventana temporal para detectar actividad inusual.
- Luego Isolation Forest con datos historicos de `detection_events`.
- Despues Random Forest usando etiquetas humanas de `human_reviews`.
