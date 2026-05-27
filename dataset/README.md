# Dataset SentinelAI

Dataset propio para entrenar el modelo `best.pt` de SentinelAI con Roboflow o Google Colab.

Clases activas del modelo nuevo `yolo_percepcion`:

- `arma`
- `arma_blanca`
- `fusil`
- `multitud`
- `no_violencia`
- `persona`
- `persona_sospechosa`
- `undefined`
- `violencia`

El modelo ya no se consume como detector binario. Las reglas de riesgo usan estas clases para distinguir armas, armas blancas, fusil, multitud, persona sospechosa, violencia y no violencia.

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
D:\SentinelAI\yolo_percepcion\entrenamiento_seguridad\weights\best.pt
```
