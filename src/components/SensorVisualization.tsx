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

interface TrackedObject {
  id: number;
  bbox: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  centroid: {
    x: number;
    y: number;
  };
  area: number;
  depth?: number;
}

interface SensorVisualizationProps {
  cameraImage?: string;
  groundObstacles?: ObstacleData;
  heightObstacles?: ObstacleData;
  trackedObjects?: TrackedObject[];
}

export const SensorVisualization = ({ cameraImage, groundObstacles, heightObstacles, trackedObjects }: SensorVisualizationProps) => {
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
      {/* Camera Feed with Object Tracking */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold">📹 Câmera D435 (Superior)</h3>
          <div className="flex items-center gap-2">
            {cameraImage ? (
              <Badge variant="default" className="gap-1">
                <CheckCircle className="w-3 h-3" />
                Ativa
              </Badge>
            ) : (
              <Badge variant="destructive" className="gap-1">
                <AlertCircle className="w-3 h-3" />
                Sem sinal
              </Badge>
            )}
            {trackedObjects && trackedObjects.length > 0 && (
              <Badge variant="secondary">{trackedObjects.length} objeto(s)</Badge>
            )}
          </div>
        </div>
        <p className="text-xs text-muted-foreground mb-3">Tracking de objetos em tempo real</p>
        <div className="aspect-video bg-secondary rounded-lg overflow-hidden relative">
          {cameraImage ? (
            <>
              <img 
                src={`data:image/jpeg;base64,${cameraImage}`} 
                alt="Camera D435 feed"
                className="w-full h-full object-cover"
              />
              {/* Overlay com objetos rastreados */}
              <svg 
                className="absolute inset-0 w-full h-full pointer-events-none"
                viewBox="0 0 640 480"
                preserveAspectRatio="none"
              >
                {trackedObjects?.map((obj) => (
                  <g key={obj.id}>
                    {/* Bounding box */}
                    <rect
                      x={obj.bbox.x}
                      y={obj.bbox.y}
                      width={obj.bbox.w}
                      height={obj.bbox.h}
                      fill="none"
                      stroke="hsl(var(--primary))"
                      strokeWidth="2"
                      className="animate-pulse"
                    />
                    {/* Label */}
                    <rect
                      x={obj.bbox.x}
                      y={obj.bbox.y - 24}
                      width={obj.depth ? 90 : 50}
                      height="20"
                      fill="hsl(var(--primary))"
                      opacity="0.9"
                    />
                    <text
                      x={obj.bbox.x + 5}
                      y={obj.bbox.y - 10}
                      fill="hsl(var(--primary-foreground))"
                      fontSize="12"
                      fontWeight="bold"
                    >
                      ID:{obj.id} {obj.depth && `${obj.depth.toFixed(2)}m`}
                    </text>
                    {/* Centroide */}
                    <circle
                      cx={obj.centroid.x}
                      cy={obj.centroid.y}
                      r="3"
                      fill="hsl(var(--accent))"
                    />
                  </g>
                ))}
              </svg>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3 p-6">
              <AlertCircle className="w-16 h-16 opacity-50" />
              <div className="text-center space-y-2">
                <p className="font-semibold text-lg">Câmera D435 Offline</p>
                <div className="text-xs space-y-1 max-w-md">
                  <p>A câmera não está enviando dados. Verifique:</p>
                  <ul className="list-disc list-inside text-left space-y-1 mt-2">
                    <li>Câmera D435 está conectada via USB</li>
                    <li>Script <code className="bg-muted px-1 py-0.5 rounded">robot_autonomous_control.py</code> está rodando</li>
                    <li>Verifique erros no terminal Python</li>
                    <li>Teste com: <code className="bg-muted px-1 py-0.5 rounded">realsense-viewer</code></li>
                  </ul>
                </div>
              </div>
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
