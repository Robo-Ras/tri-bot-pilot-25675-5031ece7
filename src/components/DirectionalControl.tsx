import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Square } from 'lucide-react';

interface DirectionalControlProps {
  onSendCommand: (m1: number, m2: number, m3: number) => void;
}

const DirectionalControl = ({ onSendCommand }: DirectionalControlProps) => {
  const moveForward = () => onSendCommand(0, -180, 180);
  const moveBackward = () => onSendCommand(0, 180, -180);
  const moveRight = () => onSendCommand(-180, -180, 180);
  const moveLeft = () => onSendCommand(180, -180, 180);
  const stop = () => onSendCommand(0, 0, 0);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key.toLowerCase()) {
        case 'w':
        case 'arrowup':
          moveForward();
          break;
        case 's':
        case 'arrowdown':
          moveBackward();
          break;
        case 'd':
        case 'arrowright':
          moveRight();
          break;
        case 'a':
        case 'arrowleft':
          moveLeft();
          break;
        case ' ':
          stop();
          event.preventDefault();
          break;
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      if (['w', 's', 'a', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(event.key.toLowerCase())) {
        stop();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h3 className="text-lg font-semibold">Controle Direcional</h3>
        <p className="text-sm text-muted-foreground">
          Use WASD, setas ou clique nos botões. Espaço para parar.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4 max-w-xs mx-auto">
        <div></div>
        <Button
          onMouseDown={moveForward}
          onMouseUp={stop}
          onMouseLeave={stop}
          size="lg"
          className="aspect-square p-0"
        >
          <ArrowUp size={24} />
        </Button>
        <div></div>

        <Button
          onMouseDown={moveLeft}
          onMouseUp={stop}
          onMouseLeave={stop}
          size="lg"
          className="aspect-square p-0"
        >
          <ArrowLeft size={24} />
        </Button>
        <Button
          onClick={stop}
          size="lg"
          variant="destructive"
          className="aspect-square p-0"
        >
          <Square size={24} />
        </Button>
        <Button
          onMouseDown={moveRight}
          onMouseUp={stop}
          onMouseLeave={stop}
          size="lg"
          className="aspect-square p-0"
        >
          <ArrowRight size={24} />
        </Button>

        <div></div>
        <Button
          onMouseDown={moveBackward}
          onMouseUp={stop}
          onMouseLeave={stop}
          size="lg"
          className="aspect-square p-0"
        >
          <ArrowDown size={24} />
        </Button>
        <div></div>
      </div>

      <div className="text-xs text-muted-foreground text-center space-y-1">
        <p><strong>Comandos:</strong></p>
        <p>Frente: M1=0, M2=-180, M3=180</p>
        <p>Trás: M1=0, M2=180, M3=-180</p>
        <p>Direita: M1=-180, M2=-180, M3=180</p>
        <p>Esquerda: M1=180, M2=-180, M3=180</p>
      </div>
    </div>
  );
};

export default DirectionalControl;