# Dataset SentinelAI

Este directorio organiza el dataset propio del proyecto. La idea es recolectar imagenes reales con la webcam, etiquetarlas con bounding boxes y entrenar un modelo YOLO personalizado.

## Concepto importante

No todo debe ser una clase YOLO.

- `person`, `knife`, `gun`, `backpack`, `cell_phone`: clases de deteccion de objetos.
- `normal`, `pelea`, `robo`: escenarios de captura para analisis posterior.
- `objeto_sospechoso`, `objeto_no_sospechoso`: carpetas de recoleccion para ordenar imagenes antes de etiquetar.

Para la version 1 del modelo, usa clases fisicas y claras:

```text
person
knife
gun
backpack
cell_phone
```

Despues, `AgenteAnalisis` y `AgenteRiesgo` combinan objetos, hora, ubicacion e historial para inferir si algo es sospechoso.

## Estructura

```text
dataset/
  raw/
    normal/
    objeto_sospechoso/
    objeto_no_sospechoso/
    pelea/
    robo/
  yolo/
    images/
      train/
      val/
      test/
    labels/
      train/
      val/
      test/
  exports/
  classes.txt
  data.yaml
```

## Captura con webcam

Ejemplo:

```powershell
python tools/capture_dataset.py --scenario objeto_sospechoso --label knife
```

Controles:

- `s`: guardar frame actual.
- `a`: activar/desactivar captura automatica.
- `q`: salir.

Ejemplos utiles:

```powershell
python tools/capture_dataset.py --scenario normal --label person
python tools/capture_dataset.py --scenario objeto_sospechoso --label gun
python tools/capture_dataset.py --scenario objeto_no_sospechoso --label backpack
python tools/capture_dataset.py --scenario pelea --label person
python tools/capture_dataset.py --scenario robo --label person
```

## Etiquetado

Instala LabelImg:

```powershell
pip install labelImg
labelImg
```

Configura formato `YOLO` y guarda etiquetas en:

```text
dataset/yolo/labels/train
dataset/yolo/labels/val
dataset/yolo/labels/test
```

Las imagenes correspondientes van en:

```text
dataset/yolo/images/train
dataset/yolo/images/val
dataset/yolo/images/test
```

Cada imagen debe tener un `.txt` con el mismo nombre.

## Meta inicial

Empieza con 200 a 500 imagenes bien hechas:

- Varias distancias.
- Varios angulos.
- Buena y mala iluminacion.
- Fondos reales.
- Objetos parcialmente tapados.
- Algo de movimiento y blur.

Es mejor tener pocas imagenes reales y balanceadas que muchas imagenes repetidas.
