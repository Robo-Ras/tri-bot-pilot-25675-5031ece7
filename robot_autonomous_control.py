"""
Sistema de Controle Autônomo com Intel RealSense L515 e D435
- L515 (LiDAR): Posicionado embaixo do robô para detectar obstáculos no chão
- D435 (Câmera): Posicionada em cima para verificar altura dos objetos
- Reconstrução 3D do ambiente em tempo real
"""

import pyrealsense2 as rs
import numpy as np
import serial
import serial.tools.list_ports
import asyncio
import websockets
import json
import cv2
import base64
import open3d as o3d
from threading import Thread
from queue import Queue
from collections import deque
from scipy.spatial import distance

class RealSenseController:
    """Gerencia os sensores Intel RealSense"""
    
    def __init__(self):
        self.pipeline_lidar = None
        self.pipeline_camera = None
        self.lidar_started = False
        self.camera_started = False
        self.lidar_serial = None
        self.camera_serial = None
        
        # Para reconstrução 3D
        self.point_cloud = o3d.geometry.PointCloud()
        self.mesh = None
        
    def cleanup(self):
        """Libera todos os recursos dos sensores"""
        try:
            if self.pipeline_lidar:
                self.pipeline_lidar.stop()
                self.pipeline_lidar = None
                self.lidar_started = False
                print("  ✓ Pipeline LiDAR liberado")
        except:
            pass
        
        try:
            if self.pipeline_camera:
                self.pipeline_camera.stop()
                self.pipeline_camera = None
                self.camera_started = False
                print("  ✓ Pipeline Câmera liberado")
        except:
            pass
        
    def list_devices(self):
        """Lista todos os dispositivos RealSense conectados"""
        ctx = rs.context()
        devices = ctx.query_devices()
        print("\n=== Dispositivos RealSense Detectados ===")
        
        if len(devices) == 0:
            print("✗ Nenhum dispositivo RealSense encontrado!")
            print("  Verifique se os sensores estão conectados via USB")
            print("  Execute: lsusb | grep Intel")
            return []
        
        device_list = []
        for i, dev in enumerate(devices):
            name = dev.get_info(rs.camera_info.name)
            serial = dev.get_info(rs.camera_info.serial_number)
            firmware = dev.get_info(rs.camera_info.firmware_version)
            product_line = dev.get_info(rs.camera_info.product_line)
            
            print(f"{i+1}. {name}")
            print(f"   Serial: {serial}")
            print(f"   Firmware: {firmware}")
            print(f"   Linha de Produto: {product_line}")
            
            # DEBUG: Mostra valores para comparação
            print(f"   [DEBUG] Nome UPPER: '{name.upper()}'")
            print(f"   [DEBUG] Product UPPER: '{product_line.upper()}'")
            print(f"   [DEBUG] Tamanho nome: {len(name)}")
            
            device_list.append({
                'name': name, 
                'serial': serial, 
                'product_line': product_line
            })
        
        return device_list
    
    def identify_devices(self):
        """Identifica e atribui dispositivos baseado no modelo"""
        devices = self.list_devices()
        
        if len(devices) == 0:
            print("\n" + "="*60)
            print("✗ ERRO CRÍTICO: Nenhum dispositivo RealSense detectado!")
            print("="*60)
            print("\nPASSOS PARA SOLUCIONAR:")
            print("1. Verifique se os sensores estão conectados via USB 3.0")
            print("2. Execute: lsusb | grep Intel")
            print("   Você deve ver 'Intel Corp' na lista")
            print("3. Verifique permissões: ls -la /dev/video*")
            print("4. Se necessário: sudo chmod 666 /dev/video*")
            print("5. Tente outro cabo ou porta USB")
            print("6. Reinicie os sensores (desconecte e reconecte)")
            print("="*60)
            return False
        
        print("\n" + "="*60)
        print(f"ANALISANDO {len(devices)} DISPOSITIVO(S) REALSENSE")
        print("="*60)
        
        for i, dev in enumerate(devices):
            name = dev['name']
            name_upper = name.upper()
            product_line = dev.get('product_line', '')
            product_upper = product_line.upper()
            serial = dev['serial']
            
            print(f"\n[{i+1}] Dispositivo encontrado:")
            print(f"    Nome: {name}")
            print(f"    Serial: {serial}")
            print(f"    Linha: {product_line}")
            
            # Debug MUITO detalhado de identificação
            print(f"    [DEBUG] Testes de identificação:")
            
            # Testes para LiDAR
            test1 = 'L515' in name_upper
            test2 = 'L5' in name_upper and len(name) < 20
            test3 = 'L500' in product_upper
            test4 = 'LIDAR' in name_upper and 'L5' in product_upper
            
            print(f"      LiDAR - 'L515' in nome: {test1}")
            print(f"      LiDAR - 'L5' in nome (curto): {test2} (len={len(name)})")
            print(f"      LiDAR - 'L500' in product: {test3}")
            print(f"      LiDAR - 'LIDAR' e 'L5': {test4}")
            
            # Testes para Câmera
            test5 = 'D435' in name_upper
            test6 = 'D4' in name_upper and len(name) < 20
            test7 = 'D400' in product_upper
            
            print(f"      Câmera - 'D435' in nome: {test5}")
            print(f"      Câmera - 'D4' in nome (curto): {test6}")
            print(f"      Câmera - 'D400' in product: {test7}")
            
            # Identifica L515 (LiDAR)
            is_lidar = test1 or test2 or test3 or test4
            
            # Identifica D435 (Câmera)
            is_camera = test5 or test6 or test7
            
            print(f"    RESULTADO:")
            if is_lidar:
                self.lidar_serial = serial
                print(f"      >>> ✓ IDENTIFICADO COMO: LiDAR L515 <<<")
                print(f"      Será usado para detecção de obstáculos no chão")
            elif is_camera:
                self.camera_serial = serial
                print(f"      >>> ✓ IDENTIFICADO COMO: Câmera D435 <<<")
                print(f"      Será usada para detecção de altura e tracking")
            else:
                print(f"      >>> ⚠ TIPO DESCONHECIDO <<<")
                print(f"      Será atribuído automaticamente no fallback")
        
        # Fallback se não conseguiu identificar especificamente
        if not self.lidar_serial and not self.camera_serial and len(devices) > 0:
            print(f"\n⚠ NENHUM DISPOSITIVO IDENTIFICADO AUTOMATICAMENTE")
            print(f"  Usando fallback: tentando atribuir dispositivos...")
            
            # Tenta atribuir baseado na ordem
            if len(devices) == 1:
                # Apenas 1 dispositivo - usa como câmera (mais comum)
                self.camera_serial = devices[0]['serial']
                print(f"  Usando {devices[0]['name']} como CÂMERA (único dispositivo)")
            elif len(devices) >= 2:
                # 2 ou mais dispositivos
                self.lidar_serial = devices[0]['serial']
                self.camera_serial = devices[1]['serial']
                print(f"  Usando {devices[0]['name']} como LiDAR (primeiro)")
                print(f"  Usando {devices[1]['name']} como CÂMERA (segundo)")
        elif not self.camera_serial and len(devices) > 0:
            # Tem LiDAR mas não tem câmera
            for dev in devices:
                if dev['serial'] != self.lidar_serial:
                    self.camera_serial = dev['serial']
                    print(f"\n⚠ Usando {dev['name']} como CÂMERA (fallback)")
                    break
        elif not self.lidar_serial and len(devices) > 0:
            # Tem câmera mas não tem LiDAR
            for dev in devices:
                if dev['serial'] != self.camera_serial:
                    self.lidar_serial = dev['serial']
                    print(f"\n⚠ Usando {dev['name']} como LiDAR (fallback)")
                    break
        
        print("\n" + "="*60)
        print("RESUMO DA CONFIGURAÇÃO:")
        if self.lidar_serial:
            print(f"  ✓ LiDAR configurado: Serial {self.lidar_serial}")
        else:
            print("  ✗ LiDAR NÃO CONFIGURADO")
        
        if self.camera_serial:
            print(f"  ✓ Câmera configurada: Serial {self.camera_serial}")
        else:
            print("  ✗ Câmera NÃO CONFIGURADA")
        print("="*60 + "\n")
        
        return self.lidar_serial is not None or self.camera_serial is not None
    
    def start(self):
        """Inicia os sensores"""
        # Primeiro, limpa qualquer recurso anterior
        print("\nLimpando recursos anteriores...")
        self.cleanup()
        
        if not self.identify_devices():
            print("✗ Nenhum dispositivo RealSense disponível!")
            return False
        
        # Inicia LiDAR (embaixo do robô) - SIMPLIFICADO como no teste
        if self.lidar_serial:
            print(f"\n{'='*60}")
            print(f"INICIANDO LIDAR L515 (Serial: {self.lidar_serial})")
            print(f"{'='*60}")
            
            try:
                ctx = rs.context()
                
                # Cria pipeline simples - igual ao teste que funcionou
                self.pipeline_lidar = rs.pipeline(ctx)
                config_lidar = rs.config()
                config_lidar.enable_device(self.lidar_serial)
                
                # NÃO força configuração específica - deixa usar padrão
                print("  Iniciando pipeline com configuração padrão...")
                profile = self.pipeline_lidar.start(config_lidar)
                
                print("  ✓ Pipeline iniciado!")
                
                # Obtém informações do stream ativo
                depth_stream = profile.get_stream(rs.stream.depth)
                if depth_stream:
                    vp = depth_stream.as_video_stream_profile()
                    print(f"  Stream de profundidade ativo:")
                    print(f"    Resolução: {vp.width()}x{vp.height()}")
                    print(f"    FPS: {vp.fps()}")
                    print(f"    Formato: {vp.format()}")
                
                # Aguarda estabilização
                import time
                print("  Aguardando estabilização (2s)...")
                time.sleep(2)
                
                # Testa captura de frames
                print("  Testando captura de frames...")
                frames_captured = 0
                for i in range(5):
                    try:
                        print(f"    Tentativa {i+1}/5...", end=" ")
                        frames = self.pipeline_lidar.wait_for_frames(timeout_ms=5000)
                        depth_frame = frames.get_depth_frame()
                        
                        if depth_frame:
                            frames_captured += 1
                            width = depth_frame.get_width()
                            height = depth_frame.get_height()
                            data = np.asanyarray(depth_frame.get_data())
                            valid_pixels = np.count_nonzero(data > 0)
                            print(f"✓ OK! {width}x{height}, {valid_pixels} pixels válidos")
                        else:
                            print("✗ Frame vazio")
                    except Exception as e:
                        print(f"✗ Erro: {str(e)[:50]}")
                    
                    time.sleep(0.1)
                
                if frames_captured > 0:
                    self.lidar_started = True
                    print(f"\n{'='*60}")
                    print(f"✓✓✓ LIDAR L515 CONECTADO E FUNCIONANDO!")
                    print(f"    Frames capturados: {frames_captured}/5")
                    print(f"    Posição: embaixo do robô")
                    print(f"{'='*60}\n")
                else:
                    print(f"\n✗ FALHA: Nenhum frame capturado")
                    self.pipeline_lidar.stop()
                    self.pipeline_lidar = None
                    self.lidar_started = False
                    
            except Exception as e:
                print(f"\n✗ ERRO ao iniciar LiDAR: {e}")
                print(f"  Tipo: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                if self.pipeline_lidar:
                    try:
                        self.pipeline_lidar.stop()
                    except:
                        pass
                self.pipeline_lidar = None
                self.lidar_started = False
        else:
            print("\n⚠ LiDAR não será iniciado (serial não identificado)")
        
        # Inicia Câmera (em cima do robô)
        if self.camera_serial:
            print(f"\nTentando iniciar Câmera (Serial: {self.camera_serial})...")
            
            # Verifica se o dispositivo está ocupado e tenta resetar
            try:
                ctx = rs.context()
                devices = ctx.query_devices()
                
                camera_device = None
                for dev in devices:
                    if dev.get_info(rs.camera_info.serial_number) == self.camera_serial:
                        camera_device = dev
                        break
                
                if camera_device:
                    print("  Verificando estado do dispositivo...")
                    
                    # Tenta fazer hardware reset se disponível
                    try:
                        if camera_device.supports(rs.camera_info.product_line):
                            print("  Tentando reset de hardware...")
                            camera_device.hardware_reset()
                            import time
                            time.sleep(3)  # Aguarda reset
                            print("  ✓ Reset concluído")
                    except:
                        pass
                
                self.pipeline_camera = rs.pipeline()
                config_camera = rs.config()
                config_camera.enable_device(self.camera_serial)
                config_camera.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
                config_camera.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
                
                profile = self.pipeline_camera.start(config_camera)
                
                # Obtém informações dos streams
                color_stream = profile.get_stream(rs.stream.color)
                depth_stream = profile.get_stream(rs.stream.depth)
                
                print(f"  ✓ Streams ativos:")
                if color_stream:
                    print(f"    Color: {color_stream.as_video_stream_profile().width()}x{color_stream.as_video_stream_profile().height()}")
                if depth_stream:
                    print(f"    Depth: {depth_stream.as_video_stream_profile().width()}x{depth_stream.as_video_stream_profile().height()}")
                
                self.camera_started = True
                print("✓ Câmera CONECTADA E FUNCIONANDO! (posição: em cima do robô)")
                
            except RuntimeError as e:
                error_msg = str(e)
                if "busy" in error_msg.lower():
                    print(f"✗ ERRO: Câmera está sendo usada por outro processo")
                    print(f"  Execute: sudo fuser -k /dev/video*")
                    print(f"  Ou reinicie o sistema")
                else:
                    print(f"✗ FALHA ao iniciar câmera: {e}")
                print(f"  Tipo de erro: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                self.pipeline_camera = None
                self.camera_started = False
            except Exception as e:
                print(f"✗ FALHA ao iniciar câmera: {e}")
                print(f"  Tipo de erro: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                self.pipeline_camera = None
                self.camera_started = False
        else:
            print("⚠ Câmera não será iniciada (serial não identificado)")
        
        print(f"\n{'='*50}")
        print("STATUS FINAL:")
        print(f"  LiDAR: {'✓ FUNCIONANDO' if self.lidar_started else '✗ OFFLINE'}")
        print(f"  Câmera: {'✓ FUNCIONANDO' if self.camera_started else '✗ OFFLINE'}")
        
        # Mensagem especial se operando apenas com câmera
        if self.camera_started and not self.lidar_started:
            print(f"\n⚠️  MODO: NAVEGAÇÃO APENAS COM CÂMERA D435")
            print(f"  ↳ Detecção de obstáculos baseada em profundidade da câmera")
            print(f"  ↳ LiDAR offline - sistema funcionará sem ele")
        elif self.lidar_started and not self.camera_started:
            print(f"\n⚠️  MODO: NAVEGAÇÃO APENAS COM LIDAR L515")
            print(f"  ↳ Câmera offline - sistema funcionará sem ela")
        
        print(f"{'='*50}\n")
        
        # Permite iniciar com apenas um sensor
        if self.camera_started or self.lidar_started:
            if self.camera_started:
                print("✓✓✓ SISTEMA PRONTO PARA NAVEGAÇÃO AUTÔNOMA")
                print("    Usando câmera D435 para detecção de obstáculos")
            return True
        else:
            print("✗✗✗ FALHA: Nenhum sensor disponível para navegação")
            return False
    
    def get_lidar_data(self):
        """Obtém dados do LiDAR (obstáculos no chão)"""
        if not self.lidar_started or not self.pipeline_lidar:
            return None
        
        try:
            frames = self.pipeline_lidar.wait_for_frames(timeout_ms=1000)
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                return None
            
            depth_image = np.asanyarray(depth_frame.get_data())
            return depth_image
        except RuntimeError as e:
            if "wait_for_frames cannot be called before start()" in str(e):
                print("⚠ LiDAR não está iniciado, tentando reiniciar...")
                self.lidar_started = False
                self.pipeline_lidar = None
            return None
        except Exception as e:
            print(f"Erro ao obter dados do LiDAR: {e}")
            return None
    
    def get_camera_data(self):
        """Obtém dados da câmera (verificação de altura)"""
        if not self.camera_started or not self.pipeline_camera:
            return None, None
        
        try:
            frames = self.pipeline_camera.wait_for_frames(timeout_ms=5000)
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                return None, None
            
            color_image = np.asanyarray(color_frame.get_data())
            depth_image = np.asanyarray(depth_frame.get_data())
            
            return color_image, depth_image
        except Exception as e:
            print(f"Erro ao obter dados da câmera: {e}")
            return None, None
    
    def create_point_cloud(self, depth_image, color_image=None):
        """Cria nuvem de pontos para reconstrução 3D"""
        if depth_image is None:
            return None
        
        # Converte profundidade para metros
        depth_meters = depth_image * 0.001
        
        # Cria malha de coordenadas
        height, width = depth_meters.shape
        fx = fy = 500  # Focal length aproximada
        cx, cy = width / 2, height / 2
        
        points = []
        colors = []
        
        for v in range(0, height, 4):  # Amostragem para performance
            for u in range(0, width, 4):
                z = depth_meters[v, u]
                if z > 0.1 and z < 10:  # Filtra valores inválidos
                    x = (u - cx) * z / fx
                    y = (v - cy) * z / fy
                    points.append([x, y, z])
                    
                    if color_image is not None:
                        b, g, r = color_image[v, u]
                        colors.append([r/255.0, g/255.0, b/255.0])
                    else:
                        colors.append([0.5, 0.5, 0.5])
        
        if len(points) == 0:
            return None
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.array(points))
        pcd.colors = o3d.utility.Vector3dVector(np.array(colors))
        
        return pcd
    
    def stop(self):
        """Para os sensores"""
        print("\nParando sensores...")
        self.cleanup()
        print("✓ Sensores parados")


class ObjectTracker:
    """Rastreia objetos detectados pela câmera - versão simplificada e robusta"""
    
    def __init__(self, max_disappeared=10, min_area=5000, max_distance=2.0, min_distance=0.5):
        self.next_object_id = 0
        self.objects = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared
        self.min_area = min_area
        self.max_distance = max_distance
        self.min_distance = min_distance
        
    def detect_objects(self, depth_frame):
        """Detecta objetos usando segmentação simples por profundidade"""
        if depth_frame is None:
            return []
        
        detected_objects = []
        
        try:
            # Converte para metros
            depth_meters = depth_frame.astype(np.float32) * 0.001
            
            # Filtra faixa de distância
            mask = ((depth_meters > self.min_distance) & (depth_meters < self.max_distance)).astype(np.uint8) * 255
            
            # Limpa ruído - operações morfológicas simples
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Encontra contornos
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.min_area:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filtra proporções estranhas
                aspect = w / float(h) if h > 0 else 0
                if aspect > 3 or aspect < 0.3:
                    continue
                
                # Centroide
                cx = x + w // 2
                cy = y + h // 2
                
                # Profundidade média robusta
                depth_roi = depth_meters[y:y+h, x:x+w]
                valid_depths = depth_roi[(depth_roi > self.min_distance) & (depth_roi < self.max_distance)]
                
                if len(valid_depths) < 50:
                    continue
                
                depth = float(np.median(valid_depths))
                
                detected_objects.append({
                    'bbox': (x, y, w, h),
                    'centroid': (cx, cy),
                    'area': int(area),
                    'depth': round(depth, 2)
                })
        
        except Exception as e:
            print(f"Erro na detecção: {e}")
        
        return detected_objects
    
    def update(self, detected_objects):
        """Atualiza tracking com associação simples"""
        if len(detected_objects) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return self.get_tracked_objects()
        
        if len(self.objects) == 0:
            for obj in detected_objects:
                self.objects[self.next_object_id] = obj
                self.disappeared[self.next_object_id] = 0
                self.next_object_id += 1
        else:
            object_ids = list(self.objects.keys())
            object_centroids = np.array([self.objects[oid]['centroid'] for oid in object_ids])
            detected_centroids = np.array([obj['centroid'] for obj in detected_objects])
            
            # Distância euclidiana
            D = distance.cdist(object_centroids, detected_centroids)
            
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > 100:  # 100 pixels
                    continue
                
                obj_id = object_ids[row]
                self.objects[obj_id] = detected_objects[col]
                self.disappeared[obj_id] = 0
                used_rows.add(row)
                used_cols.add(col)
            
            # Marca desaparecidos
            for row in set(range(D.shape[0])) - used_rows:
                obj_id = object_ids[row]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            
            # Novos objetos
            for col in set(range(D.shape[1])) - used_cols:
                self.objects[self.next_object_id] = detected_objects[col]
                self.disappeared[self.next_object_id] = 0
                self.next_object_id += 1
        
        return self.get_tracked_objects()
    
    def get_tracked_objects(self):
        """Retorna objetos ativos"""
        tracked = []
        for obj_id, obj_data in self.objects.items():
            x, y, w, h = obj_data['bbox']
            cx, cy = obj_data['centroid']
            tracked.append({
                'id': int(obj_id),
                'bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                'centroid': {'x': int(cx), 'y': int(cy)},
                'area': obj_data['area'],
                'depth': obj_data.get('depth')
            })
        return tracked


class ObstacleDetector:
    """Detecta obstáculos usando dados dos sensores"""
    
    def __init__(self, safe_distance=0.5, height_threshold=1.5):
        self.safe_distance = safe_distance  # metros - distância segura horizontal
        self.height_threshold = height_threshold  # metros - altura máxima permitida
        
    def analyze_lidar(self, depth_image):
        """Analisa dados do LiDAR (embaixo) para obstáculos no chão"""
        if depth_image is None:
            return None
        
        # Converte para metros
        depth_meters = depth_image * 0.001
        
        # Divide a imagem em setores (esquerda, centro, direita)
        height, width = depth_meters.shape
        left_sector = depth_meters[:, :width//3]
        center_sector = depth_meters[:, width//3:2*width//3]
        right_sector = depth_meters[:, 2*width//3:]
        
        # Calcula distância mínima em cada setor
        left_valid = left_sector[left_sector > 0]
        center_valid = center_sector[center_sector > 0]
        right_valid = right_sector[right_sector > 0]
        
        left_min = np.min(left_valid) if len(left_valid) > 0 else 10.0
        center_min = np.min(center_valid) if len(center_valid) > 0 else 10.0
        right_min = np.min(right_valid) if len(right_valid) > 0 else 10.0
        
        obstacles = {
            'type': 'ground',
            'left': bool(left_min < self.safe_distance),
            'center': bool(center_min < self.safe_distance),
            'right': bool(right_min < self.safe_distance),
            'distances': {
                'left': float(left_min),
                'center': float(center_min),
                'right': float(right_min)
            }
        }
        
        return obstacles
    
    def analyze_height(self, depth_image):
        """Analisa dados da câmera D435 para detectar e desviar de objetos"""
        if depth_image is None:
            return None
        
        # Converte para metros
        depth_meters = depth_image * 0.001
        
        # Analisa a região central da imagem (onde obstáculos são mais relevantes)
        height, width = depth_meters.shape
        
        # Região de interesse: FOCO NO CENTRO e PARTE SUPERIOR (ignora chão)
        # Usa apenas 40% da altura central (ignora chão na parte inferior)
        # Usa 70% da largura central (ignora periferias)
        roi_height = int(height * 0.4)  # 40% altura - região útil
        roi_width = int(width * 0.7)    # 70% largura - foco central
        margin_h = int(height * 0.1)    # Começa em 10% de altura (ignora chão)
        margin_w = (width - roi_width) // 2
        
        roi = depth_meters[margin_h:margin_h+roi_height, margin_w:margin_w+roi_width]
        
        # Divide em setores para navegação
        _, roi_width = roi.shape
        left_sector = roi[:, :roi_width//3]
        center_sector = roi[:, roi_width//3:2*roi_width//3]
        right_sector = roi[:, 2*roi_width//3:]
        
        # DISTÂNCIA DE SEGURANÇA para navegação autônoma (reduzida)
        safe_distance = 0.8  # 0.8 metros - distância mais conservadora
        
        # Filtra valores válidos em cada setor (intervalo mais restrito)
        left_valid = left_sector[(left_sector > 0.4) & (left_sector < 5.0)]
        center_valid = center_sector[(center_sector > 0.4) & (center_sector < 5.0)]
        right_valid = right_sector[(right_sector > 0.4) & (right_sector < 5.0)]
        
        # Usa PERCENTIL 10 ao invés de MIN para ignorar ruído
        # Requer muito mais pontos válidos para considerar obstáculo (500 pts)
        def get_robust_distance(valid_points, min_threshold=500):
            if len(valid_points) < min_threshold:
                return 10.0  # Caminho livre
            # Usa percentil 10 - ignora outliers/ruído
            return float(np.percentile(valid_points, 10))
        
        left_dist = get_robust_distance(left_valid)
        center_dist = get_robust_distance(center_valid)
        right_dist = get_robust_distance(right_valid)
        
        # Detecta obstáculos apenas se MUITOS pontos estiverem próximos
        left_blocked = bool(left_dist < safe_distance)
        center_blocked = bool(center_dist < safe_distance)
        right_blocked = bool(right_dist < safe_distance)
        
        height_obstacles = {
            'type': 'camera_object_detection',
            'left': left_blocked,
            'center': center_blocked,
            'right': right_blocked,
            'distances': {
                'left': float(left_dist),
                'center': float(center_dist),
                'right': float(right_dist)
            },
            'sensor': 'D435'
        }
        
        return height_obstacles


class AutonomousNavigator:
    """Sistema de navegação autônoma"""
    
    def __init__(self, obstacle_detector):
        self.detector = obstacle_detector
        self.current_state = 'idle'
        self.base_speed = 100  # Velocidade base configurável
        
    def decide_movement(self, ground_obstacles, height_obstacles):
        """Decide movimento baseado em objetos detectados pela câmera D435"""
        # Combina informações de ambos os sensores (ou usa apenas o disponível)
        obstacles_combined = {
            'left': False,
            'center': False,
            'right': False
        }
        
        distances = {
            'left': 10.0,
            'center': 10.0,
            'right': 10.0
        }
        
        # Identifica modo de operação
        sensor_mode = None
        if ground_obstacles and height_obstacles:
            sensor_mode = "lidar+camera"
        elif ground_obstacles:
            sensor_mode = "lidar"
        elif height_obstacles:
            sensor_mode = "camera"
        
        # Usa dados do LiDAR se disponível
        if ground_obstacles:
            obstacles_combined['left'] |= ground_obstacles['left']
            obstacles_combined['center'] |= ground_obstacles['center']
            obstacles_combined['right'] |= ground_obstacles['right']
            distances['left'] = min(distances['left'], ground_obstacles['distances']['left'])
            distances['center'] = min(distances['center'], ground_obstacles['distances']['center'])
            distances['right'] = min(distances['right'], ground_obstacles['distances']['right'])
        
        # Usa dados da câmera D435 para detectar objetos
        if height_obstacles:
            obstacles_combined['left'] |= height_obstacles['left']
            obstacles_combined['center'] |= height_obstacles['center']
            obstacles_combined['right'] |= height_obstacles['right']
            distances['left'] = min(distances['left'], height_obstacles['distances']['left'])
            distances['center'] = min(distances['center'], height_obstacles['distances']['center'])
            distances['right'] = min(distances['right'], height_obstacles['distances']['right'])
        
        # Se não tem nenhum sensor ativo, retorna parado
        if not ground_obstacles and not height_obstacles:
            print("⚠ Nenhum sensor ativo - mantendo parado")
            return 'stop', 0, {}
        
        # Log detalhado da detecção
        detection_info = {
            'mode': sensor_mode,
            'obstacles': obstacles_combined.copy(),
            'distances': distances.copy()
        }
        
        # Decisão de movimento baseada nos obstáculos detectados
        if sensor_mode == "camera":
            print(f"🎥 [CÂMERA D435] ", end="")
        elif sensor_mode == "lidar":
            print(f"📡 [LIDAR L515] ", end="")
        else:
            print(f"🎥📡 [DUAL] ", end="")
        
        # Lógica de navegação com velocidade configurável
        if not obstacles_combined['center']:
            # Caminho livre à frente - avançar
            speed = int(self.base_speed * 1.0)  # Velocidade cheia
            print(f"➡️ Livre! Avançando (dist: {distances['center']:.2f}m, vel: {speed})")
            return 'forward', speed, detection_info
        elif not obstacles_combined['right']:
            # Obstáculo no centro, desviar para direita
            speed = int(self.base_speed * 0.8)  # 80% da velocidade
            print(f"↪ OBJETO DETECTADO! Desviando direita (dist centro: {distances['center']:.2f}m, vel: {speed})")
            return 'right', speed, detection_info
        elif not obstacles_combined['left']:
            # Obstáculo no centro e direita, desviar para esquerda
            speed = int(self.base_speed * 0.8)  # 80% da velocidade
            print(f"↩ OBJETO DETECTADO! Desviando esquerda (dist centro: {distances['center']:.2f}m, vel: {speed})")
            return 'left', speed, detection_info
        else:
            # Obstáculos em todos os lados - recuar
            speed = int(self.base_speed * 0.6)  # 60% da velocidade
            print(f"⬅ OBJETOS EM VOLTA! Recuando (vel: {speed})")
            return 'backward', speed, detection_info


class RobotController:
    """Controla o robô via Arduino"""
    
    def __init__(self):
        self.serial_port = None
        self.speed = 150
        
    def connect(self, port):
        """Conecta ao Arduino"""
        try:
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            print(f"✓ Conectado ao Arduino na porta {port}")
            return True
        except Exception as e:
            print(f"✗ Erro ao conectar: {e}")
            return False
    
    def send_command(self, m1, m2, m3):
        """Envia comando para o Arduino"""
        if not self.serial_port:
            return False
            
        command = f"{m1},{m2},{m3}\n"
        try:
            self.serial_port.write(command.encode())
            return True
        except Exception as e:
            print(f"✗ Erro ao enviar comando: {e}")
            return False
    
    def move(self, direction, speed):
        """Move o robô na direção especificada"""
        # Configuração correta para robô omnidirecional de 3 rodas
        if direction == 'forward':
            # Frente: M1=0, M2=-velocidade, M3=velocidade
            return self.send_command(0, -speed, speed)
        elif direction == 'backward':
            # Trás: M1=0, M2=velocidade, M3=-velocidade
            return self.send_command(0, speed, -speed)
        elif direction == 'left':
            # Esquerda: M1=velocidade, M2=-velocidade, M3=velocidade
            return self.send_command(speed, -speed, speed)
        elif direction == 'right':
            # Direita: M1=-velocidade, M2=-velocidade, M3=velocidade
            return self.send_command(-speed, -speed, speed)
        elif direction == 'stop':
            return self.send_command(0, 0, 0)
        return False
    
    def get_available_ports(self):
        """Lista portas seriais disponíveis"""
        try:
            ports = serial.tools.list_ports.comports()
            port_list = []
            
            print("\n=== Buscando Portas Seriais ===")
            if not ports:
                print("✗ Nenhuma porta serial encontrada!")
                print("  Verifique se o Arduino está conectado via USB")
                print("  No Linux, execute: ls -la /dev/ttyACM* /dev/ttyUSB*")
                print("  Pode ser necessário adicionar seu usuário ao grupo 'dialout':")
                print("  sudo usermod -a -G dialout $USER")
                print("  (depois, faça logout e login novamente)")
                return []
            
            for port in ports:
                print(f"  ✓ Encontrada: {port.device}")
                print(f"    Descrição: {port.description}")
                print(f"    Fabricante: {port.manufacturer if port.manufacturer else 'N/A'}")
                port_list.append(port.device)
            
            print(f"\nTotal: {len(port_list)} porta(s) disponível(is)")
            return port_list
            
        except Exception as e:
            print(f"✗ Erro ao listar portas: {e}")
            import traceback
            traceback.print_exc()
            return []


class WebSocketServer:
    """Servidor WebSocket para comunicação com interface web"""
    
    def __init__(self, robot_controller, realsense_controller, obstacle_detector, navigator):
        self.robot = robot_controller
        self.sensors = realsense_controller
        self.detector = obstacle_detector
        self.navigator = navigator
        self.tracker = ObjectTracker()
        self.clients = set()
        self.autonomous_mode = False
        self.running = True
        
    async def register(self, websocket):
        """Registra novo cliente"""
        self.clients.add(websocket)
        print(f"✓ Cliente conectado. Total: {len(self.clients)}")
        
    async def unregister(self, websocket):
        """Remove cliente"""
        self.clients.remove(websocket)
        print(f"✗ Cliente desconectado. Total: {len(self.clients)}")
    
    async def send_to_all(self, message):
        """Envia mensagem para todos os clientes"""
        if self.clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_client(self, websocket):
        """Gerencia comunicação com cliente"""
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.process_command(data)
        finally:
            await self.unregister(websocket)
    
    async def process_command(self, data):
        """Processa comandos recebidos"""
        cmd_type = data.get('type')
        
        if cmd_type == 'discover_ports':
            # Descobre portas seriais disponíveis
            print("\n📡 Requisição de descoberta de portas recebida")
            ports = self.robot.get_available_ports()
            print(f"   Enviando {len(ports)} porta(s) para o cliente\n")
            await self.send_to_all({'type': 'ports_list', 'ports': ports})
            
        elif cmd_type == 'connect_serial':
            # Conecta ao Arduino na porta especificada
            port = data.get('port')
            print(f"\n🔌 Tentando conectar ao Arduino na porta {port}...")
            success = self.robot.connect(port)
            if success:
                print(f"   ✓ Arduino conectado com sucesso em {port}")
            else:
                print(f"   ✗ Falha ao conectar ao Arduino em {port}")
            await self.send_to_all({
                'type': 'serial_status', 
                'connected': success,
                'port': port if success else None
            })
            
        elif cmd_type == 'move':
            # Comandos de movimento diretos (m1, m2, m3)
            if 'm1' in data and 'm2' in data and 'm3' in data:
                # Comando direto dos controles
                self.robot.send_command(data['m1'], data['m2'], data['m3'])
            else:
                # Comando por direção (compatibilidade)
                direction = data.get('direction')
                speed = data.get('speed', 150)
                self.robot.move(direction, speed)
            
        elif cmd_type == 'set_autonomous':
            self.autonomous_mode = data.get('enabled', False)
            speed = data.get('speed', 100)
            self.navigator.base_speed = speed
            print(f"\n🤖 Modo autônomo: {'ATIVADO' if self.autonomous_mode else 'DESATIVADO'}")
            print(f"   Velocidade base: {speed}")
            await self.send_to_all({'type': 'autonomous_status', 'enabled': self.autonomous_mode})
        
        elif cmd_type == 'set_autonomous_speed':
            speed = data.get('speed', 100)
            self.navigator.base_speed = speed
            print(f"\n⚡ Velocidade autônoma alterada: {speed}")
    
    async def sensor_loop(self):
        """Loop principal de processamento dos sensores"""
        frame_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 20
        
        while self.running:
            try:
                frame_count += 1
                
                # Obtém dados dos sensores
                lidar_data = self.sensors.get_lidar_data()  # Obstáculos no chão
                color_image, camera_depth = self.sensors.get_camera_data()  # Altura dos objetos
                
                # Verifica se conseguiu dados
                if lidar_data is None and color_image is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"\n✗ Muitos erros consecutivos ({consecutive_errors})")
                        print("  Os sensores podem estar desconectados")
                        consecutive_errors = 0
                    await asyncio.sleep(0.5)
                    continue
                else:
                    consecutive_errors = 0
                
                # Detecta obstáculos
                ground_obstacles = None
                height_obstacles = None
                
                if lidar_data is not None:
                    ground_obstacles = self.detector.analyze_lidar(lidar_data)
                
                if camera_depth is not None:
                    height_obstacles = self.detector.analyze_height(camera_depth)
                
                # Navegação autônoma - detecção de objetos pela câmera D435
                navigation_status = None
                if self.autonomous_mode:
                    # Se tem pelo menos um sensor com dados de obstáculos
                    if ground_obstacles or height_obstacles:
                        # Indica modo de operação (apenas primeira vez ou a cada 50 frames)
                        if frame_count == 1 or frame_count % 50 == 0:
                            if height_obstacles and not ground_obstacles:
                                print("\n🎥 [NAVEGAÇÃO AUTÔNOMA ATIVA] Detectando objetos com câmera D435")
                                print("   ↳ Desviando automaticamente de obstáculos")
                            elif ground_obstacles and not height_obstacles:
                                print("\n📡 [NAVEGAÇÃO AUTÔNOMA ATIVA] Detectando obstáculos com LiDAR L515")
                            else:
                                print("\n🎥📡 [NAVEGAÇÃO AUTÔNOMA ATIVA] Sensores combinados")
                        
                        direction, speed, detection_info = self.navigator.decide_movement(ground_obstacles, height_obstacles)
                        self.robot.move(direction, speed)
                        
                        # Cria status de navegação para interface
                        navigation_status = {
                            'active': True,
                            'direction': direction,
                            'speed': speed,
                            'detection': detection_info
                        }
                    else:
                        # Sem sensores ativos no modo autônomo - para por segurança
                        if frame_count % 20 == 0:
                            print("⚠ Modo autônomo ativo mas nenhum sensor com dados - parado")
                        self.robot.move('stop', 0)
                        navigation_status = {
                            'active': False,
                            'reason': 'no_sensor_data'
                        }
                else:
                    navigation_status = {
                        'active': False,
                        'reason': 'manual_mode'
                    }
                
                # Prepara dados para enviar
                message = {
                    'type': 'sensor_data',
                    'timestamp': asyncio.get_event_loop().time(),
                    'ground_obstacles': ground_obstacles,
                    'height_obstacles': height_obstacles,
                    'navigation_status': navigation_status
                }
                
                # Envia frame do LiDAR como imagem de profundidade
                if lidar_data is not None:
                    # Normaliza dados de profundidade para visualização (0-255)
                    depth_normalized = cv2.normalize(lidar_data, None, 0, 255, cv2.NORM_MINMAX)
                    depth_colored = cv2.applyColorMap(depth_normalized.astype(np.uint8), cv2.COLORMAP_JET)
                    
                    # Envia imagem colorida do LiDAR
                    _, lidar_buffer = cv2.imencode('.jpg', depth_colored, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    lidar_image_base64 = base64.b64encode(lidar_buffer).decode('utf-8')
                    message['lidar_image'] = lidar_image_base64
                
                # Tracking de objetos e envio do frame da câmera
                if color_image is not None:
                    # Detecta e rastreia objetos usando dados de profundidade
                    detected = self.tracker.detect_objects(camera_depth)
                    tracked_objects = self.tracker.update(detected)
                    
                    if tracked_objects:
                        message['tracked_objects'] = tracked_objects
                    
                    # Envia frame da câmera (comprimido)
                    _, buffer = cv2.imencode('.jpg', color_image, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    image_base64 = base64.b64encode(buffer).decode('utf-8')
                    message['camera'] = image_base64
                
                # Reconstrução 3D em tempo real (envia sempre que tiver dados)
                if lidar_data is not None:
                    # Só envia a cada 5 frames para otimização
                    if frame_count % 5 == 0:
                        pcd = self.sensors.create_point_cloud(lidar_data, None)
                        if pcd is not None:
                            # Serializa nuvem de pontos simplificada
                            points = np.asarray(pcd.points)
                            colors = np.asarray(pcd.colors)
                            
                            # Amostragem para reduzir tamanho
                            if len(points) > 1500:
                                indices = np.random.choice(len(points), 1500, replace=False)
                                points = points[indices]
                                colors = colors[indices]
                            
                            if len(points) > 0:
                                message['point_cloud'] = {
                                    'points': points.tolist(),
                                    'colors': colors.tolist()
                                }
                
                await self.send_to_all(message)
            except Exception as e:
                print(f"Erro no loop de sensores: {e}")
                consecutive_errors += 1
            
            await asyncio.sleep(0.1)  # 10 Hz
    
    async def start_server(self, host='localhost', port=8765):
        """Inicia o servidor WebSocket"""
        async with websockets.serve(self.handle_client, host, port):
            print(f"✓ Servidor WebSocket rodando em ws://{host}:{port}")
            # Inicia loop de sensores
            await self.sensor_loop()


def main():
    """Função principal"""
    print("=== Sistema de Controle Autônomo ===\n")
    
    # Inicializa componentes
    print("Inicializando sensores...")
    sensors = RealSenseController()
    if not sensors.start():
        print("\n⚠ ATENÇÃO: Nenhum sensor foi iniciado com sucesso!")
        print("  O sistema continuará rodando para controle manual")
        print("  Mas a navegação autônoma não funcionará corretamente\n")
    
    # Verifica quais sensores estão ativos
    print("\nStatus dos sensores:")
    print(f"  LiDAR L515: {'✓ ATIVO' if sensors.lidar_started else '✗ OFFLINE (navegação funcionará apenas com câmera)'}")
    print(f"  Câmera D435: {'✓ ATIVO' if sensors.camera_started else '✗ OFFLINE'}")
    
    if sensors.camera_started and not sensors.lidar_started:
        print("\n💡 MODO: Navegação autônoma usando APENAS câmera D435")
        print("   O robô detectará obstáculos baseado em profundidade da câmera")
    elif sensors.lidar_started and sensors.camera_started:
        print("\n💡 MODO: Navegação autônoma com ambos sensores (ideal)")
    
    detector = ObstacleDetector(safe_distance=1.2)
    navigator = AutonomousNavigator(detector)
    robot = RobotController()
    
    # Inicia servidor WebSocket
    server = WebSocketServer(robot, sensors, detector, navigator)
    
    print("\n✓ Sistema pronto para uso!")
    print("  - Acesse a interface web em http://localhost:5173")
    print("  - Use os controles para mover o robô manualmente")
    print("  - Ative o modo autônomo para navegação com desvio de obstáculos\n")
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        print("\n\nEncerrando sistema...")
        sensors.stop()
        if robot.serial_port:
            robot.move('stop', 0)
        print("✓ Sistema encerrado")


if __name__ == "__main__":
    main()
