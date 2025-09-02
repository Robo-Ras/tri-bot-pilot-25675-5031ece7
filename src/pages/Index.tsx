import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';

const Index = () => {
  const [port, setPort] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string>('');
  const [motor1, setMotor1] = useState<number>(0);
  const [motor2, setMotor2] = useState<number>(0);
  const [motor3, setMotor3] = useState<number>(0);

  // Verifica se o navegador suporta WebSerial
  const isWebSerialSupported = 'serial' in navigator;

  const connectToArduino = async () => {
    try {
      if (!isWebSerialSupported) {
        throw new Error('WebSerial não é suportado neste navegador');
      }

      const selectedPort = await (navigator as any).serial.requestPort();
      await selectedPort.open({ baudRate: 9600 });
      
      setPort(selectedPort);
      setIsConnected(true);
      setError('');
    } catch (err) {
      setError(`Erro na conexão: ${err instanceof Error ? err.message : 'Erro desconhecido'}`);
    }
  };

  const sendCommand = async (m1: number, m2: number, m3: number) => {
    if (!port || !isConnected) return;

    try {
      const writer = port.writable?.getWriter();
      if (writer) {
        const command = `${m1},${m2},${m3}\n`;
        const encoder = new TextEncoder();
        await writer.write(encoder.encode(command));
        writer.releaseLock();
      }
    } catch (err) {
      setError(`Erro ao enviar comando: ${err instanceof Error ? err.message : 'Erro desconhecido'}`);
    }
  };

  const goCommand = () => {
    sendCommand(motor1, motor2, motor3);
  };

  const stopCommand = () => {
    sendCommand(0, 0, 0);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Controle do Robô</CardTitle>
          <CardDescription>
            Interface Web para controlar robô via Arduino
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center space-y-2">
            <Badge variant={isConnected ? "default" : "secondary"}>
              {isConnected ? "Conectado" : "Desconectado"}
            </Badge>
            
            {!isWebSerialSupported && (
              <Alert>
                <AlertDescription>
                  WebSerial não é suportado neste navegador. Use Chrome/Edge mais recente.
                </AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {!isConnected && isWebSerialSupported && (
              <Button onClick={connectToArduino} className="w-full">
                Conectar Arduino
              </Button>
            )}
          </div>

          {isConnected && (
            <div className="space-y-6">
              <div className="space-y-6">
                <div className="space-y-3">
                  <Label>Motor 1</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-4">
                      <Slider
                        value={[motor1]}
                        onValueChange={(value) => setMotor1(value[0])}
                        min={-255}
                        max={255}
                        step={1}
                        className="flex-1"
                      />
                      <div className="w-12 text-center text-sm font-mono">
                        {motor1}
                      </div>
                    </div>
                    <Input
                      type="number"
                      min="-255"
                      max="255"
                      value={motor1}
                      onChange={(e) => setMotor1(Number(e.target.value))}
                      placeholder="0"
                      className="text-center"
                    />
                  </div>
                </div>
                
                <div className="space-y-3">
                  <Label>Motor 2</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-4">
                      <Slider
                        value={[motor2]}
                        onValueChange={(value) => setMotor2(value[0])}
                        min={-255}
                        max={255}
                        step={1}
                        className="flex-1"
                      />
                      <div className="w-12 text-center text-sm font-mono">
                        {motor2}
                      </div>
                    </div>
                    <Input
                      type="number"
                      min="-255"
                      max="255"
                      value={motor2}
                      onChange={(e) => setMotor2(Number(e.target.value))}
                      placeholder="0"
                      className="text-center"
                    />
                  </div>
                </div>
                
                <div className="space-y-3">
                  <Label>Motor 3</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-4">
                      <Slider
                        value={[motor3]}
                        onValueChange={(value) => setMotor3(value[0])}
                        min={-255}
                        max={255}
                        step={1}
                        className="flex-1"
                      />
                      <div className="w-12 text-center text-sm font-mono">
                        {motor3}
                      </div>
                    </div>
                    <Input
                      type="number"
                      min="-255"
                      max="255"
                      value={motor3}
                      onChange={(e) => setMotor3(Number(e.target.value))}
                      placeholder="0"
                      className="text-center"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Button onClick={goCommand} size="lg" className="w-full">
                  GO
                </Button>
                <Button onClick={stopCommand} size="lg" variant="destructive" className="w-full">
                  STOP
                </Button>
              </div>
            </div>
          )}

          {isConnected && (
            <div className="text-sm text-muted-foreground text-center">
              <p>Controle direto dos motores</p>
              <p>Digite valores de -255 a 255 para cada motor</p>
            </div>
          )}

          <div className="text-xs text-muted-foreground space-y-1">
            <p><strong>Arquivos criados:</strong></p>
            <p>• robot_control.py - Interface Python</p>
            <p>• arduino_robot_control.ino - Código Arduino</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Index;
