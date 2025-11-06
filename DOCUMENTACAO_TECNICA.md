# Documentação Técnica - Sistema de Controle Remoto de Robô

## 1. Visão Geral do Sistema

### 1.1 Arquitetura
O sistema é composto por três camadas principais:

```
┌─────────────────────────────────────┐
│   Interface Web (React/TypeScript)  │
│   - Componentes de controle         │
│   - Gerenciamento de estado         │
│   - Interface do usuário            │
└──────────────┬──────────────────────┘
               │ HTTP/WebSocket
               ▼
┌─────────────────────────────────────┐
│   Servidor Backend (Python/Flask)   │
│   - API REST                        │
│   - Gerenciamento de comunicação   │
│   - Lógica de controle              │
└──────────────┬──────────────────────┘
               │ Serial (UART)
               ▼
┌─────────────────────────────────────┐
│   Microcontrolador (Arduino)        │
│   - Controle de motores             │
│   - PWM para velocidade             │
│   - Driver de motores               │
└─────────────────────────────────────┘
```

### 1.2 Tecnologias Utilizadas
- **Frontend**: React 18, TypeScript, TailwindCSS, Vite
- **Backend**: Python 3, Flask, PySerial
- **Hardware**: Arduino (AVR), Comunicação Serial UART (9600 baud)
- **Protocolo**: Comandos de texto separados por vírgula via serial

---

## 2. Frontend - Interface Web

### 2.1 Estrutura de Componentes

#### DirectionalControl.tsx
Componente principal de controle direcional com as seguintes funcionalidades:

**Estado Interno:**
```typescript
const [speed, setSpeed] = useState(180);  // Velocidade: 0-255
const [activeDirection, setActiveDirection] = useState<string | null>(null);
```

**Funções de Movimento:**
Cada função envia três valores de velocidade (M1, M2, M3) para controlar os motores:

```typescript
// Frente: M1=0, M2=-velocidade, M3=+velocidade
moveForward() → onSendCommand(0, -speed, speed)

// Trás: M1=0, M2=+velocidade, M3=-velocidade
moveBackward() → onSendCommand(0, speed, -speed)

// Direita: M1=-velocidade, M2=-velocidade, M3=+velocidade
moveRight() → onSendCommand(-speed, -speed, speed)

// Esquerda: M1=+velocidade, M2=-velocidade, M3=+velocidade
moveLeft() → onSendCommand(speed, -speed, speed)

// Parar: Todos os motores em 0
stop() → onSendCommand(0, 0, 0)
```

**Controle de Velocidade:**
- Range: 0 a 255 (8 bits - compatível com PWM do Arduino)
- Interface dual: Slider e campo numérico
- Valor padrão: 180 (aproximadamente 70% da velocidade máxima)

**Controle por Teclado:**
```typescript
// Mapeamento de teclas
W / ArrowUp    → moveForward()
S / ArrowDown  → moveBackward()
A / ArrowLeft  → moveLeft()
D / ArrowRight → moveRight()
Space          → stop()
```

#### MotorSpeedControl.tsx
Componente auxiliar para controle fino individual dos motores.

### 2.2 Fluxo de Dados no Frontend

```
┌──────────────┐
│ Ação do      │
│ Usuário      │
└──────┬───────┘
       │
       ▼
┌──────────────┐      ┌──────────────┐
│ Evento de    │─────▶│ Função de    │
│ Clique/Tecla │      │ Movimento    │
└──────────────┘      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │ onSendCommand│
                      │ (callback)   │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │ Envio via    │
                      │ HTTP POST    │
                      └──────────────┘
```

---

## 3. Backend - Servidor Python/Flask

### 3.1 Classe RobotController

**Inicialização:**
```python
class RobotController:
    def __init__(self):
        self.serial_connection = None
        self.speed = 80  # Velocidade padrão (0-100%)
        self.is_connected = False
```

### 3.2 Comunicação Serial

**Conexão:**
```python
def connect_serial(self, port):
    # Configuração: 9600 baud, 8N1 (8 bits, sem paridade, 1 stop bit)
    self.serial_connection = serial.Serial(port, 9600, timeout=1)
    time.sleep(2)  # Aguarda reset do Arduino (bootloader)
```

**Protocolo de Comandos:**
```python
def send_command(self, m1, m2, m3):
    # Formato: "M1,M2,M3\n"
    # Exemplo: "180,-180,180\n"
    command = f"{m1},{m2},{m3}\n"
    self.serial_connection.write(command.encode())
```

### 3.3 Conversão de Velocidade

O sistema usa dois sistemas de velocidade:

**Sistema Web (0-100%):**
```python
self.speed = 80  # 80%
```

**Conversão para Arduino (0-255):**
```python
arduino_speed = int(self.speed * 2.55)
# 80 * 2.55 = 204
```

**Razão da conversão:**
- Web: Interface amigável com porcentagem
- Arduino: PWM de 8 bits (0-255)
- Fator: 255/100 = 2.55

### 3.4 API REST Endpoints

**GET /api/ports**
```json
Response: {
  "ports": ["/dev/ttyUSB0", "/dev/ttyACM0", "COM3"]
}
```

**POST /api/connect**
```json
Request: {
  "port": "/dev/ttyUSB0"
}
Response: {
  "success": true,
  "message": "Conectado com sucesso"
}
```

**POST /api/move**
```json
Request: {
  "action": "forward",
  "speed": 80
}
Response: {
  "success": true,
  "message": "Enviado: M1=0, M2=204, M3=-204"
}
```

---

## 4. Firmware Arduino

### 4.1 Protocolo Serial

**Configuração:**
```cpp
Serial.begin(9600);  // 9600 baud
```

**Formato de Recepção:**
```
Entrada: "M1,M2,M3\n"
Exemplo: "180,-180,180\n"

Parsing:
- Lê até encontrar vírgula → M1
- Lê até encontrar vírgula → M2
- Lê até encontrar '\n' → M3
```

**Exemplo de código esperado no Arduino:**
```cpp
void loop() {
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');
    
    // Parse "M1,M2,M3"
    int firstComma = data.indexOf(',');
    int secondComma = data.indexOf(',', firstComma + 1);
    
    int m1 = data.substring(0, firstComma).toInt();
    int m2 = data.substring(firstComma + 1, secondComma).toInt();
    int m3 = data.substring(secondComma + 1).toInt();
    
    // Aplica aos motores
    setMotor(1, m1);
    setMotor(2, m2);
    setMotor(3, m3);
  }
}
```

### 4.2 Controle PWM

**Conversão de Velocidade para PWM:**
```cpp
void setMotor(int motor, int speed) {
  // speed: -255 a +255
  // Direção: sinal (+ ou -)
  // Velocidade: valor absoluto
  
  bool forward = (speed >= 0);
  int pwmValue = abs(speed);  // 0-255
  
  // Configurar pinos de direção
  if (motor == 1) {
    digitalWrite(DIR_PIN_1A, forward ? HIGH : LOW);
    digitalWrite(DIR_PIN_1B, forward ? LOW : HIGH);
    analogWrite(PWM_PIN_1, pwmValue);
  }
  // ... similar para motores 2 e 3
}
```

**Frequência PWM:**
- Arduino Uno: ~490 Hz (Timer 0 e 1) ou ~980 Hz (Timer 2)
- Duty cycle: 0-255 (8 bits de resolução)

---

## 5. Cálculos de Movimento

### 5.1 Sistema de 3 Motores (Holonômico)

Assumindo um robô com 3 rodas omnidirecionais a 120° entre si:

**Frente (0°):**
```
M1 = 0           (motor frontal parado)
M2 = -velocidade (motor traseiro esquerdo para trás)
M3 = +velocidade (motor traseiro direito para frente)
```

**Trás (180°):**
```
M1 = 0
M2 = +velocidade
M3 = -velocidade
```

**Direita (90°):**
```
M1 = -velocidade (motor frontal para trás)
M2 = -velocidade (motor traseiro esquerdo para trás)
M3 = +velocidade (motor traseiro direito para frente)
```

**Esquerda (270°):**
```
M1 = +velocidade (motor frontal para frente)
M2 = -velocidade (motor traseiro esquerdo para trás)
M3 = +velocidade (motor traseiro direito para frente)
```

### 5.2 Matriz de Transformação

Para movimento em qualquer direção (θ) com rotação (ω):

```
M1 = -sin(θ) * v + ω * r
M2 = sin(θ + 120°) * v + ω * r
M3 = sin(θ - 120°) * v + ω * r

Onde:
v = velocidade linear
θ = ângulo de movimento
ω = velocidade angular
r = raio da base do robô
```

---

## 6. Fluxo Completo de Execução

### 6.1 Sequência Temporal

```
T=0ms: Usuário clica em "FRENTE"
  ↓
T=5ms: React chama moveForward()
  ↓
T=10ms: onSendCommand(0, -180, 180) é executado
  ↓
T=15ms: HTTP POST para /api/move
  ↓
T=50ms: Flask recebe requisição
  ↓
T=55ms: RobotController.move_forward() é chamado
  ↓
T=60ms: Conversão: 180 (permanece 180, já em escala 0-255)
  ↓
T=65ms: send_command(0, -180, 180)
  ↓
T=70ms: Serial.write("0,-180,180\n")
  ↓
T=100ms: Arduino recebe via UART (9600 baud ≈ 1ms/byte)
  ↓
T=105ms: Arduino faz parsing dos valores
  ↓
T=110ms: PWM aplicado aos motores
  ↓
T=115ms: Motores começam a girar
```

### 6.2 Latência Total
- Rede (local): ~40-50ms
- Serial (9600 baud): ~10-15ms
- Processing: ~5-10ms
- **Total: ~55-75ms** (tempo de resposta aceitável)

---

## 7. Considerações de Hardware

### 7.1 Driver de Motores
Recomendado: L298N, L293D, ou TB6612FNG

**Conexões Típicas:**
```
Arduino → Driver → Motor

PWM_PIN → EN (Enable)
DIR_PIN_A → IN1
DIR_PIN_B → IN2
GND → GND
5V → VCC (lógica)
12V → VCC (motores)
```

### 7.2 Alimentação
- **Arduino**: 5V via USB ou 7-12V via Vin
- **Motores**: 6-12V (separado do Arduino)
- **Driver**: Alimentação lógica 5V + alimentação motores 12V
- **Importante**: Comum GND entre todos os componentes

### 7.3 Proteção
- Diodos flyback nos motores (proteção contra back-EMF)
- Capacitores de desacoplamento (100nF) próximos aos CIs
- Fusível na alimentação dos motores

---

## 8. Melhorias Futuras

### 8.1 Performance
- [ ] WebSocket para comunicação em tempo real (reduzir latência)
- [ ] Buffer de comandos no Arduino
- [ ] Aceleração/desaceleração suave (rampa de velocidade)

### 8.2 Funcionalidades
- [ ] Feedback de telemetria (sensores, bateria, odometria)
- [ ] Controle PID para movimento preciso
- [ ] Mapeamento e navegação autônoma
- [ ] Câmera com streaming de vídeo

### 8.3 Segurança
- [ ] Timeout automático (parar se perder conexão)
- [ ] Autenticação no backend
- [ ] Criptografia HTTPS/WSS
- [ ] Limite de velocidade configurável

---

## 9. Troubleshooting

### 9.1 Problemas Comuns

**Robô não responde:**
- Verificar conexão serial (porta correta)
- Verificar baud rate (9600)
- Verificar alimentação dos motores
- Testar comunicação serial manual (Serial Monitor)

**Movimento incorreto:**
- Verificar inversão de motores (trocar DIR_A com DIR_B)
- Verificar cálculos de velocidade
- Calibrar velocidade mínima (PWM < 100 pode não mover)

**Latência alta:**
- Usar baud rate maior (115200)
- Implementar WebSocket
- Reduzir processamento no Arduino

**Motores tremem ou fazem ruído:**
- Verificar alimentação adequada
- Adicionar capacitores de desacoplamento
- Verificar frequência PWM (alguns motores preferem 20kHz+)

---

## 10. Referências Técnicas

### 10.1 Documentação
- [Arduino Serial Reference](https://www.arduino.cc/reference/en/language/functions/communication/serial/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
- [React Documentation](https://react.dev/)

### 10.2 Especificações
- **UART**: RS-232/TTL, 8N1, 9600 baud
- **PWM**: 8-bit (0-255), ~490Hz ou ~980Hz
- **HTTP**: REST API, JSON payload
- **Protocolo**: ASCII text, comma-separated values

---

## Apêndice A: Diagrama de Sequência Completo

```
Usuario  Frontend  Backend  Arduino  Motor
  |         |        |        |       |
  |--click--|        |        |       |
  |         |--POST--|        |       |
  |         |        |--cmd---|       |
  |         |        |        |--PWM--|
  |         |        |        |       |--rotate
  |         |        |<--ack--|       |
  |         |<--200--|        |       |
  |<--UI----|        |        |       |
```

## Apêndice B: Tabela de Comandos

| Ação     | M1   | M2   | M3   | Resultado              |
|----------|------|------|------|------------------------|
| Frente   | 0    | -v   | +v   | Move para frente       |
| Trás     | 0    | +v   | -v   | Move para trás         |
| Direita  | -v   | -v   | +v   | Move para direita      |
| Esquerda | +v   | -v   | +v   | Move para esquerda     |
| Parar    | 0    | 0    | 0    | Para todos os motores  |

*v = velocidade (0-255)*

---

**Versão:** 1.0  
**Data:** 2025  
**Autor:** Sistema de Controle de Robô  
**Licença:** MIT
