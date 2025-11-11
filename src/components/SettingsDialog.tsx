import { Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { SerialConnectionControl } from "@/components/SerialConnectionControl";

interface SettingsDialogProps {
  wsRef: React.RefObject<WebSocket | null>;
  isArduinoConnected: boolean;
  availablePorts: string[];
  onConnectionChange: (connected: boolean) => void;
}

export const SettingsDialog = ({
  wsRef,
  isArduinoConnected,
  availablePorts,
  onConnectionChange,
}: SettingsDialogProps) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="icon">
          <Settings className="h-5 w-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Configurações</DialogTitle>
          <DialogDescription>
            Configure a conexão com o Arduino e outras opções do sistema
          </DialogDescription>
        </DialogHeader>
        <div className="mt-4">
          <SerialConnectionControl
            wsRef={wsRef}
            isArduinoConnected={isArduinoConnected}
            availablePorts={availablePorts}
            onConnectionChange={onConnectionChange}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};
