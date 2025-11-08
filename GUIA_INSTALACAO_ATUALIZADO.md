# 🤖 Sistema de Navegação Autônoma - Guia Atualizado

## ✨ Novas Funcionalidades Implementadas

### 1. **Reconhecimento Melhorado do L515**
- Sistema automático de detecção de dispositivos RealSense
- Fallback inteligente caso dispositivos específicos não sejam encontrados
- Melhor tratamento de erros e logs detalhados

### 2. **Separação de Funções dos Sensores**

#### 🎯 LiDAR L515 (Posicionado Embaixo)
- **Função**: Detectar obstáculos no nível do chão
- **Área de cobertura**: Detecta objetos no chão (pedras, degraus, buracos)
- **Processamento**: Divide o campo de visão em 3 setores (esquerda, centro, direita)
- **Distância segura**: Configurável (padrão 0.5m)

#### 📹 Câmera D435 (Posicionada em Cima)
- **Função**: Verificar altura dos objetos
- **Área de cobertura**: Detecta objetos altos (mesas, cadeiras, portas)
- **Processamento**: Analisa região superior da imagem
- **Altura máxima**: Configurável (padrão 1.5m)

### 3. **Reconstrução 3D do Ambiente**
- Mapeamento 3D em tempo real usando dados do LiDAR
- Visualização interativa (rotação com mouse)
- Nuvem de pontos com cores
- Amostragem inteligente para performance

## 📋 Pré-requisitos

### Hardware Necessário
- ✅ Notebook com USB 3.0+
- ✅ Intel RealSense L515 (LiDAR) - **instalar embaixo do robô**
- ✅ Intel RealSense D435 (Câmera RGB-D) - **instalar em cima do robô**
- ✅ Arduino (comunicação com motores)
- ✅ Robô com 3 motores omnidirecionais

### Software Necessário
- Python 3.8 ou superior
- Drivers Intel RealSense (librealsense)
- Navegador web moderno

## 🚀 Instalação Passo a Passo

### 1. Instalar Intel RealSense SDK

**Windows:**
```bash
# Baixe e instale o Intel RealSense SDK:
# https://github.com/IntelRealSense/librealsense/releases
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main"
sudo apt-get update
sudo apt-get install librealsense2-dkms librealsense2-utils librealsense2-dev
```

### 2. Verificar Dispositivos Conectados

```bash
# Liste os dispositivos RealSense conectados
realsense-viewer
```

Você deve ver:
- Intel RealSense L515
- Intel RealSense D435

### 3. Instalar Dependências Python

No diretório do projeto, execute:

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

As dependências incluem:
- `pyrealsense2` - SDK Python do RealSense
- `opencv-python` - Processamento de imagem
- `numpy` - Cálculos numéricos
- `open3d` - Reconstrução 3D
- `pyserial` - Comunicação com Arduino
- `websockets` - Comunicação com interface web
- `asyncio` - Processamento assíncrono

### 4. Conectar Arduino

1. Carregue o código `arduino_robot_control.ino` no Arduino
2. Conecte o Arduino ao notebook via USB
3. Anote a porta serial (ex: COM3 no Windows, /dev/ttyUSB0 no Linux)

## 🎮 Como Usar

### 1. Iniciar Sistema Python

```bash
python robot_autonomous_control.py
```

Você verá:
```
=== Sistema de Controle Autônomo ===

Inicializando sensores...

=== Dispositivos RealSense Detectados ===
1. Intel RealSense L515 (Serial: XXXXX)
2. Intel RealSense D435 (Serial: YYYYY)
✓ LiDAR identificado: Intel RealSense L515 (Serial: XXXXX)
✓ Câmera identificada: Intel RealSense D435 (Serial: YYYYY)
✓ LiDAR iniciado (posição: embaixo do robô)
✓ Câmera iniciada (posição: em cima do robô)
✓ Servidor WebSocket rodando em ws://localhost:8765
```

### 2. Abrir Interface Web

1. Abra o navegador
2. A interface se conectará automaticamente
3. Conecte ao Arduino usando a interface

### 3. Visualizações Disponíveis

#### 📹 Câmera D435 (Superior)
- Feed de vídeo em tempo real
- Detecta objetos altos
- ~10 FPS, qualidade ajustável

#### 🎯 LiDAR L515 (Inferior)
- Mapa de obstáculos no chão
- 3 setores: Esquerda, Centro, Direita
- Distâncias em metros
- Indicadores coloridos:
  - 🟢 Verde = Caminho livre
  - 🔴 Vermelho = Obstáculo detectado

#### 🌐 Reconstrução 3D
- Mapa 3D do ambiente
- Rotação interativa (arraste com mouse)
- Atualização em tempo real
- Nuvem de pontos colorida

### 4. Modos de Operação

#### Modo Manual
1. Use controles direcionais ou controle por motor
2. Ajuste velocidade dos motores
3. Visualize sensores em tempo real

#### Modo Autônomo
1. Ative o modo autônomo
2. O robô desvias automaticamente de obstáculos
3. Combina dados do LiDAR (chão) e Câmera (altura)
4. Parada de emergência sempre disponível

## ⚙️ Configurações Avançadas

### Ajustar Sensibilidade dos Sensores

Edite `robot_autonomous_control.py`:

```python
# Distância segura para obstáculos (metros)
detector = ObstacleDetector(
    safe_distance=0.5,      # Distância mínima para obstáculos
    height_threshold=1.5    # Altura máxima a verificar
)
```

### Ajustar Qualidade do Vídeo

```python
# Qualidade JPEG (1-100)
cv2.imencode('.jpg', color_image, [cv2.IMWRITE_JPEG_QUALITY, 50])
```

### Ajustar Taxa de Atualização

```python
# Hz da leitura dos sensores
await asyncio.sleep(0.1)  # 10 Hz
```

### Configurar Reconstrução 3D

```python
# Número de pontos na nuvem
if len(points) > 1000:
    indices = np.random.choice(len(points), 1000, replace=False)
```

## 🔧 Resolução de Problemas

### L515 Não Detectado

**Problema**: `✗ Nenhum dispositivo RealSense encontrado!`

**Soluções**:
1. Verifique se o cabo USB está conectado (USB 3.0+)
2. Execute `realsense-viewer` para confirmar que o dispositivo é visível
3. Atualize firmware do L515
4. Reinicie o computador
5. Tente outra porta USB 3.0

### Erro "Failed to set power state"

```bash
# Linux: Adicione regras udev
sudo cp config/99-realsense-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && udevadm trigger
```

### WebSocket Não Conecta

**Verificações**:
1. Script Python está rodando?
2. Porta 8765 está bloqueada? (firewall)
3. Verifique console do navegador (F12)

### Câmera Não Aparece

**Soluções**:
1. Verifique se D435 está conectada
2. Teste com `realsense-viewer`
3. Aguarde inicialização completa (~5 segundos)

### Reconstrução 3D Lenta

**Otimizações**:
1. Reduza amostragem de pontos (linha 60 em sensor_loop)
2. Aumente intervalo de atualização (linha 51)
3. Reduza resolução do LiDAR

## 🎯 Lógica de Navegação Autônoma

### Decisão de Movimento

O sistema combina dados de ambos os sensores:

```python
1. Verifica obstáculos no CHÃO (LiDAR)
2. Verifica obstáculos em ALTURA (Câmera)
3. Combina informações:
   - Se centro livre → Avançar
   - Se direita livre → Virar direita
   - Se esquerda livre → Virar esquerda
   - Se tudo bloqueado → Recuar
```

### Prioridade de Sensores

- **LiDAR**: Detecta obstáculos imediatos (alta prioridade)
- **Câmera**: Detecta objetos suspensos (média prioridade)
- **Combinação**: Garante navegação segura em 3D

## 📊 Protocolo de Comunicação

### Python → Interface (WebSocket)

```json
{
  "type": "sensor_data",
  "timestamp": 1234567890.123,
  "camera": "base64_encoded_image",
  "ground_obstacles": {
    "type": "ground",
    "left": false,
    "center": true,
    "right": false,
    "distances": {
      "left": 1.2,
      "center": 0.3,
      "right": 2.5
    }
  },
  "height_obstacles": {
    "type": "height",
    "left": false,
    "center": false,
    "right": true,
    "distances": {
      "left": 3.0,
      "center": 2.8,
      "right": 0.4
    }
  },
  "point_cloud": {
    "points": [[x, y, z], ...],
    "colors": [[r, g, b], ...]
  }
}
```

### Interface → Python (WebSocket)

```json
// Modo autônomo
{
  "type": "set_autonomous",
  "enabled": true
}

// Movimento manual
{
  "type": "move",
  "m1": 150,
  "m2": -150,
  "m3": 0
}
```

## 🚀 Próximos Passos Sugeridos

1. **SLAM Completo** - Mapeamento e localização simultâneos
2. **Gravação de Trajetos** - Salvar e reproduzir rotas
3. **Reconhecimento de Objetos** - IA para identificar objetos
4. **Planejamento A*** - Rotas otimizadas
5. **Controle por Voz** - Comandos vocais

## 📚 Documentação Adicional

- [README_NAVEGACAO_AUTONOMA.md](README_NAVEGACAO_AUTONOMA.md) - Documentação original
- [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md) - Detalhes técnicos
- [Intel RealSense Docs](https://dev.intelrealsense.com/)
- [Open3D Documentation](http://www.open3d.org/)

## 🆘 Suporte

Problemas? Verifique:
1. Console do navegador (F12)
2. Logs do Python
3. `realsense-viewer` para testar hardware
4. Documentação oficial Intel RealSense
