# Screenshots da Interface - Tri-Bot Pilot

## Nota sobre Imagens

Para adicionar o screenshot ao relatório técnico:

1. Capture um screenshot da interface rodando (`http://localhost:5173` ou preview do Lovable)
2. Salve a imagem como `tela-principal.png` na pasta `docs/`
3. A referência `![Interface Tri-Bot Pilot](tela-principal.png)` no relatório apontará para esta imagem

## Localização da Imagem

A imagem referenciada no relatório deve estar em:
- `docs/tela-principal.png` (mesma pasta do relatório resumido)

## Como Capturar

**Usando o sistema:**
1. Execute `python robot_autonomous_control.py` no notebook
2. Abra a interface no navegador
3. Aguarde conexão do backend (status verde)
4. Tire screenshot da tela completa
5. Salve como `tela-principal.png`

**Elementos importantes a capturar:**
- Status de conexões (topo)
- Seletor de porta serial
- Área de visualização de câmera
- Controles de modo autônomo
- Botão de parada de emergência
- Slider de velocidade

## Imagens Adicionais Recomendadas

Para documentação mais completa, considere adicionar:

1. `tela-conectado.png` - Interface com Arduino conectado e sensores ativos
2. `tela-autonomo-ativo.png` - Robô em navegação autônoma com objetos detectados
3. `tela-camera-objetos.png` - Câmera mostrando bounding boxes de objetos rastreados
4. `tela-controle-manual.png` - Seção de controle manual expandida
5. `diagrama-arquitetura.png` - Diagrama de blocos da arquitetura do sistema
