import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Mic, MicOff } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface VoiceControlProps {
  onSendCommand: (m1: number, m2: number, m3: number) => void;
  onToggleAutonomous: (enabled: boolean) => void;
  isConnected: boolean;
}

const VoiceControl = ({ onSendCommand, onToggleAutonomous, isConnected }: VoiceControlProps) => {
  const [isListening, setIsListening] = useState(false);
  const [lastCommand, setLastCommand] = useState<string>('');
  const [transcript, setTranscript] = useState<string>('');
  const recognitionRef = useRef<any>(null);
  const { toast } = useToast();

  useEffect(() => {
    console.log('🎙️ Inicializando Web Speech API...');
    
    // Verificar se o navegador suporta Web Speech API
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.error('❌ Navegador não suporta Web Speech API');
      toast({
        title: "Navegador não suportado",
        description: "Seu navegador não suporta reconhecimento de voz. Use Chrome ou Edge.",
        variant: "destructive",
      });
      return;
    }

    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'pt-BR';
    recognition.maxAlternatives = 1;

    console.log('✅ Web Speech API configurada:', {
      continuous: recognition.continuous,
      interimResults: recognition.interimResults,
      lang: recognition.lang
    });

    recognition.onstart = () => {
      console.log('🎤 Reconhecimento de voz INICIADO');
    };

    recognition.onresult = (event: any) => {
      const current = event.resultIndex;
      const transcript = event.results[current][0].transcript.toLowerCase().trim();
      const confidence = event.results[current][0].confidence;
      
      console.log('📝 Transcrição:', transcript, '| Confiança:', confidence);
      setTranscript(transcript);

      // Só processar comandos quando for resultado final
      if (event.results[current].isFinal) {
        console.log('✅ Resultado final:', transcript);
        processCommand(transcript);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('❌ Erro no reconhecimento de voz:', event.error);
      if (event.error === 'no-speech') {
        console.log('ℹ️ Nenhuma fala detectada (normal)');
        return;
      }
      if (event.error === 'not-allowed') {
        toast({
          title: "Permissão Negada",
          description: "Permita o acesso ao microfone nas configurações do navegador",
          variant: "destructive",
        });
        setIsListening(false);
        return;
      }
      toast({
        title: "Erro no reconhecimento",
        description: `Erro: ${event.error}`,
        variant: "destructive",
      });
    };

    recognition.onend = () => {
      console.log('⏹️ Reconhecimento de voz FINALIZADO');
      // Reiniciar automaticamente se ainda estiver no modo listening
      if (isListening) {
        console.log('🔄 Reiniciando reconhecimento...');
        try {
          recognition.start();
        } catch (error) {
          console.error('❌ Erro ao reiniciar:', error);
          setIsListening(false);
        }
      }
    };

    recognitionRef.current = recognition;

    return () => {
      console.log('🧹 Limpando reconhecimento de voz');
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [isListening]);

  const processCommand = (command: string) => {
    console.log('Processando comando:', command);
    
    const SPEED = 60;

    // Comandos de movimento
    if (command.includes('frente') || command.includes('para frente')) {
      onSendCommand(-SPEED, 0, SPEED);
      setLastCommand('Frente');
      toast({ title: "Comando de Voz", description: "Movendo para frente" });
    } 
    else if (command.includes('trás') || command.includes('para trás') || command.includes('tras')) {
      onSendCommand(SPEED, 0, -SPEED);
      setLastCommand('Trás');
      toast({ title: "Comando de Voz", description: "Movendo para trás" });
    } 
    else if (command.includes('direita') || command.includes('para direita')) {
      onSendCommand(0, SPEED, -SPEED);
      setLastCommand('Direita');
      toast({ title: "Comando de Voz", description: "Movendo para direita" });
    } 
    else if (command.includes('esquerda') || command.includes('para esquerda')) {
      onSendCommand(0, -SPEED, SPEED);
      setLastCommand('Esquerda');
      toast({ title: "Comando de Voz", description: "Movendo para esquerda" });
    } 
    else if (command.includes('parar') || command.includes('pare')) {
      onSendCommand(0, 0, 0);
      setLastCommand('Parar');
      toast({ title: "Comando de Voz", description: "Robô parado" });
    }
    // Comando de modo autônomo
    else if (command.includes('autônomo') || command.includes('autonomo') || 
             command.includes('modo autônomo') || command.includes('modo autonomo')) {
      onToggleAutonomous(true);
      setLastCommand('Modo Autônomo Ativado');
      toast({ title: "Comando de Voz", description: "Modo autônomo ativado" });
    }
    else if (command.includes('manual') || command.includes('modo manual')) {
      onToggleAutonomous(false);
      setLastCommand('Modo Manual Ativado');
      toast({ title: "Comando de Voz", description: "Modo manual ativado" });
    }
  };

  const toggleListening = async () => {
    console.log('🎤 Toggle listening. Estado atual:', isListening, '| Conectado:', isConnected);
    
    if (!isConnected) {
      toast({
        title: "Robô Desconectado",
        description: "Conecte-se ao robô antes de usar comandos de voz",
        variant: "destructive",
      });
      return;
    }

    if (isListening) {
      console.log('🛑 Desativando reconhecimento...');
      recognitionRef.current?.stop();
      setIsListening(false);
      setTranscript('');
      toast({
        title: "Reconhecimento Desativado",
        description: "Comandos de voz desativados",
      });
    } else {
      try {
        console.log('▶️ Solicitando permissão do microfone...');
        
        // Solicitar permissão do microfone primeiro
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('✅ Permissão concedida');
        stream.getTracks().forEach(track => track.stop()); // Liberar stream
        
        console.log('▶️ Iniciando reconhecimento...');
        recognitionRef.current?.start();
        setIsListening(true);
        toast({
          title: "Reconhecimento Ativado",
          description: "🎤 Comandos: frente, trás, direita, esquerda, parar, modo autônomo",
        });
      } catch (error) {
        console.error('❌ Erro ao acessar microfone:', error);
        toast({
          title: "Erro de Permissão",
          description: "Permita o acesso ao microfone nas configurações do navegador",
          variant: "destructive",
        });
      }
    }
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Controle por Voz</h3>
            <p className="text-sm text-muted-foreground">
              Comandos: frente, trás, direita, esquerda, parar, modo autônomo
            </p>
          </div>
          <Button
            onClick={toggleListening}
            size="lg"
            variant={isListening ? 'default' : 'outline'}
            className="gap-2"
            disabled={!isConnected}
          >
            {isListening ? (
              <>
                <Mic className="h-5 w-5" />
                Escutando...
              </>
            ) : (
              <>
                <MicOff className="h-5 w-5" />
                Ativar Voz
              </>
            )}
          </Button>
        </div>

        {isListening && (
          <div className="space-y-2">
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm text-muted-foreground">Ouvindo:</p>
              <p className="text-base font-medium">{transcript || 'Aguardando comando...'}</p>
            </div>
            {lastCommand && (
              <div className="p-3 bg-primary/10 rounded-md">
                <p className="text-sm text-muted-foreground">Último comando executado:</p>
                <p className="text-base font-semibold text-primary">{lastCommand}</p>
              </div>
            )}
          </div>
        )}

        {!isConnected && (
          <div className="p-3 bg-destructive/10 rounded-md">
            <p className="text-sm text-destructive">
              Conecte-se ao servidor Python para usar comandos de voz
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};

export default VoiceControl;
