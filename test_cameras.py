"""
Script de teste para verificar se L515 e D435 estão conectando
Usa exatamente o mesmo código do seu script que funciona
"""

import pyrealsense2 as rs
import time

print("="*70)
print("  TESTE DE CONEXÃO DAS CÂMERAS REALSENSE")
print("="*70)

try:
    print("\n1️⃣  Criando contexto RealSense...")
    ctx = rs.context()
    
    print("\n2️⃣  Listando dispositivos conectados...")
    devices = list(ctx.devices)
    
    if len(devices) == 0:
        print("\n❌ ERRO: Nenhuma câmera RealSense encontrada!")
        print("   Verifique:")
        print("   - Cabos USB estão conectados")
        print("   - Execute: lsusb | grep Intel")
        print("   - Tente desconectar e reconectar os cabos USB")
        exit(1)
    
    print(f"\n✓ Encontradas {len(devices)} câmera(s):")
    
    cameras_info = []
    for idx, device in enumerate(devices, start=1):
        try:
            serial = device.get_info(rs.camera_info.serial_number)
            name = device.get_info(rs.camera_info.name)
            firmware = device.get_info(rs.camera_info.firmware_version)
            
            print(f"\n   {idx}. {name}")
            print(f"      Serial: {serial}")
            print(f"      Firmware: {firmware}")
            
            # Determina resolução baseada no tipo
            if 'L515' in name:
                depth_res = (320, 240)
                color_res = (640, 480)
            elif 'D435' in name:
                depth_res = (640, 480)
                color_res = (640, 480)
            else:
                depth_res = (640, 480)
                color_res = (640, 480)
            
            cameras_info.append({
                'name': name,
                'serial': serial,
                'depth_res': depth_res,
                'color_res': color_res
            })
        except Exception as e:
            print(f"   ❌ Erro ao ler informações do dispositivo {idx}: {e}")
            continue
    
    if not cameras_info:
        print("\n❌ ERRO: Não foi possível ler informações das câmeras")
        exit(1)
    
    # Testa inicialização de cada câmera
    print(f"\n3️⃣  Testando inicialização das câmeras...")
    
    successful_cameras = []
    
    for cam_info in cameras_info:
        print(f"\n   Testando {cam_info['name']}...")
        
        try:
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_device(cam_info['serial'])
            
            # Configura streams
            depth_w, depth_h = cam_info['depth_res']
            color_w, color_h = cam_info['color_res']
            
            config.enable_stream(rs.stream.depth, depth_w, depth_h, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, color_w, color_h, rs.format.bgr8, 30)
            
            print(f"      Iniciando pipeline...")
            profile = pipeline.start(config)
            
            # Obtém depth scale
            depth_sensor = profile.get_device().first_depth_sensor()
            depth_scale = depth_sensor.get_depth_scale()
            
            print(f"      ✓ Pipeline iniciado!")
            print(f"      ✓ Depth scale: {depth_scale}")
            
            # Testa captura de frames
            print(f"      Testando captura de 5 frames...")
            frames_ok = 0
            for i in range(5):
                frames = pipeline.wait_for_frames(timeout_ms=2000)
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                
                if depth_frame and color_frame:
                    frames_ok += 1
                    print(f"         Frame {i+1}/5: ✓ {color_frame.get_width()}x{color_frame.get_height()}")
                else:
                    print(f"         Frame {i+1}/5: ❌ falhou")
                
                time.sleep(0.1)
            
            if frames_ok >= 3:
                print(f"      ✓✓✓ {cam_info['name']} FUNCIONANDO ({frames_ok}/5 frames OK)")
                successful_cameras.append(cam_info['name'])
            else:
                print(f"      ⚠️  {cam_info['name']} instável ({frames_ok}/5 frames OK)")
            
            # Para pipeline
            pipeline.stop()
            
        except Exception as e:
            print(f"      ❌ Erro ao testar {cam_info['name']}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Resultado final
    print(f"\n{'='*70}")
    print("  RESULTADO DO TESTE")
    print(f"{'='*70}")
    
    if len(successful_cameras) == 0:
        print("\n❌ NENHUMA câmera funcionando!")
        print("   O sistema autônomo NÃO funcionará.")
        print("\n   Soluções:")
        print("   1. Desconecte e reconecte os cabos USB")
        print("   2. Tente conectar em portas USB diferentes")
        print("   3. Reinicie o computador")
        print("   4. Verifique se tem permissão USB (udev rules)")
    elif len(successful_cameras) == len(cameras_info):
        print(f"\n✓✓✓ TODAS as {len(successful_cameras)} câmeras estão FUNCIONANDO!")
        for cam_name in successful_cameras:
            print(f"   ✓ {cam_name}")
        print("\n🎉 Sistema autônomo PRONTO para uso!")
        print("   Execute: python3 robot_autonomous_control.py")
    else:
        print(f"\n⚠️  Apenas {len(successful_cameras)}/{len(cameras_info)} câmera(s) funcionando:")
        for cam_name in successful_cameras:
            print(f"   ✓ {cam_name}")
        print("\n   O sistema pode funcionar parcialmente.")
    
    print(f"\n{'='*70}\n")

except Exception as e:
    print(f"\n❌ ERRO CRÍTICO: {e}")
    import traceback
    traceback.print_exc()
    print("\n   Isso pode indicar problema com:")
    print("   - Instalação do pyrealsense2")
    print("   - Drivers USB")
    print("   - Permissões do sistema")
    exit(1)
