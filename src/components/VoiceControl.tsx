import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Mic, MicOff } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

interface VoiceControlProps {
  onCommand: (command: string) => void;
  isConnected: boolean;
}

const VoiceControl = ({ onCommand, isConnected }: VoiceControlProps) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [recognition, setRecognition] = useState<any>(null);
  const { toast } = useToast();

  useEffect(() => {
    // Check if browser supports Speech Recognition
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.error('❌ Navegador não suporta reconhecimento de voz');
      toast({
        title: "Não suportado",
        description: "Seu navegador não suporta reconhecimento de voz. Use Chrome ou Edge.",
        variant: "destructive"
      });
      return;
    }

    console.log('✓ Inicializando reconhecimento de voz contínuo...');
    const recognitionInstance = new SpeechRecognition();
    recognitionInstance.continuous = true;
    recognitionInstance.interimResults = false;
    recognitionInstance.lang = 'pt-BR';
    recognitionInstance.maxAlternatives = 1;

    recognitionInstance.onstart = () => {
      console.log('🎤 Reconhecimento de voz iniciado (modo contínuo)');
    };

    recognitionInstance.onresult = (event: any) => {
      const lastResult = event.results[event.results.length - 1];
      if (lastResult.isFinal) {
        const transcriptText = lastResult[0].transcript.toLowerCase().trim();
        console.log('🎙️ Texto reconhecido:', transcriptText);
        setTranscript(transcriptText);
        processVoiceCommand(transcriptText);
      }
    };

    recognitionInstance.onerror = (event: any) => {
      console.error('❌ Erro no reconhecimento de voz:', event.error);
      if (event.error === 'no-speech') {
        // Ignorar erro de silêncio, é normal
        return;
      }
      if (event.error !== 'aborted') {
        setIsListening(false);
        toast({
          title: "Erro no reconhecimento",
          description: `Erro: ${event.error}`,
          variant: "destructive"
        });
      }
    };

    recognitionInstance.onend = () => {
      console.log('🔴 Reconhecimento finalizado');
      // Restart automatically if still listening
      if (isListening) {
        setTimeout(() => {
          try {
            console.log('♻️ Reiniciando reconhecimento automático...');
            recognitionInstance.start();
          } catch (e) {
            console.error('❌ Falha ao reiniciar:', e);
            setIsListening(false);
          }
        }, 200);
      }
    };

    setRecognition(recognitionInstance);

    return () => {
      console.log('🧹 Limpando reconhecimento de voz');
      if (recognitionInstance) {
        try {
          recognitionInstance.abort();
        } catch (e) {
          console.error('Erro ao parar recognition:', e);
        }
      }
    };
  }, []);

  const processVoiceCommand = (text: string) => {
    const normalized = text.toLowerCase().trim();
    
    // Command mapping - APENAS UM COMANDO POR DIREÇÃO
    const commands: { [key: string]: string } = {
      'frente': 'forward',
      'para trás': 'backward',
      'tras': 'backward',
      'esquerda': 'left',
      'direita': 'right',
      'parar': 'stop',
      'autônomo': 'autonomous',
      'autonomo': 'autonomous',
      'manual': 'manual'
    };

    // Check if any command matches
    for (const [phrase, command] of Object.entries(commands)) {
      if (normalized === phrase || normalized.includes(phrase)) {
        console.log('✓ Comando reconhecido:', phrase, '→', command);
        onCommand(command);
        toast({
          title: "✓ Comando executado",
          description: phrase,
        });
        // Limpa o transcript após 1 segundo
        setTimeout(() => setTranscript(''), 1000);
        return;
      }
    }
    
    console.log('✗ Comando não reconhecido:', normalized);
    // Não mostra erro para evitar spam de toasts
    setTimeout(() => setTranscript(''), 1000);
  };

  const toggleListening = () => {
    if (!recognition) {
      console.error('❌ Recognition não inicializado');
      toast({
        title: "Erro",
        description: "Sistema de voz não está disponível",
        variant: "destructive"
      });
      return;
    }

    if (isListening) {
      console.log('⏹️ Parando reconhecimento...');
      try {
        recognition.abort();
        setIsListening(false);
        setTranscript('');
      } catch (e) {
        console.error('Erro ao parar:', e);
      }
    } else {
      if (!isConnected) {
        toast({
          title: "Não conectado",
          description: "Conecte ao servidor Python primeiro",
          variant: "destructive"
        });
        return;
      }
      console.log('▶️ Iniciando reconhecimento...');
      try {
        recognition.start();
        setIsListening(true);
        toast({
          title: "Ouvindo",
          description: "Fale um comando agora",
        });
      } catch (e) {
        console.error('❌ Erro ao iniciar:', e);
        toast({
          title: "Erro",
          description: "Não foi possível iniciar o reconhecimento",
          variant: "destructive"
        });
      }
    }
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Controle por Voz</h3>
          <Badge variant={isListening ? "default" : "secondary"}>
            {isListening ? "Ouvindo..." : "Inativo"}
          </Badge>
        </div>

        <Button
          onClick={toggleListening}
          variant={isListening ? "destructive" : "default"}
          className="w-full"
          disabled={!recognition}
        >
          {isListening ? (
            <>
              <MicOff className="mr-2 h-4 w-4" />
              Parar de Ouvir
            </>
          ) : (
            <>
              <Mic className="mr-2 h-4 w-4" />
              Começar a Ouvir
            </>
          )}
        </Button>

        {transcript && (
          <div className="p-3 bg-muted rounded-md">
            <p className="text-sm text-muted-foreground">Reconhecendo:</p>
            <p className="font-medium">{transcript}</p>
          </div>
        )}

        <div className="text-xs text-muted-foreground space-y-1">
          <p className="font-semibold">Comandos disponíveis:</p>
          <ul className="list-disc list-inside space-y-0.5">
            <li><strong>Frente</strong></li>
            <li><strong>Para trás</strong> (ou "tras")</li>
            <li><strong>Esquerda</strong></li>
            <li><strong>Direita</strong></li>
            <li><strong>Parar</strong></li>
            <li><strong>Autônomo</strong></li>
            <li><strong>Manual</strong></li>
          </ul>
          <p className="text-xs mt-2 italic">💡 Modo contínuo: fale vários comandos seguidos</p>
        </div>
      </div>
    </Card>
  );
};

export default VoiceControl;
