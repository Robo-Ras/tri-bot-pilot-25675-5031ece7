import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Smartphone } from 'lucide-react';

export const TabletQRCodeDialog = () => {
  const [notebookIp, setNotebookIp] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');

  const handleGenerateQRCode = () => {
    if (notebookIp) {
      const baseUrl = window.location.origin;
      const url = `${baseUrl}/robot-face?ip=${notebookIp}`;
      setQrCodeUrl(url);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Smartphone className="w-4 h-4" />
          QR Code para Tablet
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Conectar Tablet via QR Code</DialogTitle>
          <DialogDescription>
            Digite o IP do notebook e escaneie o QR code no tablet
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="notebook-ip">IP do Notebook</Label>
            <div className="flex gap-2">
              <Input
                id="notebook-ip"
                placeholder="Ex: 10.42.0.1 ou 192.168.1.100"
                value={notebookIp}
                onChange={(e) => setNotebookIp(e.target.value)}
              />
              <Button onClick={handleGenerateQRCode}>Gerar</Button>
            </div>
          </div>

          {qrCodeUrl && (
            <div className="flex flex-col items-center gap-4 p-4 border rounded-lg bg-background">
              <QRCodeSVG 
                value={qrCodeUrl} 
                size={200}
                level="H"
                includeMargin={true}
              />
              <p className="text-sm text-muted-foreground text-center break-all">
                {qrCodeUrl}
              </p>
              <p className="text-xs text-muted-foreground text-center">
                Escaneie este QR code no tablet para conectar automaticamente
              </p>
            </div>
          )}

          <div className="text-xs text-muted-foreground space-y-1">
            <p>💡 <strong>Dica:</strong> Para encontrar o IP do notebook:</p>
            <ul className="list-disc list-inside ml-2 space-y-1">
              <li>Hotspot: geralmente 10.42.0.1</li>
              <li>Wi-Fi: use <code className="bg-muted px-1 rounded">hostname -I</code></li>
            </ul>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
