import { useState, useEffect, useRef } from "react";
import DirectionalControl from "@/components/DirectionalControl";
import MotorSpeedControl from "@/components/MotorSpeedControl";
import { SensorVisualization } from "@/components/SensorVisualization";
import { AutonomousControl } from "@/components/AutonomousControl";
import { SerialConnectionControl } from "@/components/SerialConnectionControl";
import { ArduinoTroubleshooting } from "@/components/ArduinoTroubleshooting";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";

const Index = () => {
  const [lastCommand, setLastCommand] = useState<string>("");
  const [isConnected, setIsConnected] = useState(false);
  const [isArduinoConnected, setIsArduinoConnected] = useState(false);
  const [autonomousMode, setAutonomousMode] = useState(false);
  const [cameraImage, setCameraImage] = useState<string>();
  const [groundObstacles, setGroundObstacles] = useState<any>();
  const [heightObstacles, setHeightObstacles] = useState<any>();
  const [trackedObjects, setTrackedObjects] = useState<any>();
  const [navigationStatus, setNavigationStatus] = useState<any>();
  const [availablePorts, setAvailablePorts] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const { toast } = useToast();

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      console.log('🌐 Tentando conectar ao servidor Python em ws://localhost:8765');
      const ws = new WebSocket('ws://localhost:8765');
      
      ws.onopen = () => {
        console.log('✓✓✓ CONECTADO ao servidor Python com sucesso!');
        setIsConnected(true);
        toast({
          title: "Conectado",
          description: "Conexão estabelecida com o sistema de sensores",
        });
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('📩 Mensagem recebida do servidor:', data.type);
        
        if (data.type === 'sensor_data') {
          if (data.camera) {
            setCameraImage(data.camera);
          }
          if (data.ground_obstacles) {
            setGroundObstacles(data.ground_obstacles);
          }
          if (data.height_obstacles) {
            setHeightObstacles(data.height_obstacles);
          }
          if (data.tracked_objects) {
            setTrackedObjects(data.tracked_objects);
          }
          if (data.navigation_status) {
            setNavigationStatus(data.navigation_status);
          }
        } else if (data.type === 'ports_list') {
          console.log('✅ Lista de portas recebida:', data.ports);
          setAvailablePorts(data.ports || []);
        } else if (data.type === 'serial_status') {
          console.log('✅ Status serial atualizado:', data.connected, data.port);
          setIsArduinoConnected(data.connected);
          if (data.connected) {
            toast({
              title: "Arduino Conectado",
              description: `Conectado na porta ${data.port}`,
            });
          }
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ ERRO WebSocket:', error);
        console.error('Certifique-se que robot_autonomous_control.py está rodando!');
        console.error('Execute: python robot_autonomous_control.py');
        toast({
          title: "Erro de Conexão",
          description: "Servidor Python não está rodando. Execute: python robot_autonomous_control.py",
          variant: "destructive",
        });
      };
      
      ws.onclose = () => {
        console.log('✗ Desconectado do servidor Python');
        setIsConnected(false);
        // Tentar reconectar após 3 segundos
        console.log('⏳ Tentando reconectar em 3 segundos...');
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current = ws;
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [toast]);

  const handleSendCommand = (m1: number, m2: number, m3: number) => {
    setLastCommand(`M1: ${m1}, M2: ${m2}, M3: ${m3}`);
    console.log("Sending command:", m1, m2, m3);
    
    // Envia comando via WebSocket se conectado
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'move',
        m1, m2, m3
      }));
    }
  };

  const handleToggleAutonomous = (enabled: boolean) => {
    setAutonomousMode(enabled);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'set_autonomous',
        enabled
      }));
    }
    
    toast({
      title: enabled ? "Modo Autônomo Ativado" : "Modo Manual Ativado",
      description: enabled 
        ? "O robô agora desviará automaticamente de obstáculos" 
        : "Use os controles manuais para mover o robô",
    });
  };

  const handleEmergencyStop = () => {
    handleSendCommand(0, 0, 0);
    setAutonomousMode(false);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'set_autonomous',
        enabled: false
      }));
    }
    toast({
      title: "Parada de Emergência",
      description: "Todos os motores foram parados",
      variant: "destructive",
    });
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-4xl font-bold">Tri-Bot Pilot</h1>
      </div>
      <p className="text-center text-muted-foreground mb-8">
        Sistema de Controle Remoto com Navegação Autônoma
      </p>
      
      {/* Connection Status */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* WebSocket Status */}
        <div className={`p-4 rounded-lg border-2 ${isConnected ? 'bg-green-500/10 border-green-500' : 'bg-destructive/10 border-destructive'}`}>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-destructive'}`} />
            <span className="font-semibold">Servidor Python</span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {isConnected ? 'Conectado (WebSocket)' : 'Desconectado - Execute robot_autonomous_control.py'}
          </p>
        </div>

        {/* Arduino Status */}
        <div className={`p-4 rounded-lg border-2 ${isArduinoConnected ? 'bg-green-500/10 border-green-500' : 'bg-muted/50 border-border'}`}>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isArduinoConnected ? 'bg-green-500 animate-pulse' : 'bg-muted-foreground'}`} />
            <span className="font-semibold">Arduino</span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {isArduinoConnected ? 'Conectado' : 'Aguardando conexão'}
          </p>
        </div>
      </div>

      {/* Arduino Connection */}
      <div className="mb-6 space-y-4">
        <SerialConnectionControl
          wsRef={wsRef}
          isArduinoConnected={isArduinoConnected}
          availablePorts={availablePorts}
          onConnectionChange={setIsArduinoConnected}
        />
        
        {!isArduinoConnected && <ArduinoTroubleshooting />}
      </div>
      
      {lastCommand && (
        <div className="text-center mb-6 p-4 bg-secondary rounded-lg">
          <p className="text-sm text-muted-foreground">Último comando enviado:</p>
          <p className="font-mono font-semibold">{lastCommand}</p>
        </div>
      )}

      {/* Autonomous Control */}
      <div className="mb-6">
        <AutonomousControl
          isConnected={isConnected}
          autonomousMode={autonomousMode}
          onToggleAutonomous={handleToggleAutonomous}
          onEmergencyStop={handleEmergencyStop}
          navigationStatus={navigationStatus}
          heightObstacles={heightObstacles}
        />
      </div>

      {/* Camera D435 */}
      <div className="mb-6">
        <SensorVisualization
          cameraImage={cameraImage}
          groundObstacles={groundObstacles}
          heightObstacles={heightObstacles}
          trackedObjects={trackedObjects}
        />
      </div>

      <Tabs defaultValue="directional" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-6">
          <TabsTrigger value="directional">Controle Direcional</TabsTrigger>
          <TabsTrigger value="motor">Controle por Motor</TabsTrigger>
        </TabsList>
        
        <TabsContent value="directional">
          <DirectionalControl onSendCommand={handleSendCommand} />
        </TabsContent>
        
        <TabsContent value="motor">
          <MotorSpeedControl onSendCommand={handleSendCommand} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Index;
