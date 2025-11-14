# 🎯 Guia de Integração MediaPipe

## Visão Geral
Sistema de detecção de objetos usando MediaPipe EfficientDet integrado com o LiDAR L515 para identificação e medição de distância em tempo real.

## 📋 Requisitos

### Modelo MediaPipe
Baixe o modelo EfficientDet Lite0:
```bash
wget https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite
```

Ou baixe manualmente de: https://developers.google.com/mediapipe/solutions/vision/object_detector

### Dependências Python
```bash
pip install mediapipe
```

Já incluído em `requirements.txt`.

## 🚀 Como Usar

### 1. Teste Standalone
Teste o detector isoladamente:
```bash
python mediapipe_detector.py
```

Pressione **Q** para sair.

### 2. Integração com Sistema Principal
O MediaPipe já está integrado ao `robot_autonomous_control.py`:

```bash
python robot_autonomous_control.py
```

### 3. Visualização na Interface Web
Acesse a interface web e navegue até a seção **"Detecção de Objetos (MediaPipe)"** para ver:
- Feed da câmera L515
- Bounding boxes dos objetos detectados
- Labels e distâncias em tempo real
- Lista detalhada de objetos

## 🎨 Interface Web

### Nova Visualização
A interface possui uma nova seção dedicada mostrando:

- **Feed da Câmera**: Imagem ao vivo do L515
- **Bounding Boxes**: Retângulos verdes ao redor dos objetos
- **Labels**: Nome do objeto + distância + confiança
- **Lista de Objetos**: Detalhes de cada objeto detectado
- **Estatísticas**: Contador de objetos, informações do modelo

### Dados Transmitidos
Via WebSocket, a estrutura `detected_objects` contém:
```json
{
  "label": "person",
  "confidence": 0.95,
  "distance": 1.25,
  "bbox": {
    "x": 100,
    "y": 150,
    "width": 200,
    "height": 300
  }
}
```

## ⚙️ Configurações

### Modelo MediaPipe
- **Modelo**: EfficientDet Lite0
- **Formato**: TensorFlow Lite (.tflite)
- **Máximo de Objetos**: 5 simultâneos
- **Modo**: IMAGE (processamento frame-a-frame)

### Resolução L515
- **Cor**: 640×480 @ 30 FPS (BGR8)
- **Profundidade**: 320×240 @ 30 FPS (Z16)

### Taxa de Atualização
- Detecção: ~10 Hz (limitado pelo loop principal)
- Alinhamento: Depth alinhado ao Color

## 🔧 Personalização

### Alterar Número Máximo de Objetos
Em `mediapipe_detector.py`:
```python
options = mp_object_detector_options(
    base_options=mp_base_options(model_asset_path=model_path),
    max_results=5,  # Altere aqui
    running_mode=mp_vision_running_mode.IMAGE
)
```

### Alterar Threshold de Confiança
Por padrão, MediaPipe usa threshold interno. Para filtrar manualmente:
```python
if confidence >= 0.5:  # Adicione filtro
    detected_objects.append(obj_info)
```

### Desenhar na Imagem (Debug)
```python
output_img = detector.draw_detections(color_img, detections)
cv2.imshow("Debug", output_img)
```

## 📊 Classes Detectadas
EfficientDet Lite0 detecta 90 classes do COCO dataset, incluindo:
- Pessoas (person)
- Veículos (car, truck, bicycle, motorcycle)
- Animais (dog, cat, bird, horse)
- Objetos comuns (chair, bottle, laptop, phone)
- E mais...

## 🐛 Troubleshooting

### "Module not found: mediapipe"
```bash
pip install --upgrade mediapipe
```

### "Model file not found"
Verifique se `efficientdet_lite0.tflite` está no diretório raiz do projeto.

### Baixa Taxa de FPS
- Reduza `max_results` para 2-3 objetos
- Aumente o intervalo do loop: `await asyncio.sleep(0.15)`
- Use modelo mais leve (se disponível)

### Objetos Não Detectados
- Verifique iluminação (MediaPipe precisa de boa iluminação)
- Certifique-se que o objeto está em uma das 90 classes COCO
- Ajuste confiança/threshold

## 🔗 Recursos

- [MediaPipe Object Detection](https://developers.google.com/mediapipe/solutions/vision/object_detector)
- [EfficientDet Paper](https://arxiv.org/abs/1911.09070)
- [COCO Dataset Classes](https://cocodataset.org/#explore)
- [Intel RealSense L515](https://www.intelrealsense.com/lidar-camera-l515/)

## 📝 Notas

- O MediaPipe usa CPU por padrão (sem necessidade de GPU)
- Distância calculada do centro do bounding box
- Sistema funciona mesmo sem o modelo (graceful degradation)
- Detecção independente do modo autônomo/manual
