# Screenshots da Interface - Tri-Bot Pilot

## Tela 1: Dashboard Principal (Sistema de Controle Remoto com Navegação Autônoma)

Esta é a tela inicial do sistema onde o usuário gerencia a conexão e escolhe o modo de operação do robô. No topo, há um indicador de status que mostra se o sistema está conectado ao backend Python e ao Arduino. Logo abaixo, encontra-se um switch para alternar entre Modo Autônomo (onde o robô desvia automaticamente de obstáculos usando a câmera D435) e Controle Manual (onde o usuário comanda diretamente os movimentos). O botão vermelho "PARADA DE EMERGÊNCIA" permite interromper imediatamente todos os movimentos do robô em situações críticas. Na parte inferior, há uma instrução para executar o script `robot_autonomous_control.py` no notebook para iniciar o sistema.

## Tela 2: Controle Direcional

Esta tela oferece controle manual completo do robô através de uma interface intuitiva. O usuário pode ajustar a velocidade de movimento usando um slider que varia de 0 a 255, com entrada manual também disponível. Os botões direcionais (setas para cima, baixo, esquerda e direita) permitem movimentar o robô, enquanto o botão central vermelho para o movimento. O controle também pode ser feito via teclado usando as teclas WASD, setas direcionais ou espaço para parar. Na parte inferior, são exibidos os comandos específicos enviados para cada motor (M1, M2, M3) em cada direção, permitindo ao usuário entender como o robô omnidirecional executa cada movimento.

## Tela 3: Dashboard de Sensores e Visualização

Esta tela apresenta em tempo real todos os dados coletados pelos sensores do robô. A seção "Câmera D435 (Superior)" mostra o feed de vídeo da câmera montada na parte superior do robô, responsável por detectar objetos altos. A seção "LiDAR L515 (Inferior)" exibe dados do sensor LiDAR montado embaixo, que detecta obstáculos no chão divididos em três zonas (esquerda, centro, direita), com indicação de distância em metros. A seção "Detecção de Altura" mostra informações processadas pela câmera D435 sobre objetos altos, também dividida em três zonas. No lado direito, há uma área de "Reconstrução 3D do Ambiente" que exibe um mapa tridimensional gerado pelo LiDAR, permitindo visualizar espacialmente o ambiente ao redor do robô. Todas as seções aguardam dados dos sensores quando o sistema está iniciando.
