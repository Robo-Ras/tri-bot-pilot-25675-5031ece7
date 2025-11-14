#!/bin/bash

echo "================================"
echo "Corrigindo permissões RealSense"
echo "================================"

# 1. Baixar e instalar regras udev
echo ""
echo "1. Instalando regras udev..."
sudo wget -O /etc/udev/rules.d/99-realsense-libusb.rules https://raw.githubusercontent.com/IntelRealSense/librealsense/master/config/99-realsense-libusb.rules

if [ ! -f /etc/udev/rules.d/99-realsense-libusb.rules ]; then
    echo "❌ Falha ao baixar regras. Criando manualmente..."
    sudo tee /etc/udev/rules.d/99-realsense-libusb.rules > /dev/null <<'EOF'
# Intel RealSense D400 series
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b3a", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b37", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b07", MODE="0666", GROUP="plugdev"

# Intel RealSense L500 series
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b64", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b3d", MODE="0666", GROUP="plugdev"
EOF
fi

# 2. Adicionar usuário ao grupo plugdev
echo ""
echo "2. Adicionando usuário ao grupo plugdev..."
sudo usermod -aG plugdev $USER

# 3. Recarregar regras udev
echo ""
echo "3. Recarregando regras udev..."
sudo udevadm control --reload-rules
sudo udevadm trigger

# 4. Verificar versão pyrealsense2
echo ""
echo "4. Verificando pyrealsense2..."
python3 -c "import pyrealsense2 as rs; print(f'pyrealsense2 versão: {rs.__version__}')" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ pyrealsense2 não encontrado. Instalando..."
    pip3 install pyrealsense2
fi

# 5. Testar detecção
echo ""
echo "5. Testando detecção de dispositivos..."
python3 << 'PYEOF'
import pyrealsense2 as rs
ctx = rs.context()
devices = ctx.query_devices()
print(f"\n✓ Dispositivos encontrados: {len(devices)}")
for dev in devices:
    print(f"  - {dev.get_info(rs.camera_info.name)} (Serial: {dev.get_info(rs.camera_info.serial_number)})")
PYEOF

echo ""
echo "================================"
echo "✓ Processo concluído!"
echo "================================"
echo ""
echo "IMPORTANTE: Você precisa DESCONECTAR e RECONECTAR os sensores RealSense"
echo "          ou REINICIAR o computador para aplicar as mudanças."
echo ""
echo "Depois, execute: python3 robot_autonomous_control.py"
