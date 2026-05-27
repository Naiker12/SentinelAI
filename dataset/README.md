# Dataset SentinelAI

Dataset propio para entrenar el modelo `best.pt` de SentinelAI con Roboflow o Google Colab.

Clases activas del modelo entrenado `proyecto_violence_v4`:

- `NonViolence`
- `Violence`

Los escenarios como `normal`, `pelea`, `robo`, `objeto_sospechoso` y `objeto_no_sospechoso` pueden servir para ordenar capturas, pero el modelo actual se consume como detector binario de violencia/no violencia.

Estructura esperada:

```text
dataset/
  raw/
  yolo/images/train
  yolo/images/val
  yolo/images/test
  yolo/labels/train
  yolo/labels/val
  yolo/labels/test
  data.yaml
  classes.txt
```

Entrenamiento base en Colab:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.train(data="dataset/data.yaml", epochs=50, imgsz=640)
```

Modelo activo actual:

```text
D:\SentinelAI\proyecto_violence_v4\entrenamiento_violence-3\weights\best.pt
```
