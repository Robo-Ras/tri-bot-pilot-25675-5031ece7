#!/usr/bin/env python3
"""
Script de teste AVANÇADO para Intel RealSense LiDAR L515
Testa múltiplas configurações e resoluções
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import sys

def test_l515_advanced():
    """Teste avançado com múltiplas tentativas e configurações"""
    
    print("="*70)
    print("TESTE AVANÇADO - INTEL REALSENSE L515")
    print("="*70)
    
    # Passo 1: Criar contexto e listar dispositivos
    print("\n[1/6] Criando contexto RealSense...")
    try:
        ctx = rs.context()
        devices = ctx.query_devices()
        
        if len(devices) == 0:
            print("✗ ERRO: Nenhum dispositivo RealSense encontrado!")
            print("\nVerifique:")
            print("  1. Cabo USB está conectado")
            print("  2. Execute: lsusb | grep Intel")
            print("  3. Execute: rs-enumerate-devices")
            return False
            
        print(f"✓ Encontrados {len(devices)} dispositivo(s)")
        
    except Exception as e:
        print(f"✗ ERRO ao criar contexto: {e}")
        return False
    
    # Passo 2: Identificar L515
    print("\n[2/6] Identificando L515...")
    l515_device = None
    l515_serial = None
    
    for i, dev in enumerate(devices):
        name = dev.get_info(rs.camera_info.name)
        serial = dev.get_info(rs.camera_info.serial_number)
        product_line = dev.get_info(rs.camera_info.product_line)
        firmware = dev.get_info(rs.camera_info.firmware_version)
        
        print(f"\n  Dispositivo {i+1}:")
        print(f"    Nome: {name}")
        print(f"    Serial: {serial}")
        print(f"    Product Line: {product_line}")
        print(f"    Firmware: {firmware}")
        
        # Análise detalhada para identificação
        name_upper = name.upper()
        product_upper = product_line.upper()
        
        print(f"    Verificando identificação:")
        print(f"      'L515' em nome? {'L515' in name_upper}")
        print(f"      'L5' em nome? {'L5' in name_upper}")
        print(f"      'L500' em product_line? {'L500' in product_upper}")
        print(f"      'LIDAR' em nome? {'LIDAR' in name_upper}")
        
        # Verifica se é L515 (critérios mais amplos)
        is_l515 = any([
            'L515' in name_upper,
            'L5' in name_upper and len(name_upper) < 20,  # Evita falsos positivos
            'L500' in product_upper,
            'LIDAR' in name_upper and 'L5' in product_upper
        ])
        
        if is_l515:
            l515_device = dev
            l515_serial = serial
            print(f"    >>> ✓ IDENTIFICADO COMO L515! <<<")
            break
        else:
            print(f"    >>> Não é L515 <<<")
    
    if not l515_device:
        print("\n⚠ L515 NÃO FOI IDENTIFICADO AUTOMATICAMENTE!")
        print("\nTentando usar QUALQUER dispositivo RealSense disponível...")
        
        if len(devices) > 0:
            # Pergunta ao usuário qual dispositivo usar
            print("\nDispositivos disponíveis:")
            for i, dev in enumerate(devices):
                name = dev.get_info(rs.camera_info.name)
                serial = dev.get_info(rs.camera_info.serial_number)
                print(f"  [{i+1}] {name} (Serial: {serial})")
            
            print("\n⚠ USANDO AUTOMATICAMENTE O PRIMEIRO DISPOSITIVO PARA TESTE")
            l515_device = devices[0]
            l515_serial = devices[0].get_info(rs.camera_info.serial_number)
            print(f"  Dispositivo selecionado: {devices[0].get_info(rs.camera_info.name)}")
            print(f"  Serial: {l515_serial}")
        else:
            print("\n✗ Nenhum dispositivo disponível!")
            return False
    
    # Passo 3: Listar sensores do L515
    print("\n[3/6] Listando sensores do L515...")
    sensors = l515_device.query_sensors()
    print(f"  Total de sensores: {len(sensors)}")
    
    for i, sensor in enumerate(sensors):
        sensor_name = sensor.get_info(rs.camera_info.name)
        print(f"  [{i+1}] {sensor_name}")
    
    # Passo 4: Listar perfis disponíveis
    print("\n[4/6] Listando perfis de stream disponíveis...")
    available_profiles = []
    
    for sensor in sensors:
        for profile in sensor.get_stream_profiles():
            if profile.stream_type() == rs.stream.depth:
                video_profile = profile.as_video_stream_profile()
                width = video_profile.width()
                height = video_profile.height()
                fps = video_profile.fps()
                format_type = video_profile.format()
                
                profile_info = {
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'format': format_type
                }
                
                if profile_info not in available_profiles:
                    available_profiles.append(profile_info)
                    print(f"  ✓ {width}x{height} @ {fps}fps ({format_type})")
    
    if len(available_profiles) == 0:
        print("  ✗ Nenhum perfil de profundidade encontrado!")
        return False
    
    # Passo 5: Testar cada configuração disponível
    print("\n[5/6] Testando configurações...")
    
    # Configurações recomendadas para L515 (em ordem de prioridade)
    test_configs = [
        {'width': 640, 'height': 480, 'fps': 30},
        {'width': 1024, 'height': 768, 'fps': 30},
        {'width': 320, 'height': 240, 'fps': 30},
        {'width': 640, 'height': 480, 'fps': 15},
    ]
    
    pipeline = None
    working_config = None
    
    for i, config_params in enumerate(test_configs):
        print(f"\n  Teste {i+1}: {config_params['width']}x{config_params['height']} @ {config_params['fps']}fps")
        
        try:
            # Cria novo pipeline
            pipeline = rs.pipeline(ctx)
            config = rs.config()
            config.enable_device(l515_serial)
            config.enable_stream(
                rs.stream.depth,
                config_params['width'],
                config_params['height'],
                rs.format.z16,
                config_params['fps']
            )
            
            print("    Iniciando pipeline...")
            profile = pipeline.start(config)
            
            # Aguarda estabilização
            import time
            time.sleep(1)
            
            # Testa captura de frames
            print("    Testando captura de frames...")
            frames_ok = 0
            for attempt in range(5):
                try:
                    frames = pipeline.wait_for_frames(timeout_ms=2000)
                    depth_frame = frames.get_depth_frame()
                    
                    if depth_frame:
                        frames_ok += 1
                        
                        if frames_ok == 1:
                            # Informações do primeiro frame
                            width = depth_frame.get_width()
                            height = depth_frame.get_height()
                            print(f"    ✓ Frame capturado: {width}x{height}")
                            
                            # Estatísticas de profundidade
                            depth_data = np.asanyarray(depth_frame.get_data())
                            valid_pixels = np.count_nonzero(depth_data > 0)
                            total_pixels = depth_data.size
                            percentage = (valid_pixels / total_pixels) * 100
                            
                            print(f"    Pixels válidos: {valid_pixels}/{total_pixels} ({percentage:.1f}%)")
                            print(f"    Distância média: {np.mean(depth_data[depth_data > 0]) / 1000:.2f}m")
                            
                except Exception as e:
                    print(f"    ⚠ Falha na tentativa {attempt + 1}: {e}")
            
            if frames_ok >= 3:
                print(f"    ✓✓✓ CONFIGURAÇÃO FUNCIONAL! ({frames_ok}/5 frames capturados)")
                working_config = config_params
                
                # Passo 6: Salvar imagem de teste
                print("\n[6/6] Salvando imagem de teste...")
                try:
                    frames = pipeline.wait_for_frames(timeout_ms=2000)
                    depth_frame = frames.get_depth_frame()
                    
                    if depth_frame:
                        depth_image = np.asanyarray(depth_frame.get_data())
                        
                        # Normaliza e coloriza
                        depth_normalized = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                        depth_colorized = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
                        
                        filename = 'l515_test_working.png'
                        cv2.imwrite(filename, depth_colorized)
                        print(f"  ✓ Imagem salva: {filename}")
                        
                except Exception as e:
                    print(f"  ⚠ Não foi possível salvar imagem: {e}")
                
                break
            else:
                print(f"    ✗ Poucos frames capturados ({frames_ok}/5)")
                pipeline.stop()
                pipeline = None
                
        except Exception as e:
            print(f"    ✗ Erro: {e}")
            if pipeline:
                try:
                    pipeline.stop()
                except:
                    pass
                pipeline = None
    
    # Resultado final
    print("\n" + "="*70)
    if working_config:
        print("✓✓✓ SUCESSO! L515 ESTÁ FUNCIONANDO! ✓✓✓")
        print(f"\nConfiguração recomendada:")
        print(f"  Resolução: {working_config['width']}x{working_config['height']}")
        print(f"  FPS: {working_config['fps']}")
        print("\nUse estas configurações no script principal!")
        
        if pipeline:
            try:
                pipeline.stop()
            except:
                pass
        
        return True
    else:
        print("✗✗✗ FALHA: Nenhuma configuração funcionou ✗✗✗")
        print("\nPossíveis problemas:")
        print("  1. L515 está defeituoso ou precisa de atualização de firmware")
        print("  2. Porta USB não fornece energia suficiente (use USB 3.0)")
        print("  3. Driver ou biblioteca pyrealsense2 desatualizada")
        print("  4. Conflito com outro processo usando o dispositivo")
        return False
    
    print("="*70)

if __name__ == "__main__":
    print("\n" + "🔍 "*20)
    print("DIAGNÓSTICO COMPLETO DO LIDAR L515")
    print("🔍 "*20 + "\n")
    
    success = test_l515_advanced()
    
    if success:
        print("\n✓ Teste concluído com SUCESSO!")
        sys.exit(0)
    else:
        print("\n✗ Teste FALHOU - verifique os erros acima")
        sys.exit(1)
