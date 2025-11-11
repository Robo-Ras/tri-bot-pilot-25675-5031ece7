import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Usb, RefreshCw } from "lucide-react";

interface SerialConnectionControlProps {
  wsRef: React.RefObject<WebSocket | null>;
  isArduinoConnected: boolean;
  onConnectionChange: (connected: boolean) => void;
}

export const SerialConnectionControl = ({ 
  wsRef, 
  isArduinoConnected,
  onConnectionChange 
}: SerialConnectionControlProps) => {
  const [ports, setPorts] = useState<string[]>([]);
  const [selectedPort, setSelectedPort] = useState<string>("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshPorts = () => {
    console.log('🔍 Tentando descobrir portas...');
    console.log('WebSocket state:', wsRef.current?.readyState);
    console.log('OPEN =', WebSocket.OPEN, 'CONNECTING =', WebSocket.CONNECTING, 'CLOSED =', WebSocket.CLOSED);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('✓ WebSocket aberto, enviando discover_ports');
      setIsRefreshing(true);
      wsRef.current.send(JSON.stringify({
        type: 'discover_ports'
      }));
      
      setTimeout(() => setIsRefreshing(false), 1000);
    } else {
      console.error('✗ WebSocket não está aberto! Estado:', wsRef.current?.readyState);
      console.error('Certifique-se que robot_autonomous_control.py está rodando');
    }
  };

  const connectArduino = () => {
    console.log('🔌 Tentando conectar Arduino na porta:', selectedPort);
    console.log('WebSocket state:', wsRef.current?.readyState);
    
    if (selectedPort && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('✓ Enviando comando connect_serial');
      wsRef.current.send(JSON.stringify({
        type: 'connect_serial',
        port: selectedPort
      }));
    } else {
      console.error('✗ Não pode conectar! Porta:', selectedPort, 'WS state:', wsRef.current?.readyState);
    }
  };

  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const handleMessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'ports_list') {
          console.log('Portas recebidas:', data.ports);
          setPorts(data.ports || []);
        } else if (data.type === 'serial_status') {
          console.log('Status serial:', data.connected, data.port);
          onConnectionChange(data.connected);
        }
      };

      wsRef.current.addEventListener('message', handleMessage);
      
      // Request ports on mount
      setTimeout(() => refreshPorts(), 500);

      return () => {
        wsRef.current?.removeEventListener('message', handleMessage);
      };
    }
  }, [wsRef.current, wsRef.current?.readyState]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Usb className="h-5 w-5" />
            <CardTitle>Conexão Arduino</CardTitle>
          </div>
          <Badge variant={isArduinoConnected ? "default" : "secondary"}>
            {isArduinoConnected ? "Conectado" : "Desconectado"}
          </Badge>
        </div>
        <CardDescription>
          Selecione a porta serial para conectar ao Arduino
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2">
          <Select value={selectedPort} onValueChange={setSelectedPort} disabled={isArduinoConnected}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Selecione uma porta" />
            </SelectTrigger>
            <SelectContent>
              {ports.length === 0 ? (
                <SelectItem value="none" disabled>Nenhuma porta encontrada</SelectItem>
              ) : (
                ports.map((port) => (
                  <SelectItem key={port} value={port}>
                    {port}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          
          <Button 
            variant="outline" 
            size="icon"
            onClick={refreshPorts}
            disabled={isRefreshing || isArduinoConnected}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          
          <Button 
            onClick={connectArduino}
            disabled={!selectedPort || isArduinoConnected}
          >
            Conectar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
