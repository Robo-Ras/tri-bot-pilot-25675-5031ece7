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
    recognitionInstance.continuous = false;
    recognitionInstance.interimResults = false;
    recognitionInstance.lang = 'pt-BR';
    recognitionInstance.maxAlternatives = 1;

    recognitionInstance.onresult = (event: any) => {
      const transcriptText = event.results[0][0].transcript.toLowerCase().trim();
      setTranscript(transcriptText);
      processVoiceCommand(transcriptText);
    };

    recognitionInstance.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setIsListening(false);
      }
    };

    recognitionInstance.onend = () => {
      if (isListening) {
        setTimeout(() => {
          try {
            recognitionInstance.start();
          } catch (e) {
            console.error('Failed to restart recognition:', e);
          }
        }, 100);
      }
    };

    setRecognition(recognitionInstance);

    return () => {
      if (recognitionInstance) {
        try {
          recognitionInstance.stop();
        } catch (e) {
          console.error('Error stopping recognition:', e);
        }
      }
    };
  }, [isListening]);

  const processVoiceCommand = (text: string) => {
    const normalized = text.toLowerCase().trim();
    
    // Command mapping - ordem importa, mais específicos primeiro
    const commands: { [key: string]: string } = {
      'para frente': 'forward',
      'frente': 'forward',
      'vá para frente': 'forward',
      'para trás': 'backward',
      'trás': 'backward',
      'tras': 'backward',
      'ré': 'backward',
      're': 'backward',
      'voltar': 'backward',
      'esquerda': 'left',
      'vire à esquerda': 'left',
      'virar esquerda': 'left',
      'direita': 'right',
      'vire à direita': 'right',
      'virar direita': 'right',
      'parar': 'stop',
      'pare': 'stop',
      'parado': 'stop',
      'modo autônomo': 'autonomous',
      'autônomo': 'autonomous',
      'autonomo': 'autonomous',
      'modo manual': 'manual',
      'manual': 'manual'
    };

    // Check if any command matches
    for (const [phrase, command] of Object.entries(commands)) {
      if (normalized.includes(phrase)) {
        console.log('✓ Comando reconhecido:', phrase, '→', command);
        onCommand(command);
        toast({
          title: "✓ Comando reconhecido",
          description: `"${phrase}" → ${command}`,
        });
        setTranscript('');
        return;
      }
    }
    
    console.log('✗ Comando não reconhecido:', normalized);
    toast({
      title: "Comando não reconhecido",
      description: `"${normalized}"`,
      variant: "destructive"
    });
    setTranscript('');
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
            <li><strong>Frente:</strong> "frente", "para frente"</li>
            <li><strong>Trás:</strong> "trás", "para trás", "ré", "voltar"</li>
            <li><strong>Esquerda:</strong> "esquerda", "virar esquerda"</li>
            <li><strong>Direita:</strong> "direita", "virar direita"</li>
            <li><strong>Parar:</strong> "parar", "pare"</li>
            <li><strong>Autônomo:</strong> "modo autônomo", "autônomo"</li>
            <li><strong>Manual:</strong> "modo manual", "manual"</li>
          </ul>
          <p className="text-xs mt-2 italic">💡 Fale de forma clara e pausada</p>
        </div>
      </div>
    </Card>
  );
};

export default VoiceControl;
