import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Camera, Video, VideoOff } from "lucide-react";

interface CameraStatusProps {
  lidarOnline?: boolean;
  d435Online?: boolean;
  yoloEnabled?: boolean;
  trackingMode?: string;
}

export const CameraStatus = ({ 
  lidarOnline = false, 
  d435Online = false,
  yoloEnabled = false,
  trackingMode = "basic"
}: CameraStatusProps) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Camera className="h-5 w-5" />
          Status das Câmeras
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Status do Sistema */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                yoloEnabled ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              }`} />
              <span className="font-medium">Sistema de Tracking</span>
            </div>
            <Badge variant={yoloEnabled ? "default" : "secondary"}>
              {yoloEnabled ? "ATIVO" : "INATIVO"}
            </Badge>
          </div>

          {/* LiDAR L515 */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              {lidarOnline ? (
                <Video className="h-4 w-4 text-green-500" />
              ) : (
                <VideoOff className="h-4 w-4 text-gray-400" />
              )}
              <span className="font-medium">LiDAR L515</span>
            </div>
            <Badge variant={lidarOnline ? "default" : "secondary"}>
              {lidarOnline ? "ONLINE" : "OFFLINE"}
            </Badge>
          </div>

          {/* Câmera D435 */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              {d435Online ? (
                <Video className="h-4 w-4 text-green-500" />
              ) : (
                <VideoOff className="h-4 w-4 text-gray-400" />
              )}
              <span className="font-medium">Câmera D435</span>
            </div>
            <Badge variant={d435Online ? "default" : "secondary"}>
              {d435Online ? "ONLINE" : "OFFLINE"}
            </Badge>
          </div>

          {/* Modo de Tracking */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <span className="font-medium text-sm">Modo de Tracking</span>
            <Badge variant="outline">
              {trackingMode === "yolo" ? "YOLO" : 
               trackingMode === "basic" ? "Básico" : 
               trackingMode === "error" ? "Erro" : "Aguardando"}
            </Badge>
          </div>

          {/* Mensagem de Status */}
          {!yoloEnabled && (
            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm">
              <p className="text-blue-600 dark:text-blue-400">
                💡 Ative o "YOLO Tracking" acima para iniciar as câmeras
              </p>
            </div>
          )}

          {yoloEnabled && !lidarOnline && !d435Online && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-sm">
              <p className="text-yellow-600 dark:text-yellow-400">
                ⚠️ Nenhuma câmera detectada. Verifique as conexões USB.
              </p>
            </div>
          )}

          {yoloEnabled && (lidarOnline || d435Online) && (
            <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-sm">
              <p className="text-green-600 dark:text-green-400">
                ✓ {lidarOnline && d435Online ? "Ambas" : "Uma"} câmera(s) operacional(is)
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
