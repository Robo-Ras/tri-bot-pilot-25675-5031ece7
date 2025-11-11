import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Usb, Power } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface WebSerialConnectionProps {
  onSendCommand: (m1: number, m2: number, m3: number) => void;
}

export const WebSerialConnection = ({ onSendCommand }: WebSerialConnectionProps) => {
  const [port, setPort] = useState<SerialPort | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { toast } = useToast();

  const connectSerial = async () => {
    try {
      // Verifica se Web Serial API está disponível
      if (!('serial' in navigator)) {
        toast({
          title: "API não suportada",
          description: "Seu navegador não suporta Web Serial API. Use Chrome, Edge ou Opera.",
          variant: "destructive",
        });
        return;
      }

      // Solicita acesso à porta serial (abre popup do navegador)
      const selectedPort = await navigator.serial.requestPort();
      
      // Abre a porta com configurações para Arduino
      await selectedPort.open({ 
        baudRate: 9600,
        dataBits: 8,
        stopBits: 1,
        parity: "none"
      });

      setPort(selectedPort);
      setIsConnected(true);

      toast({
        title: "Arduino Conectado",
        description: "Conexão serial estabelecida com sucesso",
      });

      console.log('✓ Arduino conectado via Web Serial API');
    } catch (error) {
      console.error('Erro ao conectar:', error);
      toast({
        title: "Erro na Conexão",
        description: "Não foi possível conectar ao Arduino",
        variant: "destructive",
      });
    }
  };

  const disconnectSerial = async () => {
    if (port) {
      try {
        await port.close();
        setPort(null);
        setIsConnected(false);
        
        toast({
          title: "Desconectado",
          description: "Arduino desconectado",
        });
      } catch (error) {
        console.error('Erro ao desconectar:', error);
      }
    }
  };

  const sendSerialCommand = async (m1: number, m2: number, m3: number) => {
    if (!port || !isConnected) {
      toast({
        title: "Não Conectado",
        description: "Conecte o Arduino primeiro",
        variant: "destructive",
      });
      return;
    }

    try {
      const writer = port.writable?.getWriter();
      if (writer) {
        // Formato: M1,M2,M3\n
        const command = `${m1},${m2},${m3}\n`;
        const data = new TextEncoder().encode(command);
        await writer.write(data);
        writer.releaseLock();
        
        console.log('✓ Comando enviado:', command.trim());
        onSendCommand(m1, m2, m3);
      }
    } catch (error) {
      console.error('Erro ao enviar comando:', error);
      toast({
        title: "Erro de Comunicação",
        description: "Não foi possível enviar o comando",
        variant: "destructive",
      });
    }
  };

  // Expõe a função de envio para componentes pais
  (window as any).sendArduinoCommand = sendSerialCommand;

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Usb className="w-5 h-5" />
          <div>
            <h3 className="font-semibold">Conexão Arduino</h3>
            <p className="text-sm text-muted-foreground">
              {isConnected ? "Conectado via USB" : "Clique para conectar"}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge variant={isConnected ? "default" : "secondary"}>
            {isConnected ? "Conectado" : "Desconectado"}
          </Badge>
          
          {!isConnected ? (
            <Button onClick={connectSerial}>
              <Power className="w-4 h-4 mr-2" />
              Conectar
            </Button>
          ) : (
            <Button onClick={disconnectSerial} variant="outline">
              Desconectar
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
};
