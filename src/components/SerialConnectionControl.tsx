import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { RefreshCw, Plug } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface SerialConnectionControlProps {
  wsRef: React.RefObject<WebSocket | null>;
  isArduinoConnected: boolean;
  availablePorts: string[];
  onConnectionChange: (connected: boolean) => void;
}

export const SerialConnectionControl = ({
  wsRef,
  isArduinoConnected,
  availablePorts,
  onConnectionChange,
}: SerialConnectionControlProps) => {
  const [selectedPort, setSelectedPort] = useState<string>("ttyUSB0");
  const [isConnecting, setIsConnecting] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'discover_ports' }));
    }
  }, [wsRef]);

  const handleRefreshPorts = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'discover_ports' }));
      toast({
        title: "Atualizando portas",
        description: "Buscando portas disponíveis...",
      });
    }
  };

  const handleConnect = () => {
    if (!selectedPort) {
      toast({
        title: "Selecione uma porta",
        variant: "destructive",
      });
      return;
    }

    setIsConnecting(true);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'connect_serial',
        port: selectedPort
      }));
      
      setTimeout(() => setIsConnecting(false), 3000);
    } else {
      setIsConnecting(false);
      toast({
        title: "Erro",
        description: "WebSocket não conectado. Execute robot_autonomous_control.py",
        variant: "destructive",
      });
    }
  };

  const handleDisconnect = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'disconnect_serial' }));
      onConnectionChange(false);
    }
  };

  if (isArduinoConnected) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/10">
          <Plug className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">Conectado: {selectedPort}</span>
        </div>
        <Button onClick={handleDisconnect} variant="outline" className="w-full">
          Desconectar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="port-select">Porta Serial</Label>
        <div className="flex gap-2">
          <Select value={selectedPort} onValueChange={setSelectedPort}>
            <SelectTrigger id="port-select" className="flex-1">
              <SelectValue placeholder="Selecione a porta" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ttyUSB0">/dev/ttyUSB0</SelectItem>
              <SelectItem value="ttyUSB1">/dev/ttyUSB1</SelectItem>
              <SelectItem value="ttyACM0">/dev/ttyACM0</SelectItem>
              <SelectItem value="ttyACM1">/dev/ttyACM1</SelectItem>
              {availablePorts.map((port) => (
                <SelectItem key={port} value={port}>
                  {port}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefreshPorts}
            title="Atualizar portas"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Button
        onClick={handleConnect}
        disabled={isConnecting}
        className="w-full"
      >
        {isConnecting ? "Conectando..." : "Conectar Arduino"}
      </Button>
    </div>
  );
};
