import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface DetectedObject {
  label: string;
  distance: number;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;
}

interface ObjectDetectionVisualizationProps {
  cameraImage?: string;
  detectedObjects?: DetectedObject[];
}

export const ObjectDetectionVisualization = ({
  cameraImage,
  detectedObjects = []
}: ObjectDetectionVisualizationProps) => {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>🎯</span>
          Detecção de Objetos (MediaPipe)
          <Badge variant="secondary" className="ml-auto">
            {detectedObjects.length} objetos
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Visualização da Câmera com Bounding Boxes */}
        <div className="relative aspect-video bg-muted rounded-lg overflow-hidden">
          {cameraImage ? (
            <>
              <img
                src={`data:image/jpeg;base64,${cameraImage}`}
                alt="Camera Feed"
                className="w-full h-full object-contain"
              />
              {/* SVG Overlay para Bounding Boxes */}
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none"
                viewBox="0 0 640 480"
                preserveAspectRatio="xMidYMid meet"
              >
                {detectedObjects.map((obj, idx) => (
                  <g key={idx}>
                    {/* Bounding Box */}
                    <rect
                      x={obj.bbox.x}
                      y={obj.bbox.y}
                      width={obj.bbox.width}
                      height={obj.bbox.height}
                      fill="none"
                      stroke="#00ff00"
                      strokeWidth="2"
                    />
                    {/* Label Background */}
                    <rect
                      x={obj.bbox.x}
                      y={obj.bbox.y - 25}
                      width={150}
                      height={22}
                      fill="#00ff00"
                      fillOpacity="0.8"
                    />
                    {/* Label Text */}
                    <text
                      x={obj.bbox.x + 5}
                      y={obj.bbox.y - 8}
                      fill="black"
                      fontSize="14"
                      fontWeight="bold"
                    >
                      {obj.label} {obj.distance.toFixed(2)}m
                    </text>
                  </g>
                ))}
              </svg>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Aguardando feed da câmera L515...
            </div>
          )}
        </div>

        {/* Lista de Objetos Detectados */}
        {detectedObjects.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Objetos Detectados:</h4>
            <div className="grid gap-2">
              {detectedObjects.map((obj, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-muted rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{idx + 1}</Badge>
                    <div>
                      <p className="font-medium">{obj.label}</p>
                      <p className="text-xs text-muted-foreground">
                        Confiança: {(obj.confidence * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-primary">
                      {obj.distance.toFixed(2)}m
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {obj.bbox.width}×{obj.bbox.height}px
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Legenda */}
        <div className="text-xs text-muted-foreground border-t pt-3">
          <p className="font-semibold mb-1">💡 Informações:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Modelo: EfficientDet Lite0 (MediaPipe)</li>
            <li>Resolução: 640×480 (cor) / 320×240 (profundidade)</li>
            <li>Taxa: 30 FPS</li>
            <li>Máximo: 5 objetos simultâneos</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};
