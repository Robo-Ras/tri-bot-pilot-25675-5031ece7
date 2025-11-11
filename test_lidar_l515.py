#!/usr/bin/env python3
"""
Script de teste isolado para Intel RealSense L515 LiDAR
Use este script para diagnosticar problemas de conexão do LiDAR
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import sys

def test_lidar():
    """Testa conexão e funcionamento do LiDAR L515"""
    
    print("\n" + "="*70)
    print("DIAGNÓSTICO DO INTEL REALSENSE L515 LIDAR")
    print("="*70)
    
    # Passo 1: Listar todos os dispositivos
    print("\n[PASSO 1] Listando dispositivos RealSense conectados...")
    ctx = rs.context()
    devices = ctx.query_devices()
    
    if len(devices) == 0:
        print("✗ ERRO: Nenhum dispositivo RealSense encontrado!")
        print("\nSOLUÇÕES:")
        print("  1. Verifique se o L515 está conectado via USB")
        print("  2. Execute: lsusb | grep Intel")
        print("  3. Verifique se o LED do sensor está aceso")
        print("  4. Tente outro cabo ou porta USB 3.0")
        print("  5. Execute: sudo chmod 666 /dev/video*")
        return False
    
    print(f"✓ Encontrado(s) {len(devices)} dispositivo(s)\n")
    
    # Passo 2: Identificar o L515
    print("[PASSO 2] Identificando L515...")
    lidar_device = None
    lidar_serial = None
    
    for i, dev in enumerate(devices):
        name = dev.get_info(rs.camera_info.name)
        serial = dev.get_info(rs.camera_info.serial_number)
        firmware = dev.get_info(rs.camera_info.firmware_version)
        product_line = dev.get_info(rs.camera_info.product_line)
        
        print(f"\nDispositivo {i+1}:")
        print(f"  Nome: {name}")
        print(f"  Serial: {serial}")
        print(f"  Firmware: {firmware}")
        print(f"  Linha: {product_line}")
        
        # Verifica se é L515
        name_upper = name.upper()
        product_upper = product_line.upper()
        
        if 'L515' in name_upper or 'L5' in name_upper or 'L500' in product_upper:
            lidar_device = dev
            lidar_serial = serial
            print("  >>> ESTE É O L515! <<<")
    
    if not lidar_device:
        print("\n✗ ERRO: L515 não foi identificado entre os dispositivos")
        print("  Verifique se o dispositivo conectado é realmente um L515")
        if len(devices) > 0:
            print(f"\n  Tentando usar {devices[0].get_info(rs.camera_info.name)} como teste...")
            lidar_device = devices[0]
            lidar_serial = devices[0].get_info(rs.camera_info.serial_number)
        else:
            return False
    else:
        print(f"\n✓ L515 identificado com sucesso!")
    
    # Passo 3: Listar sensores disponíveis
    print(f"\n[PASSO 3] Verificando sensores no L515 (Serial: {lidar_serial})...")
    sensors = lidar_device.query_sensors()
    
    print(f"  Sensores encontrados: {len(sensors)}")
    for i, sensor in enumerate(sensors):
        sensor_name = sensor.get_info(rs.camera_info.name)
        print(f"    {i+1}. {sensor_name}")
        
        # Lista perfis de stream disponíveis
        stream_profiles = sensor.get_stream_profiles()
        depth_profiles = [p for p in stream_profiles if p.stream_type() == rs.stream.depth]
        
        if depth_profiles:
            print(f"       Perfis de profundidade disponíveis: {len(depth_profiles)}")
            for j, profile in enumerate(depth_profiles[:3]):  # Mostra primeiros 3
                vp = profile.as_video_stream_profile()
                print(f"         - {vp.width()}x{vp.height()} @ {vp.fps()}fps")
    
    # Passo 4: Tentar iniciar pipeline
    print(f"\n[PASSO 4] Tentando iniciar pipeline do L515...")
    
    try:
        pipeline = rs.pipeline(ctx)
        config = rs.config()
        config.enable_device(lidar_serial)
        
        print("  Iniciando pipeline...")
        profile = pipeline.start(config)
        
        print("  ✓ Pipeline iniciado com sucesso!")
        
        # Obtém informações do stream ativo
        depth_stream = profile.get_stream(rs.stream.depth)
        if depth_stream:
            vp = depth_stream.as_video_stream_profile()
            print(f"  Stream de profundidade ativo:")
            print(f"    Resolução: {vp.width()}x{vp.height()}")
            print(f"    FPS: {vp.fps()}")
            print(f"    Formato: {vp.format()}")
        
        # Passo 5: Testar captura de frames
        print(f"\n[PASSO 5] Testando captura de frames...")
        
        import time
        time.sleep(2)  # Aguarda estabilização
        
        for i in range(5):
            print(f"  Tentativa {i+1}/5...", end=" ")
            try:
                frames = pipeline.wait_for_frames(timeout_ms=5000)
                depth_frame = frames.get_depth_frame()
                
                if depth_frame:
                    width = depth_frame.get_width()
                    height = depth_frame.get_height()
                    data = np.asanyarray(depth_frame.get_data())
                    
                    # Estatísticas dos dados
                    valid_pixels = np.count_nonzero(data)
                    min_depth = np.min(data[data > 0]) if valid_pixels > 0 else 0
                    max_depth = np.max(data)
                    
                    print(f"✓ OK! Resolução: {width}x{height}, Pixels válidos: {valid_pixels}, Min: {min_depth}mm, Max: {max_depth}mm")
                else:
                    print("✗ Frame vazio")
            except Exception as e:
                print(f"✗ Erro: {e}")
            
            time.sleep(0.5)
        
        # Passo 6: Salvar imagem de teste
        print(f"\n[PASSO 6] Salvando imagem de teste...")
        try:
            frames = pipeline.wait_for_frames(timeout_ms=5000)
            depth_frame = frames.get_depth_frame()
            
            if depth_frame:
                depth_image = np.asanyarray(depth_frame.get_data())
                
                # Normaliza e coloriza
                depth_normalized = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX)
                depth_colored = cv2.applyColorMap(depth_normalized.astype(np.uint8), cv2.COLORMAP_JET)
                
                filename = 'lidar_test_output.jpg'
                cv2.imwrite(filename, depth_colored)
                print(f"  ✓ Imagem salva em: {filename}")
        except Exception as e:
            print(f"  ✗ Erro ao salvar: {e}")
        
        # Para pipeline
        pipeline.stop()
        print("\n✓ Pipeline parado com sucesso")
        
        print("\n" + "="*70)
        print("RESULTADO: L515 ESTÁ FUNCIONANDO CORRETAMENTE! ✓")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n✗ ERRO ao iniciar pipeline: {e}")
        print(f"  Tipo: {type(e).__name__}")
        
        import traceback
        print("\nStack trace completo:")
        traceback.print_exc()
        
        print("\n" + "="*70)
        print("RESULTADO: FALHA NA INICIALIZAÇÃO DO L515 ✗")
        print("="*70)
        return False

if __name__ == "__main__":
    print("\nExecutando teste do LiDAR L515...")
    print("Pressione Ctrl+C para cancelar\n")
    
    try:
        success = test_lidar()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTeste cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nErro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
