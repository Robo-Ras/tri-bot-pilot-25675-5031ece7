import { useState, useEffect, useRef } from "react";
import DirectionalControl from "@/components/DirectionalControl";
import MotorSpeedControl from "@/components/MotorSpeedControl";
import { SensorVisualization } from "@/components/SensorVisualization";
import { LidarVisualization } from "@/components/LidarVisualization";
import { AutonomousControl } from "@/components/AutonomousControl";
import { SerialConnectionControl } from "@/components/SerialConnectionControl";
import Map3DVisualization from "@/components/Map3DVisualization";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";

const Index = () => {
  const [lastCommand, setLastCommand] = useState<string>("");
  const [isConnected, setIsConnected] = useState(false);
  const [isArduinoConnected, setIsArduinoConnected] = useState(false);
  const [autonomousMode, setAutonomousMode] = useState(false);
  const [cameraImage, setCameraImage] = useState<string>();
  const [lidarImage, setLidarImage] = useState<string>();
  const [groundObstacles, setGroundObstacles] = useState<any>();
  const [heightObstacles, setHeightObstacles] = useState<any>();
  const [pointCloud, setPointCloud] = useState<any>();
  const [trackedObjects, setTrackedObjects] = useState<any>();
  const wsRef = useRef<WebSocket | null>(null);
  const { toast } = useToast();

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8765');
      
      ws.onopen = () => {
        console.log('✓ Conectado ao servidor Python');
        setIsConnected(true);
        toast({
          title: "Conectado",
          description: "Conexão estabelecida com o sistema de sensores",
        });
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'sensor_data') {
          if (data.camera) {
            setCameraImage(data.camera);
          }
          if (data.lidar_image) {
            setLidarImage(data.lidar_image);
          }
          if (data.ground_obstacles) {
            setGroundObstacles(data.ground_obstacles);
          }
          if (data.height_obstacles) {
            setHeightObstacles(data.height_obstacles);
          }
          if (data.point_cloud) {
            setPointCloud(data.point_cloud);
          }
          if (data.tracked_objects) {
            setTrackedObjects(data.tracked_objects);
          }
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        toast({
          title: "Erro de Conexão",
          description: "Verifique se o script Python está rodando",
          variant: "destructive",
        });
      };
      
      ws.onclose = () => {
        console.log('✗ Desconectado do servidor');
        setIsConnected(false);
        // Tentar reconectar após 3 segundos
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
      <h1 className="text-4xl font-bold text-center mb-2">Tri-Bot Pilot</h1>
      <p className="text-center text-muted-foreground mb-8">
        Sistema de Controle Remoto com Navegação Autônoma
      </p>
      
      {lastCommand && (
        <div className="text-center mb-6 p-4 bg-secondary rounded-lg">
          <p className="text-sm text-muted-foreground">Último comando enviado:</p>
          <p className="font-mono font-semibold">{lastCommand}</p>
        </div>
      )}

      {/* Serial Connection */}
      <div className="mb-6">
        <SerialConnectionControl
          wsRef={wsRef}
          isArduinoConnected={isArduinoConnected}
          onConnectionChange={setIsArduinoConnected}
        />
      </div>

      {/* Autonomous Control */}
      <div className="mb-6">
        <AutonomousControl
          isConnected={isConnected}
          autonomousMode={autonomousMode}
          onToggleAutonomous={handleToggleAutonomous}
          onEmergencyStop={handleEmergencyStop}
        />
      </div>

      {/* Sensors and 3D Map */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SensorVisualization
          cameraImage={cameraImage}
          groundObstacles={groundObstacles}
          heightObstacles={heightObstacles}
          trackedObjects={trackedObjects}
        />
        
        <LidarVisualization
          lidarImage={lidarImage}
          groundObstacles={groundObstacles}
        />
      </div>

      {/* 3D Reconstruction Map */}
      <div className="mb-6">
        <Map3DVisualization pointCloud={pointCloud} />
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
