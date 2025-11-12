# Relatório Técnico Resumido - Tri-Bot Pilot

## 1. Visão Geral

Sistema de navegação autônoma para robô omnidirecional de 3 rodas utilizando câmera Intel RealSense D435 e Arduino.

### Arquitetura
```
Interface Web (React) ←→ Backend Python ←→ Arduino
       ↓                      ↓
  WebSocket 8765        RealSense D435
```

---

## 2. Comunicação

### WebSocket (porta 8765)

**Frontend → Backend:**
- `discover_ports`: Lista portas seriais
- `connect_serial`: Conecta Arduino
- `move`: Controle manual (M1, M2, M3)
- `set_autonomous`: Ativa/desativa autônomo
- `set_autonomous_speed`: Ajusta velocidade

**Backend → Frontend:**
- `sensor_data`: Câmera + obstáculos (10 Hz)
- `ports_list`: Portas disponíveis
- `serial_status`: Status Arduino

---

## 3. Câmera Intel RealSense D435

### Especificações
- RGB-D (cor + profundidade)
- 640x480 @ 30 FPS
- Alcance: 0.3m a 3.0m
- Tecnologia: Visão estéreo ativa

### Processamento
1. **Captura:** Frames RGB + Depth sincronizados
2. **Conversão:** Depth em milímetros → metros
3. **ROI:** Processa apenas 30-70% vertical
4. **Divisão:** 3 setores (esquerda, centro, direita)
5. **Transmissão:** JPEG base64 via WebSocket

---

## 4. Detecção de Obstáculos

### Método
```python
# Divide campo de visão em 3 setores
# Para cada setor:
min_distance = np.min(valid_depths)
if min_distance < 0.8m:
    obstacle_detected = True
```

### Parâmetros
- **Distância segura:** 0.8m (frontal)
- **ROI vertical:** 30-70% (ignora chão/teto)
- **Filtros:** 0.1m < depth < 3.0m

---

## 5. Rastreamento de Objetos

### Pipeline
1. Máscara de distância (0.3-3.0m)
2. Filtro bilateral (preserva bordas)
3. Operações morfológicas (remove ruído)
4. Detecção de contornos

### Validação
- Área mínima: 4000 pixels
- Pontos válidos: ≥100
- Preenchimento: ≥30% da bbox
- Desvio padrão: <0.3m

### Estabilização
- 3 frames consecutivos para validar
- Suavização exponencial (α=0.7)

---

## 6. Navegação Autônoma

### Lógica de Decisão
```
1. Analisa 3 setores (esq, centro, dir)
2. Se centro livre: avança
3. Se centro bloqueado:
   - Esquerda livre? → vira esquerda
   - Direita livre? → vira direita
   - Ambos bloqueados? → ré
4. A cada 8 movimentos livres: rotação 45° (mapeamento)
```

### Rotação Periódica
- **Quando:** Após 8 movimentos sem obstáculos
- **Ângulo:** 45° horário
- **Duração:** 0.8s
- **Tipo:** In-place (eixo próprio)

---

## 7. Controle de Motores

### Configuração 3 Rodas
```
        M1 (topo)
           |
    M2 ----+---- M3
    (esq)        (dir)
```

### Comandos
| Direção | M1 | M2 | M3 |
|---------|----|----|-----|
| Frente | 0 | -V | +V |
| Trás | 0 | +V | -V |
| Esquerda | +V | -V | +V |
| Direita | -V | -V | +V |
| Rotação 45° | -V | -V | -V |

### Arduino
- **Porta:** /dev/ttyUSB0
- **Protocolo:** Serial USB
- **Comando:** `Mxx:yyy` (motor:velocidade)

---

## 8. Interface Web

### Componentes Principais
- **SerialConnectionControl:** Conexão Arduino
- **AutonomousControl:** Modo autônomo + velocidade
- **SensorVisualization:** Câmera em tempo real
- **DirectionalControl:** Controle manual (WASD)

### Tecnologias
- React 18 + TypeScript
- Vite (bundler)
- WebSocket API nativa
- Shadcn/ui (componentes)

---

## 9. Armazenamento de Dados

### Tipo: Volátil (RAM)
- **Frames:** ~1.5 MB (descartados após processamento)
- **Objetos rastreados:** ~1-10 KB (temporário)
- **Estado navegação:** ~1 KB (durante execução)
- **Buffer WebSocket:** ~20-50 KB (até transmissão)

### Justificativa
- Sistema em tempo real (<100ms decisão)
- Dados efêmeros (ambiente dinâmico)
- Volume alto (45 MB/s contínuo)
- Zero latência de I/O

### Não Armazenado
❌ Histórico de trajetórias  
❌ Mapas do ambiente  
❌ Gravações de vídeo  
❌ Logs persistentes  

---

## 10. Loop Principal

```python
while True:
    # 1. Captura dados da câmera
    color_image, depth_image = get_camera_data()
    
    # 2. Detecta obstáculos
    obstacles = analyze_obstacles(depth_image)
    
    # 3. Rastreia objetos
    tracked_objects = detect_objects(depth_image)
    
    # 4. Decide movimento (se autônomo)
    if autonomous_enabled:
        command = decide_movement(obstacles)
        send_to_arduino(command)
    
    # 5. Transmite para interface
    send_via_websocket(color_image, obstacles, tracked_objects)
    
    # Taxa: 10 Hz
    sleep(0.1)
```

---

## 11. Requisitos

### Hardware
- Intel RealSense D435
- Arduino (Uno/Mega/Nano)
- Robô omnidirecional 3 rodas
- Notebook (USB 3.0)

### Software Backend
- Python 3.8+
- pyrealsense2, numpy, opencv-python
- websockets, pyserial

### Software Frontend
- Node.js 16+
- React 18, TypeScript, Vite

---

## 12. Desempenho

| Métrica | Valor |
|---------|-------|
| Latência WebSocket | ~10-20 ms |
| FPS câmera | 30 FPS |
| Taxa de controle | 10 Hz |
| Frame size | 20-30 KB |
| CPU (Python) | ~40-60% |

---

## 13. Limitações

1. Opera apenas com câmera D435 (LiDAR L515 não integrado)
2. Sem mapeamento persistente (SLAM)
3. Rotação 45° empírica (não medida por IMU)
4. Alcance limitado a 3m
5. Ambiente interno controlado

---

## 14. Melhorias Futuras

1. **Integração LiDAR:** Detecção de obstáculos no chão
2. **SLAM completo:** Cartographer ou ORB-SLAM3
3. **IMU:** Rotação precisa medida
4. **Path planning:** A* ou RRT*
5. **Logging persistente:** Histórico estruturado
6. **Gravação de sessões:** Replay de trajetórias

---

**Versão:** 1.0 Resumida  
**Data:** 2025-01-12  
**Sistema:** Tri-Bot Pilot Navegação Autônoma
