#!/usr/bin/env python3
"""
Script de Diagnóstico - Intel RealSense L515
Verifica se o LiDAR L515 está conectado e funcionando
"""

import pyrealsense2 as rs
import sys

def check_l515():
    """Verifica se o L515 está conectado e acessível"""
    
    print("="*70)
    print("🔍 DIAGNÓSTICO DO INTEL REALSENSE L515")
    print("="*70)
    
    # 1. Verifica contexto RealSense
    print("\n[1/4] Verificando SDK RealSense...")
    try:
        ctx = rs.context()
        print("    ✓ SDK RealSense carregado com sucesso")
    except Exception as e:
        print(f"    ✗ ERRO: Não foi possível carregar SDK RealSense")
        print(f"    Detalhes: {e}")
        return False
    
    # 2. Lista dispositivos conectados
    print("\n[2/4] Buscando dispositivos RealSense conectados...")
    devices = ctx.query_devices()
    
    if len(devices) == 0:
        print("    ✗ NENHUM dispositivo RealSense encontrado!")
        print("\n📋 TROUBLESHOOTING:")
        print("    1. Verifique se o L515 está conectado via USB 3.0")
        print("    2. Execute: lsusb | grep Intel")
        print("    3. Verifique permissões: ls -la /dev/video*")
        print("    4. Tente outro cabo ou porta USB")
        print("    5. Reinicie o sensor (desconecte e reconecte)")
        return False
    
    print(f"    ✓ {len(devices)} dispositivo(s) encontrado(s)")
    
    # 3. Identifica cada dispositivo
    print("\n[3/4] Identificando dispositivos...")
    l515_found = False
    l515_device = None
    
    for i, dev in enumerate(devices):
        try:
            name = dev.get_info(rs.camera_info.name)
            serial = dev.get_info(rs.camera_info.serial_number)
            firmware = dev.get_info(rs.camera_info.firmware_version)
            product_line = dev.get_info(rs.camera_info.product_line)
            usb_type = dev.get_info(rs.camera_info.usb_type_descriptor)
            
            print(f"\n    📷 Dispositivo #{i+1}:")
            print(f"       Nome: {name}")
            print(f"       Serial: {serial}")
            print(f"       Firmware: {firmware}")
            print(f"       Linha de Produto: {product_line}")
            print(f"       USB: {usb_type}")
            
            # Verifica se é L515
            name_upper = name.upper()
            product_upper = product_line.upper()
            
            if 'L515' in name_upper or 'L515' in product_upper or 'L5' in product_upper:
                print(f"       🎯 >>> ESTE É O L515! <<<")
                l515_found = True
                l515_device = dev
                l515_serial = serial
            else:
                print(f"       ℹ️  Não é L515")
                
        except Exception as e:
            print(f"    ✗ Erro ao ler dispositivo #{i+1}: {e}")
    
    if not l515_found:
        print("\n    ✗ L515 NÃO ENCONTRADO!")
        print("    Os dispositivos detectados não são L515")
        return False
    
    # 4. Testa o L515
    print(f"\n[4/4] Testando L515 (Serial: {l515_serial})...")
    
    try:
        # Lista sensores disponíveis
        print("\n    📡 Sensores disponíveis no L515:")
        for sensor in l515_device.query_sensors():
            sensor_name = sensor.get_info(rs.camera_info.name)
            print(f"       - {sensor_name}")
        
        # Tenta iniciar pipeline simples
        print("\n    🔧 Testando captura de dados...")
        pipeline = rs.pipeline(ctx)
        config = rs.config()
        config.enable_device(l515_serial)
        
        # Configuração básica que funciona
        config.enable_stream(rs.stream.depth, 320, 240, rs.format.z16, 30)
        
        print("       Iniciando pipeline...")
        profile = pipeline.start(config)
        
        print("       Aguardando estabilização (2s)...")
        import time
        time.sleep(2)
        
        print("       Capturando 3 frames de teste...")
        frames_ok = 0
        for i in range(3):
            try:
                frames = pipeline.wait_for_frames(timeout_ms=2000)
                depth_frame = frames.get_depth_frame()
                
                if depth_frame:
                    import numpy as np
                    data = np.asanyarray(depth_frame.get_data())
                    valid = np.count_nonzero(data > 0)
                    print(f"       ✓ Frame {i+1}/3: {depth_frame.get_width()}x{depth_frame.get_height()}, {valid} pixels válidos")
                    frames_ok += 1
                else:
                    print(f"       ✗ Frame {i+1}/3: vazio")
                    
                time.sleep(0.1)
            except Exception as e:
                print(f"       ✗ Frame {i+1}/3: erro - {e}")
        
        pipeline.stop()
        
        if frames_ok >= 2:
            print(f"\n{'='*70}")
            print("✅ L515 ESTÁ FUNCIONANDO PERFEITAMENTE!")
            print(f"{'='*70}")
            print(f"\n📊 RESUMO:")
            print(f"   Serial Number: {l515_serial}")
            print(f"   Frames capturados: {frames_ok}/3")
            print(f"   Status: OPERACIONAL")
            print(f"\n✅ Você pode usar o L515 no seu projeto!")
            return True
        else:
            print(f"\n⚠️  L515 DETECTADO MAS COM PROBLEMAS")
            print(f"   Apenas {frames_ok}/3 frames capturados")
            print(f"   Tente reiniciar o sensor")
            return False
            
    except Exception as e:
        print(f"\n    ✗ ERRO ao testar L515: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n")
    success = check_l515()
    print("\n")
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
