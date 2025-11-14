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
      toast({
        title: "Não suportado",
        description: "Seu navegador não suporta reconhecimento de voz",
        variant: "destructive"
      });
      return;
    }

    const recognitionInstance = new SpeechRecognition();
    recognitionInstance.continuous = true;
    recognitionInstance.interimResults = true;
    recognitionInstance.lang = 'pt-BR'; // Português do Brasil

    recognitionInstance.onresult = (event: any) => {
      const current = event.resultIndex;
      const transcriptText = event.results[current][0].transcript.toLowerCase().trim();
      
      setTranscript(transcriptText);

      // Only process final results
      if (event.results[current].isFinal) {
        processVoiceCommand(transcriptText);
      }
    };

    recognitionInstance.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
    };

    recognitionInstance.onend = () => {
      if (isListening) {
        recognitionInstance.start();
      }
    };

    setRecognition(recognitionInstance);

    return () => {
      if (recognitionInstance) {
        recognitionInstance.stop();
      }
    };
  }, []);

  const processVoiceCommand = (text: string) => {
    const normalized = text.toLowerCase();
    
    // Command mapping
    const commands: { [key: string]: string } = {
      'frente': 'forward',
      'para frente': 'forward',
      'trás': 'backward',
      'para trás': 'backward',
      'ré': 'backward',
      'esquerda': 'left',
      'direita': 'right',
      'parar': 'stop',
      'pare': 'stop',
      'modo autônomo': 'autonomous',
      'autônomo': 'autonomous',
      'modo manual': 'manual',
      'manual': 'manual'
    };

    // Check if any command matches
    for (const [phrase, command] of Object.entries(commands)) {
      if (normalized.includes(phrase)) {
        onCommand(command);
        toast({
          title: "Comando reconhecido",
          description: `${phrase} → ${command}`,
        });
        setTranscript('');
        return;
      }
    }
  };

  const toggleListening = () => {
    if (!recognition) return;

    if (isListening) {
      recognition.stop();
      setIsListening(false);
      setTranscript('');
    } else {
      if (!isConnected) {
        toast({
          title: "Não conectado",
          description: "Conecte ao servidor Python primeiro",
          variant: "destructive"
        });
        return;
      }
      recognition.start();
      setIsListening(true);
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
            <li>"frente" ou "para frente"</li>
            <li>"trás", "para trás" ou "ré"</li>
            <li>"esquerda"</li>
            <li>"direita"</li>
            <li>"parar" ou "pare"</li>
            <li>"modo autônomo" ou "autônomo"</li>
            <li>"modo manual" ou "manual"</li>
          </ul>
        </div>
      </div>
    </Card>
  );
};

export default VoiceControl;
