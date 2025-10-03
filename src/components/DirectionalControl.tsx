import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Square } from 'lucide-react';

interface DirectionalControlProps {
  onSendCommand: (m1: number, m2: number, m3: number) => void;
}

const DirectionalControl = ({ onSendCommand }: DirectionalControlProps) => {
  const [speed, setSpeed] = useState(180);

  const moveForward = () => onSendCommand(0, -speed, speed);
  const moveBackward = () => onSendCommand(0, speed, -speed);
  const moveRight = () => onSendCommand(-speed, -speed, speed);
  const moveLeft = () => onSendCommand(speed, -speed, speed);
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
  }, [speed]);

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h3 className="text-lg font-semibold">Controle Direcional</h3>
        <p className="text-sm text-muted-foreground">
          Use WASD, setas ou clique nos botões. Espaço para parar.
        </p>
      </div>

      <div className="space-y-4 max-w-md mx-auto">
        <div className="space-y-2">
          <label className="text-sm font-medium">Velocidade: {speed}</label>
          <div className="flex gap-4 items-center">
            <Slider
              value={[speed]}
              onValueChange={(value) => setSpeed(value[0])}
              min={0}
              max={255}
              step={1}
              className="flex-1"
            />
            <Input
              type="number"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              min={0}
              max={255}
              className="w-20"
            />
          </div>
        </div>
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
        <p>Frente: M1=0, M2=-{speed}, M3={speed}</p>
        <p>Trás: M1=0, M2={speed}, M3=-{speed}</p>
        <p>Direita: M1=-{speed}, M2=-{speed}, M3={speed}</p>
        <p>Esquerda: M1={speed}, M2=-{speed}, M3={speed}</p>
      </div>
    </div>
  );
};

export default DirectionalControl;