# Relatório Técnico - Sistema de Navegação Autônoma Tri-Bot Pilot

## 1. Visão Geral do Sistema

O **Tri-Bot Pilot** é um sistema completo de navegação autônoma para robô omnidirecional de 3 rodas, utilizando sensores Intel RealSense e controle via Arduino. O projeto combina visão computacional, processamento de profundidade 3D, comunicação em tempo real e lógica de navegação inteligente.

### 1.1 Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE WEB (React)                     │
│  - Visualização de câmera em tempo real                     │
│  - Controles manuais e autônomos                            │
│  - Status de conexões e sensores                            │
└────────────────────┬────────────────────────────────────────┘
                     │ WebSocket (porta 8765)
                     │ JSON bidirectional
┌────────────────────▼────────────────────────────────────────┐
│            BACKEND PYTHON (Notebook)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ WebSocketServer                                       │  │
│  │ - Recebe comandos da interface                       │  │
│  │ - Envia dados de sensores em tempo real              │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ RealSenseController                                   │  │
│  │ - Gerencia câmera D435 (RGB-D)                       │  │
│  │ - Captura frames de cor e profundidade               │  │
│  │ - Gera nuvens de pontos 3D                           │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ ObstacleDetector                                      │  │
│  │ - Processa dados de profundidade                     │  │
│  │ - Divide ambiente em setores (esq, centro, dir)      │  │
│  │ - Calcula distâncias para obstáculos                 │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ ObjectTracker                                         │  │
│  │ - Detecta e rastreia objetos                         │  │
│  │ - Estabilização temporal                             │  │
│  │ - Filtragem de ruídos                                │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ AutonomousNavigator                                   │  │
│  │ - Toma decisões de movimento                         │  │
│  │ - Implementa estratégia de desvio                    │  │
│  │ - Rotações periódicas para mapeamento                │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │ RobotController                                       │  │
│  │ - Comunicação serial com Arduino                     │  │
│  │ - Traduz comandos em velocidades de motor            │  │
│  │ - Controle de robô omnidirecional                    │  │
│  └──────────────┬───────────────────────────────────────┘  │
└─────────────────┼────────────────────────────────────────┘
                  │ Serial USB
┌─────────────────▼────────────────────────────────────────┐
│                    ARDUINO                                │
│  - Recebe comandos (M1, M2, M3)                          │
│  - Controla drivers de motor                             │
│  - Hardware: 3 motores omnidirecionais                   │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Comunicação WebSocket

### 2.1 Protocolo de Comunicação

O sistema utiliza WebSocket para comunicação bidirecional em tempo real entre frontend (React) e backend (Python).

**Servidor:** `ws://localhost:8765`

### 2.2 Mensagens: Frontend → Backend

#### 2.2.1 Descoberta de Portas Seriais
```json
{
  "type": "discover_ports"
}
```
**Resposta:** Lista de portas seriais disponíveis para conexão com Arduino.

#### 2.2.2 Conexão Serial
```json
{
  "type": "connect_serial",
  "port": "/dev/ttyUSB0"
}
```
**Resposta:** Status de conexão com Arduino.

#### 2.2.3 Comando de Movimento Manual
```json
{
  "type": "move",
  "m1": 150,
  "m2": -150,
  "m3": 150
}
```
Controle direto dos 3 motores (valores: -255 a +255).

#### 2.2.4 Ativar/Desativar Modo Autônomo
```json
{
  "type": "set_autonomous",
  "enabled": true,
  "speed": 100
}
```

#### 2.2.5 Ajustar Velocidade Autônoma
```json
{
  "type": "set_autonomous_speed",
  "speed": 120
}
```

### 2.3 Mensagens: Backend → Frontend

#### 2.3.1 Dados de Sensores (10 Hz)
```json
{
  "type": "sensor_data",
  "camera": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "height_obstacles": {
    "left": false,
    "center": true,
    "right": false,
    "distances": {
      "left": 2.5,
      "center": 0.6,
      "right": 3.0
    }
  },
  "tracked_objects": [
    {
      "id": 1,
      "bbox": [x, y, w, h],
      "centroid": [cx, cy],
      "depth": 1.2
    }
  ],
  "navigation_status": {
    "mode": "camera",
    "state": "moving",
    "direction": "forward",
    "speed": 100,
    "distances": {
      "left": 2.5,
      "center": 0.6,
      "right": 3.0
    },
    "free_moves": 5
  }
}
```

#### 2.3.2 Lista de Portas Seriais
```json
{
  "type": "ports_list",
  "ports": ["/dev/ttyUSB0", "/dev/ttyACM0"]
}
```

#### 2.3.3 Status de Conexão Serial
```json
{
  "type": "serial_status",
  "connected": true,
  "port": "/dev/ttyUSB0"
}
```

---

## 3. Processamento da Câmera Intel RealSense D435

### 3.1 Especificações do Sensor

- **Modelo:** Intel RealSense D435
- **Tipo:** Câmera RGB-D (cor + profundidade)
- **Resolução Cor:** 640x480 @ 30 FPS
- **Resolução Profundidade:** 640x480 @ 30 FPS
- **Alcance:** 0.3m a 3.0m (configurável)
- **Tecnologia:** Visão estéreo ativa

### 3.2 Inicialização do Pipeline

```python
def start(self):
    config_camera = rs.config()
    config_camera.enable_device(self.camera_serial)
    config_camera.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config_camera.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    
    self.pipeline_camera = rs.pipeline()
    self.pipeline_camera.start(config_camera)
    self.camera_started = True
```

**Características:**
- **Stream duplo:** Cor (BGR8) + Profundidade (Z16)
- **Sincronização:** Frames alinhados temporalmente
- **Taxa:** 30 FPS configurados, 10 Hz efetivo no loop

### 3.3 Captura de Frames

```python
def get_camera_data(self):
    frames = self.pipeline_camera.wait_for_frames(timeout_ms=5000)
    color_frame = frames.get_color_frame()
    depth_frame = frames.get_depth_frame()
    
    color_image = np.asanyarray(color_frame.get_data())
    depth_image = np.asanyarray(depth_frame.get_data())
    
    return color_image, depth_image
```

**Dados obtidos:**
- `color_image`: Array NumPy (480, 640, 3) em BGR8
- `depth_image`: Array NumPy (480, 640) em uint16, valores em milímetros

### 3.4 Codificação para WebSocket

```python
_, buffer = cv2.imencode('.jpg', color_image, [cv2.IMWRITE_JPEG_QUALITY, 70])
camera_b64 = base64.b64encode(buffer).decode('utf-8')
camera_data = f"data:image/jpeg;base64,{camera_b64}"
```

**Otimizações:**
- **Formato:** JPEG com qualidade 70%
- **Compressão:** ~20-30 KB por frame
- **Codificação:** Base64 para transmissão JSON
- **Taxa efetiva:** ~10 Hz

---

## 4. Detecção de Obstáculos: Cálculos e Algoritmos

### 4.1 Divisão do Campo de Visão

O ambiente é dividido em **3 setores horizontais**:

```
┌─────────────────────────────────┐
│         CAMPO DE VISÃO          │
│  ┌────────┬────────┬────────┐  │
│  │ SETOR  │ SETOR  │ SETOR  │  │
│  │ LEFT   │ CENTER │ RIGHT  │  │
│  │  33%   │  34%   │  33%   │  │
│  └────────┴────────┴────────┘  │
└─────────────────────────────────┘
```

### 4.2 Região de Interesse (ROI)

```python
def analyze_height(self, depth_image):
    height, width = depth_image.shape
    
    # ROI: 30% central vertical (evita chão e teto)
    roi_top = int(height * 0.3)
    roi_bottom = int(height * 0.7)
    roi = depth_image[roi_top:roi_bottom, :]
```

**Justificativa:**
- **30-70% vertical:** Ignora chão (inferior) e teto/ruído superior
- **100% horizontal:** Usa toda largura para máxima detecção lateral

### 4.3 Conversão de Profundidade

```python
depth_meters = depth_image.astype(float) / 1000.0  # Milímetros → Metros
```

**Validação de dados:**
```python
valid_mask = (depth_meters > 0.1) & (depth_meters < 3.0)
depth_meters[~valid_mask] = np.nan
```

**Filtros aplicados:**
- **Mínimo:** 0.1m (elimina ruído próximo)
- **Máximo:** 3.0m (limite de confiabilidade do sensor)
- **Inválidos:** Convertidos para NaN

### 4.4 Cálculo de Distâncias por Setor

```python
def analyze_height(self, depth_image):
    sector_width = width // 3
    sectors = {
        'left': roi[:, 0:sector_width],
        'center': roi[:, sector_width:2*sector_width],
        'right': roi[:, 2*sector_width:]
    }
    
    obstacles = {'left': False, 'center': False, 'right': False}
    distances = {'left': 10.0, 'center': 10.0, 'right': 10.0}
    
    for sector_name, sector_data in sectors.items():
        valid_depths = sector_data[~np.isnan(sector_data)]
        
        if len(valid_depths) > 0:
            min_distance = np.min(valid_depths)
            distances[sector_name] = float(min_distance)
            
            if min_distance < self.safe_distance:
                obstacles[sector_name] = True
```

**Lógica:**
1. **Divisão:** Imagem dividida em 3 partes iguais
2. **Medição:** Distância mínima válida em cada setor
3. **Comparação:** Se `min_distance < safe_distance` → Obstáculo detectado
4. **Default:** 10.0m se nenhum ponto válido (caminho livre)

### 4.5 Parâmetros de Segurança

```python
self.safe_distance = 0.8  # metros
```

**Distâncias críticas na navegação:**
- **Centro < 0.8m:** Obstáculo frontal - desvio obrigatório
- **Laterais < 0.6m:** Obstáculo lateral - evitar direção
- **Rotação:** Distância mínima mantida durante giro

---

## 5. Rastreamento de Objetos (ObjectTracker)

### 5.1 Pipeline de Detecção

```python
def detect_objects(self, depth_image):
    depth_meters = depth_image.astype(float) / 1000.0
    
    # 1. Máscara de distância
    mask = ((depth_meters > 0.3) & (depth_meters < 3.0)).astype(np.uint8) * 255
    
    # 2. Filtro bilateral (preserva bordas)
    filtered = cv2.bilateralFilter(mask, 9, 75, 75)
    
    # 3. Operações morfológicas
    kernel = np.ones((7,7), np.uint8)
    morph = cv2.morphologyEx(filtered, cv2.MORPH_CLOSE, kernel)
    morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
    
    # 4. Detecção de contornos
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

### 5.2 Validação de Objetos

**Filtros rigorosos aplicados:**

```python
area = cv2.contourArea(cnt)
if area < 4000:  # Área mínima
    continue

x, y, w, h = cv2.boundingRect(cnt)
roi_depth = depth_meters[y:y+h, x:x+w]
valid_points = roi_depth[~np.isnan(roi_depth)]

if len(valid_points) < 100:  # Mínimo de pontos válidos
    continue

mean_depth = np.mean(valid_points)
if mean_depth < 0.3 or mean_depth > 3.0:  # Fora do alcance
    continue

depth_std = np.std(valid_points)
if depth_std > 0.3:  # Muito variável = ruído
    continue

filled_ratio = len(valid_points) / (w * h)
if filled_ratio < 0.3:  # Objeto deve preencher 30% da bbox
    continue
```

**Resumo de critérios:**
- Área mínima: 4000 pixels
- Distância: 0.3m a 3.0m
- Pontos válidos: mínimo 100
- Desvio padrão: < 0.3m
- Preenchimento: ≥ 30% da bounding box

### 5.3 Estabilização Temporal

```python
self.stability_counter = {}  # Contador por ID

# Objeto precisa aparecer em 3 frames para ser válido
if self.stability_counter[obj_id] < 3:
    self.stability_counter[obj_id] += 1
    continue  # Não exibe ainda
```

### 5.4 Suavização Exponencial

```python
alpha = 0.7  # Fator de suavização

# Atualiza posição, tamanho e profundidade
existing['bbox'] = [
    int(alpha * new_x + (1-alpha) * old_x),
    int(alpha * new_y + (1-alpha) * old_y),
    int(alpha * new_w + (1-alpha) * old_w),
    int(alpha * new_h + (1-alpha) * old_h)
]

existing['centroid'] = [
    int(alpha * new_cx + (1-alpha) * old_cx),
    int(alpha * new_cy + (1-alpha) * old_cy)
]

existing['depth'] = alpha * new_depth + (1-alpha) * old_depth
```

**Benefícios:**
- Reduz jitter (tremor) nas bounding boxes
- Transições suaves de posição
- Profundidade estável

---

## 6. Lógica de Navegação Autônoma

### 6.1 Máquina de Estados

```
┌──────────┐  Obstáculo detectado   ┌──────────┐
│  MOVING  │ ────────────────────→  │ DESVIO   │
│ (frente) │                         │ (esq/dir)│
└────┬─────┘                         └────┬─────┘
     │                                    │
     │ 8 movimentos livres                │ Caminho livre
     │                                    │
     ▼                                    ▼
┌──────────┐  Rotação completa (6 steps) │
│ ROTATING │ ←────────────────────────────┘
│ (45° CW) │
└──────────┘
```

### 6.2 Combinação de Sensores

```python
def decide_movement(self, ground_obstacles, height_obstacles):
    distances = {'left': 10.0, 'center': 10.0, 'right': 10.0}
    
    # Combina distâncias (usa o menor valor de ambos sensores)
    if ground_obstacles:
        distances['left'] = min(distances['left'], ground_obstacles['distances']['left'])
        distances['center'] = min(distances['center'], ground_obstacles['distances']['center'])
        distances['right'] = min(distances['right'], ground_obstacles['distances']['right'])
    
    if height_obstacles:
        distances['left'] = min(distances['left'], height_obstacles['distances']['left'])
        distances['center'] = min(distances['center'], height_obstacles['distances']['center'])
        distances['right'] = min(distances['right'], height_obstacles['distances']['right'])
```

**Estratégia:** Princípio da segurança - usa sempre a distância mais conservadora.

### 6.3 Algoritmo de Desvio

```python
# Detecção de obstáculos
obstacle_detected = (
    distances['center'] < 0.8 or 
    distances['left'] < 0.6 or 
    distances['right'] < 0.6
)

if obstacle_detected:
    self.free_path_counter = 0  # Reseta contador
    
    if distances['center'] < 0.8:
        # Obstáculo frontal - escolhe melhor lado
        if distances['right'] > distances['left'] and distances['right'] > 0.8:
            return 'right', speed * 0.7
        elif distances['left'] > distances['right'] and distances['left'] > 0.8:
            return 'left', speed * 0.7
        else:
            return 'stop', 0  # Ambos bloqueados
    
    elif distances['left'] < 0.6:
        return 'right', speed * 0.7  # Desviar para direita
    
    elif distances['right'] < 0.6:
        return 'left', speed * 0.7  # Desviar para esquerda

else:
    # Caminho livre - continuar em frente
    self.free_path_counter += 1
    return 'forward', speed
```

### 6.4 Rotações Periódicas de Mapeamento

```python
# Após 8 movimentos sem obstáculos, mapear novo setor
if self.free_path_counter >= self.max_moves_before_rotation:
    self.current_state = 'rotating'
    self.rotation_counter = 0
    return 'stop', 0  # Para antes de iniciar rotação

# Estado de rotação
if self.current_state == 'rotating':
    self.rotation_counter += 1
    
    if self.rotation_counter <= self.rotation_steps:
        return 'rotate_right', speed * 0.6  # 45° horário
    else:
        # Rotação completa
        self.current_state = 'moving'
        self.free_path_counter = 0
        return 'stop', 0
```

**Parâmetros:**
- `max_moves_before_rotation`: 8 movimentos livres
- `rotation_steps`: 6 passos para ~45° (ajustável empiricamente)
- Velocidade de rotação: 60% da velocidade base

**Objetivo:** Evitar colisões com objetos fora do campo de visão frontal.

---

## 7. Controle de Motores (Robô Omnidirecional)

### 7.1 Configuração de 3 Rodas

```
        FRENTE
          ▲
          │
    M2 ●──┼──● M3
       ╲  │  ╱
        ╲ │ ╱
         ╲│╱
          ●
         M1
```

**Layout:**
- **M1:** Motor traseiro (120° em relação à frente)
- **M2:** Motor frontal-esquerdo (240° em relação à frente)
- **M3:** Motor frontal-direito (0° em relação à frente)

### 7.2 Cinemática de Movimentos

#### Movimento Frontal
```python
'forward': (0, -speed, speed)
# M1 = 0: Motor traseiro parado
# M2 = -speed: Gira para trás
# M3 = speed: Gira para frente
```

#### Movimento Traseiro
```python
'backward': (0, speed, -speed)
# Inversão dos motores frontais
```

#### Movimento Lateral Esquerdo
```python
'left': (speed, -speed, speed)
# M1 contribui positivamente
# Vetores resultam em deslocamento lateral
```

#### Movimento Lateral Direito
```python
'right': (-speed, -speed, speed)
# Configuração ajustada para direita
```

#### Rotação Horária (in-place)
```python
'rotate_right': (speed, speed, speed)
# Todos motores mesma direção angular
# Robô gira sobre próprio eixo
```

#### Rotação Anti-Horária (in-place)
```python
'rotate_left': (-speed, -speed, -speed)
# Direção oposta à rotação horária
```

### 7.3 Comunicação Serial com Arduino

```python
def send_command(self, m1, m2, m3):
    command = f"{m1},{m2},{m3}\n"
    self.serial_port.write(command.encode())
```

**Protocolo:**
- **Formato:** `"M1,M2,M3\n"` (valores inteiros, separados por vírgula, terminado em newline)
- **Baudrate:** 9600
- **Timeout:** 1 segundo
- **Faixa:** -255 a +255 por motor

**Exemplo:** `"150,-100,200\n"`

---

## 8. Loop Principal do Sistema

### 8.1 Fluxo de Execução

```python
async def sensor_loop(self):
    while self.running:
        # 1. Captura de dados
        color_image, depth_image = self.sensors.get_camera_data()
        
        # 2. Processamento de obstáculos
        height_obstacles = self.detector.analyze_height(depth_image)
        
        # 3. Rastreamento de objetos
        self.tracker.update(depth_image)
        tracked_objects = self.tracker.get_tracked_objects()
        
        # 4. Navegação autônoma
        if self.autonomous_mode:
            direction, speed, nav_status = self.navigator.decide_movement(
                None, height_obstacles
            )
            self.robot.move(direction, speed)
        
        # 5. Codificação e transmissão
        _, buffer = cv2.imencode('.jpg', color_image, [cv2.IMWRITE_JPEG_QUALITY, 70])
        camera_b64 = base64.b64encode(buffer).decode('utf-8')
        
        await self.send_to_all({
            'type': 'sensor_data',
            'camera': f"data:image/jpeg;base64,{camera_b64}",
            'height_obstacles': height_obstacles,
            'tracked_objects': tracked_objects,
            'navigation_status': nav_status
        })
        
        await asyncio.sleep(0.1)  # 10 Hz
```

### 8.2 Taxa de Atualização

| Componente | Frequência | Tempo (ms) |
|------------|-----------|------------|
| Captura D435 | 30 FPS | ~33 |
| Processamento obstáculos | 10 Hz | ~20 |
| Rastreamento objetos | 10 Hz | ~30 |
| Navegação autônoma | 10 Hz | ~5 |
| Codificação JPEG | 10 Hz | ~10 |
| Transmissão WebSocket | 10 Hz | ~2 |
| **Loop total** | **10 Hz** | **~100** |

---

## 9. Interface Web (React/TypeScript)

### 9.1 Componentes Principais

#### 9.1.1 `Index.tsx` (Página Principal)
- Gerencia conexão WebSocket
- Recebe e distribui dados de sensores
- Coordena todos os sub-componentes

#### 9.1.2 `AutonomousControl.tsx`
- Switch de modo autônomo
- Slider de velocidade (0-255)
- Botão de parada de emergência
- Exibição de status de navegação

#### 9.1.3 `SensorVisualization.tsx`
- Renderiza feed de câmera em base64
- Overlay de bounding boxes de objetos rastreados
- Indicadores de obstáculos por setor (esq/centro/dir)
- Badges de status (vermelho/verde)

#### 9.1.4 `DirectionalControl.tsx`
- Controles direcionais (↑↓←→)
- Suporte a teclado (WASD, setas)
- Slider de velocidade

#### 9.1.5 `MotorSpeedControl.tsx`
- Controle independente por motor (-255 a +255)
- Sliders individuais para M1, M2, M3
- Input manual de valores

#### 9.1.6 `SerialConnectionControl.tsx`
- Descoberta de portas seriais
- Seleção e conexão com Arduino
- Adiciona automaticamente prefixo `/dev/`

### 9.2 Estado Global (React Hooks)

```typescript
const [isConnected, setIsConnected] = useState(false);          // WebSocket
const [isArduinoConnected, setIsArduinoConnected] = useState(false);
const [autonomousMode, setAutonomousMode] = useState(false);
const [autonomousSpeed, setAutonomousSpeed] = useState(100);
const [cameraImage, setCameraImage] = useState<string>();
const [heightObstacles, setHeightObstacles] = useState<any>();
const [trackedObjects, setTrackedObjects] = useState<any>();
const [navigationStatus, setNavigationStatus] = useState<any>();
const [availablePorts, setAvailablePorts] = useState<string[]>([]);
```

### 9.3 Visualização de Objetos Rastreados

```tsx
{trackedObjects?.map((obj: any) => (
  <g key={obj.id}>
    {/* Bounding Box */}
    <rect
      x={obj.bbox[0]} y={obj.bbox[1]}
      width={obj.bbox[2]} height={obj.bbox[3]}
      fill="none" stroke="lime" strokeWidth="2"
    />
    
    {/* Centroide */}
    <circle
      cx={obj.centroid[0]} cy={obj.centroid[1]}
      r="4" fill="yellow"
    />
    
    {/* Label com profundidade */}
    <text x={obj.bbox[0]} y={obj.bbox[1]-5} fill="lime" fontSize="12">
      ID: {obj.id} | {obj.depth.toFixed(2)}m
    </text>
  </g>
))}
```

---

## 10. Segurança e Failsafes

### 10.1 Parada de Emergência

**Frontend:**
```typescript
const handleEmergencyStop = () => {
  handleSendCommand(0, 0, 0);  // Para todos motores
  setAutonomousMode(false);    // Desativa autônomo
  wsRef.current.send(JSON.stringify({
    type: 'set_autonomous',
    enabled: false
  }));
};
```

**Backend:**
```python
if cmd_type == 'emergency_stop':
    self.autonomous_mode = False
    self.robot.move('stop', 0)
```

### 10.2 Reconexão Automática

```typescript
ws.onclose = () => {
  setIsConnected(false);
  setTimeout(connectWebSocket, 3000);  // Reconecta em 3s
};
```

### 10.3 Validação de Distâncias

```python
# Todas as distâncias validadas antes de uso
if distances['center'] < 0.8:
    # Parar ou desviar
elif all(d < 0.6 for d in distances.values()):
    # Completamente bloqueado - parar
    return 'stop', 0
```

---

## 11. Requisitos de Hardware e Software

### 11.1 Hardware

| Componente | Especificação |
|------------|---------------|
| Câmera | Intel RealSense D435 |
| Microcontrolador | Arduino (Uno/Mega/Nano) |
| Robô | Omnidirecional 3 rodas |
| Notebook | CPU multi-core, USB 3.0 |
| Conexões | USB 3.0 (câmera), USB 2.0 (Arduino) |

### 11.2 Software

**Backend (Python 3.8+):**
- pyrealsense2
- numpy
- opencv-python
- websockets
- pyserial
- scipy
- open3d

**Frontend (Node.js 16+):**
- React 18
- TypeScript
- Vite
- WebSocket API nativa
- Shadcn/ui (componentes)

---

## 12. Desempenho e Otimizações

### 12.1 Otimizações Implementadas

1. **Compressão JPEG:** Qualidade 70% reduz tráfego de rede
2. **ROI reduzida:** Processa apenas 40% da imagem (linhas 30-70%)
3. **Downsampling:** Point cloud usa 1 ponto a cada 4 pixels
4. **Filtros morfológicos:** Reduz ruído antes de processamento pesado
5. **Estabilização temporal:** Evita reprocessamento de objetos instáveis
6. **Loop assíncrono:** WebSocket não bloqueia processamento

### 12.2 Métricas de Performance

| Métrica | Valor |
|---------|-------|
| Latência WebSocket | ~10-20 ms |
| FPS de câmera | 30 FPS |
| Taxa de controle | 10 Hz |
| Tamanho de frame | 20-30 KB |
| CPU (Python) | ~40-60% (1 core) |
| CPU (Frontend) | ~5-10% |

---

## 13. Limitações e Trabalhos Futuros

### 13.1 Limitações Atuais

1. **Sensor único:** Sistema projetado para 2 sensores, mas opera apenas com D435
2. **Sem SLAM:** Não há mapeamento persistente do ambiente
3. **Rotação empírica:** Ângulo de 45° estimado, não medido
4. **Profundidade limitada:** 3m de alcance máximo
5. **Ambiente controlado:** Não testado em ambientes externos ou com luz solar direta

### 13.2 Melhorias Propostas

1. **Integração LiDAR L515:** Adicionar detecção de obstáculos no chão
2. **SLAM completo:** Implementar Cartographer ou ORB-SLAM3
3. **IMU:** Adicionar giroscópio para medição precisa de rotação
4. **Path planning:** A* ou RRT* para rotas otimizadas
5. **Aprendizado:** Rede neural para detecção de objetos
6. **Múltiplos clientes:** Broadcast de dados para várias interfaces
7. **Gravação de rotas:** Record/playback de trajetórias

---

## 14. Conclusão

O **Tri-Bot Pilot** é um sistema completo de navegação autônoma que integra:
- Visão computacional 3D com Intel RealSense D435
- Processamento em tempo real de profundidade
- Lógica de navegação inteligente com rotações periódicas
- Comunicação bidirecional via WebSocket
- Interface web responsiva com controles manuais e autônomos
- Controle preciso de robô omnidirecional

O sistema demonstra capacidade de navegar autonomamente em ambientes internos, desviando de obstáculos detectados por análise de profundidade da câmera RGB-D, com fallback para controle manual completo.

**Documentos relacionados:**
- `README_NAVEGACAO_AUTONOMA.md`: Guia de uso
- `DOCUMENTACAO_TECNICA.md`: Especificações de API
- `GUIA_INSTALACAO_ATUALIZADO.md`: Setup e instalação

---

**Versão:** 1.0  
**Data:** 2025-01-12  
**Autor:** Sistema Tri-Bot Pilot  
**Licença:** Uso acadêmico/pesquisa
