import { useEffect, useState } from "react";
import { Smile, Frown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const RobotFace = () => {
  const [isMoving, setIsMoving] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [serverIp, setServerIp] = useState<string>(() => {
    return localStorage.getItem('robot-server-ip') || '';
  });
  const [tempIp, setTempIp] = useState<string>(serverIp);
  const [showConfig, setShowConfig] = useState<boolean>(!serverIp);

  useEffect(() => {
    if (!serverIp) return;

    const websocket = new WebSocket(`ws://${serverIp}:8765`);
    
    websocket.onopen = () => {
      console.log('Robot Face: WebSocket connected');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Detecta se o robô está em movimento baseado nos comandos
        if (data.command && data.command !== 'stop') {
          setIsMoving(true);
        } else if (data.command === 'stop') {
          setIsMoving(false);
        }
        
        // Detecta movimento pela navegação autônoma
        if (data.navigation) {
          setIsMoving(data.navigation.direction !== 'stop');
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('Robot Face: WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log('Robot Face: WebSocket disconnected, reconnecting...');
      setTimeout(() => {
        setWs(null);
      }, 3000);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [serverIp]);

  const handleConnect = () => {
    localStorage.setItem('robot-server-ip', tempIp);
    setServerIp(tempIp);
    setShowConfig(false);
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-background via-secondary/20 to-background relative">
      {/* Config Button */}
      <Button
        variant="ghost"
        size="sm"
        className="absolute top-4 right-4 text-muted-foreground"
        onClick={() => setShowConfig(!showConfig)}
      >
        ⚙️ Configurar
      </Button>

      {/* Config Panel */}
      {showConfig && (
        <div className="absolute top-20 right-4 bg-card p-6 rounded-lg shadow-xl border border-border space-y-4 z-10">
          <h3 className="font-semibold text-lg">Configurar Servidor</h3>
          <div className="space-y-2">
            <label className="text-sm text-muted-foreground">
              IP do notebook (ex: 192.168.1.100)
            </label>
            <Input
              type="text"
              placeholder="192.168.1.100"
              value={tempIp}
              onChange={(e) => setTempIp(e.target.value)}
              className="w-64"
            />
          </div>
          <Button onClick={handleConnect} className="w-full">
            Conectar
          </Button>
          <p className="text-xs text-muted-foreground">
            💡 Use o comando 'hostname -I' no Linux para descobrir o IP
          </p>
        </div>
      )}

      <div className="text-center space-y-8 p-8">
        {/* Face Icon */}
        <div className={`transition-all duration-500 ${isMoving ? 'scale-110 animate-pulse' : 'scale-100'}`}>
          {isMoving ? (
            <Smile 
              className="w-64 h-64 text-green-500 mx-auto drop-shadow-2xl" 
              strokeWidth={1.5}
            />
          ) : (
            <Frown 
              className="w-64 h-64 text-amber-500 mx-auto drop-shadow-2xl opacity-80" 
              strokeWidth={1.5}
            />
          )}
        </div>

        {/* Status Text */}
        <div className="space-y-2">
          <h1 className={`text-5xl font-bold transition-colors duration-300 ${
            isMoving ? 'text-green-500' : 'text-amber-500'
          }`}>
            {isMoving ? 'Em Movimento' : 'Parado'}
          </h1>
          <p className="text-muted-foreground text-xl">
            {ws ? '🟢 Conectado' : '🔴 Desconectado'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default RobotFace;
