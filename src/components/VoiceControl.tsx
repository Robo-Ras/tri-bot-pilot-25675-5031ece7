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
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [micPermission, setMicPermission] = useState<'granted' | 'denied' | 'prompt'>('prompt');
  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number>(0);
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

  const startAudioMonitoring = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      
      analyserRef.current.fftSize = 256;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      const updateAudioLevel = () => {
        if (!analyserRef.current) return;
        
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        setAudioLevel(Math.min(100, (average / 255) * 200));
        
        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      };
      
      updateAudioLevel();
      console.log('✅ Monitoramento de áudio iniciado');
    } catch (error) {
      console.error('❌ Erro ao monitorar áudio:', error);
    }
  };

  const stopAudioMonitoring = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
    console.log('⏹️ Monitoramento de áudio parado');
  };

  const checkMicPermission = async () => {
    try {
      const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      setMicPermission(result.state as 'granted' | 'denied' | 'prompt');
      console.log('🎤 Permissão do microfone:', result.state);
    } catch (error) {
      console.log('ℹ️ Não foi possível verificar permissão automaticamente');
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
      stopAudioMonitoring();
      toast({
        title: "Reconhecimento Desativado",
        description: "Comandos de voz desativados",
      });
    } else {
      try {
        console.log('▶️ Solicitando permissão do microfone...');
        
        await startAudioMonitoring();
        setMicPermission('granted');
        console.log('✅ Permissão concedida');
        
        console.log('▶️ Iniciando reconhecimento...');
        recognitionRef.current?.start();
        setIsListening(true);
        toast({
          title: "Reconhecimento Ativado",
          description: "🎤 Comandos: frente, trás, direita, esquerda, parar, modo autônomo",
        });
      } catch (error) {
        console.error('❌ Erro ao acessar microfone:', error);
        setMicPermission('denied');
        toast({
          title: "Erro de Permissão",
          description: "Permita o acesso ao microfone nas configurações do navegador",
          variant: "destructive",
        });
      }
    }
  };

  useEffect(() => {
    checkMicPermission();
    return () => {
      stopAudioMonitoring();
    };
  }, []);

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
        
        {/* Área de feedback - mostra sempre quando conectado */}
        {isConnected && (
          <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Status:</span>
              <span className={`text-sm font-medium ${isListening ? "text-green-500" : "text-muted-foreground"}`}>
                {isListening ? "🎤 Ativo" : "⏸️ Inativo"}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Microfone:</span>
              <span className={`text-sm font-medium ${
                micPermission === 'granted' ? "text-green-500" : 
                micPermission === 'denied' ? "text-red-500" : 
                "text-yellow-500"
              }`}>
                {micPermission === 'granted' ? '✅ Permitido' : 
                 micPermission === 'denied' ? '❌ Negado - Verifique configurações do navegador' : 
                 '⚠️ Aguardando permissão'}
              </span>
            </div>
            
            {isListening && (
              <div className="space-y-2 pt-2 border-t border-border">
                <div>
                  <span className="text-sm text-muted-foreground">Nível de áudio:</span>
                  <div className="mt-1.5 h-3 bg-background rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-100"
                      style={{ width: `${audioLevel}%` }}
                    />
                  </div>
                  {audioLevel < 5 && (
                    <p className="text-xs text-yellow-500 mt-1.5">
                      ⚠️ Nenhum áudio detectado - fale mais alto ou verifique seu microfone
                    </p>
                  )}
                  {audioLevel >= 5 && (
                    <p className="text-xs text-green-500 mt-1.5">
                      ✅ Áudio sendo detectado
                    </p>
                  )}
                </div>
              </div>
            )}
            
            <div className="space-y-2 pt-2 border-t border-border">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Reconhecido agora:</p>
                <p className="text-sm font-mono bg-background/50 p-2 rounded min-h-[2rem]">
                  {transcript || '---'}
                </p>
              </div>
              
              {lastCommand && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Comando executado:</p>
                  <p className="text-sm font-semibold text-primary bg-background/50 p-2 rounded">
                    {lastCommand}
                  </p>
                </div>
              )}
            </div>
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
