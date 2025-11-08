import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle } from "lucide-react";

interface ObstacleData {
  type?: string;
  left: boolean;
  center: boolean;
  right: boolean;
  distances: {
    left: number;
    center: number;
    right: number;
  };
}

interface SensorVisualizationProps {
  cameraImage?: string;
  groundObstacles?: ObstacleData;
  heightObstacles?: ObstacleData;
}

export const SensorVisualization = ({ cameraImage, groundObstacles, heightObstacles }: SensorVisualizationProps) => {
  const renderObstacleSector = (sector: 'left' | 'center' | 'right', obstacles: ObstacleData | undefined) => {
    const sectorName = sector === 'left' ? 'Esquerda' : sector === 'center' ? 'Centro' : 'Direita';
    const hasObstacle = obstacles?.[sector];
    const distance = obstacles?.distances[sector];

    return (
      <div className={`p-3 rounded-lg border-2 transition-colors ${
        hasObstacle 
          ? 'border-destructive bg-destructive/10' 
          : 'border-border bg-secondary'
      }`}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium">{sectorName}</span>
          {hasObstacle ? (
            <AlertCircle className="w-4 h-4 text-destructive" />
          ) : (
            <CheckCircle className="w-4 h-4 text-primary" />
          )}
        </div>
        <div className="text-lg font-bold">
          {distance?.toFixed(2) ?? '--'}m
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Camera Feed */}
      <Card className="p-4">
        <h3 className="text-lg font-semibold mb-2">📹 Câmera D435 (Superior)</h3>
        <p className="text-xs text-muted-foreground mb-3">Detecta objetos altos</p>
        <div className="aspect-video bg-secondary rounded-lg overflow-hidden">
          {cameraImage ? (
            <img 
              src={`data:image/jpeg;base64,${cameraImage}`} 
              alt="Camera feed"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              Aguardando dados da câmera...
            </div>
          )}
        </div>
      </Card>

      {/* Ground Obstacles - LiDAR */}
      <Card className="p-4">
        <h3 className="text-lg font-semibold mb-2">🎯 LiDAR L515 (Inferior)</h3>
        <p className="text-xs text-muted-foreground mb-3">Obstáculos no chão</p>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {renderObstacleSector('left', groundObstacles)}
            {renderObstacleSector('center', groundObstacles)}
            {renderObstacleSector('right', groundObstacles)}
          </div>
          {groundObstacles && (
            <div className="text-center">
              <Badge variant={groundObstacles.left || groundObstacles.center || groundObstacles.right ? "destructive" : "default"}>
                {groundObstacles.left || groundObstacles.center || groundObstacles.right 
                  ? '⚠️ Obstáculos no Chão' 
                  : '✓ Chão Livre'}
              </Badge>
            </div>
          )}
        </div>
      </Card>

      {/* Height Obstacles - Camera */}
      <Card className="p-4">
        <h3 className="text-lg font-semibold mb-2">📏 Detecção de Altura</h3>
        <p className="text-xs text-muted-foreground mb-3">Objetos altos pela câmera</p>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {renderObstacleSector('left', heightObstacles)}
            {renderObstacleSector('center', heightObstacles)}
            {renderObstacleSector('right', heightObstacles)}
          </div>
          {heightObstacles && (
            <div className="text-center">
              <Badge variant={heightObstacles.left || heightObstacles.center || heightObstacles.right ? "destructive" : "default"}>
                {heightObstacles.left || heightObstacles.center || heightObstacles.right 
                  ? '⚠️ Objetos Altos' 
                  : '✓ Altura Livre'}
              </Badge>
            </div>
          )}
        </div>
      </Card>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <CheckCircle className="w-3 h-3 text-primary" />
          <span className="text-muted-foreground">Livre</span>
        </div>
        <div className="flex items-center gap-1">
          <AlertCircle className="w-3 h-3 text-destructive" />
          <span className="text-muted-foreground">Obstáculo</span>
        </div>
      </div>
    </div>
  );
};
