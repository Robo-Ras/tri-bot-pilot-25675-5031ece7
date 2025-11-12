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

### Visualização do Processamento

```
┌─────────────────────────────────────────────────────┐
│         INTEL REALSENSE D435 - PIPELINE             │
└─────────────────────────────────────────────────────┘

📸 CAPTURA (30 FPS)
├─ Stream RGB:   640x480 BGR8
└─ Stream Depth: 640x480 Z16 (milímetros)

         ↓

🔍 PROCESSAMENTO
├─ Conversão: mm → metros
├─ Filtros: 0.1m < depth < 3.0m
├─ ROI: Linhas 30-70% (ignora chão/teto)
└─ Divisão: 3 setores (Left, Center, Right)

         ↓

📊 ANÁLISE
┌─────────┬──────────┬─────────┐
│  LEFT   │  CENTER  │  RIGHT  │
│  33%    │   34%    │  33%    │
├─────────┼──────────┼─────────┤
│ 2.5m ✓  │  0.6m ⚠  │ 3.0m ✓ │
│ Livre   │ Obstáculo│ Livre   │
└─────────┴──────────┴─────────┘

         ↓

📤 TRANSMISSÃO
├─ Compressão JPEG (70%)
├─ Base64 encoding
└─ WebSocket → Frontend (10 Hz)
```

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

### Lógica de Decisão - Fluxograma

```
┌─────────────────────────────────────────────────────┐
│       INÍCIO DO CICLO DE NAVEGAÇÃO (10 Hz)          │
└──────────────────┬──────────────────────────────────┘
                   ↓
          ┌────────────────┐
          │ Analisar 3     │
          │ setores        │
          │ (L, C, R)      │
          └────────┬───────┘
                   ↓
          ┌────────────────┐
          │ Centro livre?  │
          │ (>0.8m)        │
          └────┬───────┬───┘
               │       │
          SIM  │       │ NÃO
               ↓       ↓
        ┌──────────┐ ┌────────────────┐
        │ AVANÇAR  │ │ Qual lado      │
        │ (frente) │ │ está livre?    │
        └────┬─────┘ └───┬────────┬───┘
             │           │        │
             │      ESQ  │        │ DIR
             │           ↓        ↓
             │    ┌───────────┐ ┌───────────┐
             │    │ VIRAR     │ │ VIRAR     │
             │    │ ESQUERDA  │ │ DIREITA   │
             │    └─────┬─────┘ └─────┬─────┘
             │          │             │
             │          └──────┬──────┘
             │                 │
             │            AMBOS BLOQUEADOS
             │                 ↓
             │          ┌─────────────┐
             │          │ MOVER P/    │
             │          │ TRÁS (ré)   │
             │          └──────┬──────┘
             │                 │
             └─────────┬───────┘
                       ↓
              ┌─────────────────┐
              │ Incrementar     │
              │ contador_livre  │
              └────────┬────────┘
                       ↓
              ┌─────────────────┐
              │ Atingiu 8       │
              │ movimentos?     │
              └────┬───────┬────┘
                   │       │
              NÃO  │       │ SIM
                   ↓       ↓
            ┌──────────┐ ┌────────────────┐
            │ Continuar│ │ ROTAÇÃO 45°    │
            │ navegando│ │ (horário)      │
            └──────┬───┘ │ 0.8s × 6 steps │
                   │     └────────┬───────┘
                   │              │
                   └──────┬───────┘
                          ↓
                   ┌─────────────┐
                   │ Zerar       │
                   │ contador    │
                   └──────┬──────┘
                          ↓
                   [PRÓXIMO CICLO]
```

### Parâmetros de Decisão

| Condição | Distância | Ação |
|----------|-----------|------|
| Centro livre | > 0.8m | Avançar |
| Centro bloqueado | < 0.8m | Verificar laterais |
| Lateral livre | > 0.6m | Virar para lado livre |
| Todos bloqueados | < 0.6m | Mover para trás |
| 8 movimentos livres | - | Rotação 45° (mapeamento) |

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

### Configuração 3 Rodas - Vista Superior

```
        Frente do Robô
             ↑
             
       ╔═══════════╗
       ║           ║
    M2 ●           ● M3
       ║           ║
       ║     ●     ║  (Centro de rotação)
       ║           ║
       ║     M1    ║
       ╚═════●═════╝
       
       Trás do Robô
```

### Tabela de Comandos (V = velocidade configurada)

| Direção | M1 | M2 | M3 | Descrição |
|---------|----|----|-----|-----------|
| 🔼 **Frente** | 0 | -V | +V | M2 anti-horário, M3 horário |
| 🔽 **Trás** | 0 | +V | -V | M2 horário, M3 anti-horário |
| ⬅️ **Esquerda** | +V | -V | +V | Todos giram para esquerda |
| ➡️ **Direita** | -V | -V | +V | M1/M2 horário, M3 anti-horário |
| 🔄 **Rotação 45°** | -V | -V | -V | Todos horário (in-place) |
| ⏸️ **Parar** | 0 | 0 | 0 | Todos motores desligados |

### Exemplo Visual: Movimento para FRENTE

```
    Antes              Durante             Depois
    
    M2  M3            M2⟲  M3⟳           M2  M3
     ●   ●             ↑    ↑             ●   ●
      \ /               \  /               \ /
       ●                 ●▲                 ●
      M1                M1                M1
                   (robô moveu 10cm)
                   
Legenda:
⟲ = rotação anti-horária (negativo)
⟳ = rotação horária (positivo)
▲ = direção de movimento resultante
```

### Exemplo Visual: ROTAÇÃO 45° (in-place)

```
   Passo 1 (0°)        Passo 4 (45°)      Passo 6 (final)
   
   M2    M3           M2    M3              M3
    ●─────●            ╲    ╱                ●
    │     │             ╲  ╱                ╱ ╲
    │  ●  │              ●                 ●   M2
    │ M1  │             ╱  ╲                ╲ ╱
    ●─────●            ╱    ╲                ●
                      M1                    M1
                      
  Orientação: 0°     Orientação: ~22°    Orientação: 45°
  Tempo: 0.0s        Tempo: 0.4s         Tempo: 0.8s
  
  Comando: M1=-100, M2=-100, M3=-100 (todos horário)
  Duração: 0.8s × 6 repetições = mapeamento de 270°
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

### Tela Principal

> **Nota:** Para incluir screenshot da interface, capture a tela rodando e salve como `docs/tela-principal.png`

```
┌─────────────────────────────────────────────────────────────┐
│                    TRI-BOT PILOT                            │
│         Sistema de Controle Remoto com Navegação           │
├─────────────────────────────────────────────────────────────┤
│ ① STATUS DE CONEXÕES                                        │
│   🔴 Servidor Python: Desconectado                         │
│   ⚫ Arduino: Aguardando conexão                            │
├─────────────────────────────────────────────────────────────┤
│ ② PORTA SERIAL                                              │
│   [/dev/ttyUSB0 ▼] [🔄] [Conectar Arduino]                │
├─────────────────────────────────────────────────────────────┤
│ ③ VISUALIZAÇÃO DE SENSORES                                 │
│   ┌───────────────────────────────────┐                    │
│   │                                   │  Offline            │
│   │     📹 CÂMERA D435               │                    │
│   │     (Stream em tempo real)        │                    │
│   │                                   │                    │
│   └───────────────────────────────────┘                    │
├─────────────────────────────────────────────────────────────┤
│ ④ MODO AUTÔNOMO                                            │
│   [🔘 OFF] O robô desviará automaticamente de objetos      │
├─────────────────────────────────────────────────────────────┤
│ ⑤ CONTROLE MANUAL                                          │
│   [▶ Expandir] Use controles direcionais para mover        │
├─────────────────────────────────────────────────────────────┤
│ ⑥ VELOCIDADE AUTÔNOMA                          100         │
│   Lento (50) ◀═══════●═══════▶ Rápido (200)              │
├─────────────────────────────────────────────────────────────┤
│ ⑦ [      PARADA DE EMERGÊNCIA      ]                       │
│    Pressione para interromper todos os movimentos          │
└─────────────────────────────────────────────────────────────┘
  ⑧ Notificações (toasts no canto superior direito)
```

A interface é dividida em seções funcionais numeradas abaixo:

#### 1. Área de Status de Conexões
**Localização:** Topo da tela

- **Servidor Python (vermelho/verde):** 
  - Verde: Backend WebSocket conectado
  - Vermelho: Backend desconectado
  - Instrução quando offline: "Execute robot_autonomous_control.py"

- **Arduino (cinza/verde):**
  - Verde: Arduino conectado via serial
  - Cinza: Aguardando conexão
  - Mostra porta conectada quando ativo

#### 2. Seletor de Porta Serial
**Função:** Escolher porta USB do Arduino

- Dropdown com portas disponíveis (/dev/ttyUSB0, /dev/ttyACM0, etc.)
- Botão "Atualizar" (🔄) para reescanear portas
- Botão "Conectar Arduino" para estabelecer comunicação serial

**Diagnóstico:** Link "Problemas ao conectar?" abre guia de troubleshooting

#### 3. Visualização de Sensores
**Função:** Stream de vídeo da câmera D435 em tempo real

- Área de vídeo 640x480 pixels
- Exibe feed RGB da câmera
- Bounding boxes de objetos rastreados (quando detectados)
- Status "Desconectado" quando backend offline
- Badge "Offline" no canto superior direito

#### 4. Controle de Modo Autônomo
**Função:** Ativar navegação autônoma

- **Toggle Switch:** Liga/desliga modo autônomo
- **Descrição:** "O robô desviará automaticamente de objetos detectados pela câmera"
- **Pré-requisitos:** 
  - Arduino conectado
  - Backend Python rodando
  - Câmera D435 operacional

#### 5. Controle Manual
**Função:** Movimentação manual do robô

- Botão expansível "Controle Manual"
- Controles direcionais (cima, baixo, esquerda, direita, parar)
- Suporte a teclado: WASD, setas, espaço para parar
- Slider de velocidade individual por motor (M1, M2, M3)

#### 6. Ajuste de Velocidade Autônoma
**Função:** Configurar velocidade antes de ativar modo autônomo

- **Slider horizontal:** 50 (Lento) até 200 (Rápido)
- **Valor padrão:** 100
- **Label:** "Velocidade Autônoma" com valor numérico
- **Uso:** Ajuste preventivo de velocidade antes de iniciar navegação

#### 7. Botão de Parada de Emergência
**Função:** Interromper todos os movimentos imediatamente

- **Aparência:** Botão rosa/vermelho grande
- **Texto:** "PARADA DE EMERGÊNCIA"
- **Ação:** Envia comando de parar para todos os motores (M1=0, M2=0, M3=0)
- **Atalho:** Tecla de espaço
- **Uso:** Segurança em caso de comportamento inesperado

#### 8. Área de Notificações
**Função:** Feedback de sistema e erros

- Toasts aparecem no canto superior direito
- **Erro de Conexão (vermelho):** "Servidor Python não está rodando. Execute: python robot_autonomous_control.py"
- **Sucesso (verde):** Confirmação de ações
- **Avisos (amarelo):** Alertas de sensores offline

### Fluxo de Uso Típico

```
1. Iniciar backend → python robot_autonomous_control.py
2. Interface detecta conexão (status verde)
3. Selecionar porta serial (/dev/ttyUSB0)
4. Clicar "Conectar Arduino"
5. Ajustar velocidade autônoma (ex: 100)
6. Ativar toggle "Modo Autônomo"
7. Robô navega autonomamente
8. Parada de emergência se necessário
```

### Tecnologias
- React 18 + TypeScript
- Vite (bundler)
- WebSocket API nativa
- Shadcn/ui (componentes)
- Tailwind CSS (estilização)

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
