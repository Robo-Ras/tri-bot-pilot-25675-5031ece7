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

# Tenta importar sistema YOLO (opcional)
try:
    from robot_tracking_system import MultiCameraTracker
    YOLO_AVAILABLE = True
    print("✓ Sistema YOLO disponível")
except:
    YOLO_AVAILABLE = False
    print("⚠ Sistema YOLO não disponível - usando tracking básico")

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
        """Lista todos os dispositivos RealSense conectados (modo compatível)"""
        try:
            ctx = rs.context()
            devices = list(ctx.devices)  # MESMA ABORDAGEM DO SEU SCRIPT QUE FUNCIONA
            print("\n=== Dispositivos RealSense Detectados ===")
            
            if len(devices) == 0:
                print("✗ Nenhum dispositivo RealSense encontrado!")
                print("  Verifique se os sensores estão conectados via USB")
                print("  Execute: lsusb | grep Intel")
                return []
            
            device_list = []
            for idx, dev in enumerate(devices, start=1):
                try:
                    name = dev.get_info(rs.camera_info.name)
                    serial = dev.get_info(rs.camera_info.serial_number)
                    firmware = dev.get_info(rs.camera_info.firmware_version)
                    product_line = dev.get_info(rs.camera_info.product_line)
                    
                    print(f"{idx}. {name}")
                    print(f"   Serial: {serial}")
                    print(f"   Firmware: {firmware}")
                    print(f"   Linha de Produto: {product_line}")
                    
                    device_list.append({
                        'name': name,
                        'serial': serial,
                        'product_line': product_line,
                    })
                except Exception as e:
                    print(f"  Erro ao acessar dispositivo {idx}: {e}")
                    continue
            
            return device_list
        except Exception as e:
            print("\n✗ Erro ao listar dispositivos RealSense (ctx.devices):", e)
            print("  Tente desconectar e reconectar os sensores USB ou reiniciar o PC")
            return []
    
    def identify_devices(self):
        """Identifica qual é o LiDAR e qual é a câmera"""
        devices = self.list_devices()
        
        if not devices:
            print("\n✗ Nenhum dispositivo encontrado")
            return False
        
        print("\n=== Identificando Dispositivos ===")
        
        for device in devices:
            name = device['name']
            serial = device['serial']
            product_line = device['product_line']
            
            if 'L515' in name or 'L515' in product_line:
                self.lidar_serial = serial
                print(f"✓ LiDAR L515 identificado: {serial}")
            elif 'D435' in name or 'D435' in product_line:
                self.camera_serial = serial
                print(f"✓ Câmera D435 identificada: {serial}")
        
        if self.lidar_serial:
            print(f"\n✓ LiDAR configurado: Serial {self.lidar_serial}")
        else:
            print("\n✗ LiDAR NÃO ENCONTRADO")
        
        if self.camera_serial:
            print(f"✓ Câmera configurada: Serial {self.camera_serial}")
        else:
            print("✗ Câmera NÃO ENCONTRADA")
        
        return self.lidar_serial is not None or self.camera_serial is not None
    
    def start(self):
        """Inicia os sensores"""
        print("\nLimpando recursos anteriores...")
        self.cleanup()
        
        if not self.identify_devices():
            print("✗ Nenhum dispositivo RealSense disponível!")
            return False
        
        # Inicia LiDAR se disponível
        if self.lidar_serial:
            try:
                print(f"\n🔄 Iniciando LiDAR L515 (Serial: {self.lidar_serial})...")
                
                ctx = rs.context()
                self.pipeline_lidar = rs.pipeline(ctx)
                config_lidar = rs.config()
                config_lidar.enable_device(self.lidar_serial)
                
                print("  Iniciando pipeline com configuração padrão...")
                profile = self.pipeline_lidar.start(config_lidar)
                
                print("  ✓ Pipeline iniciado!")
                
                depth_stream = profile.get_stream(rs.stream.depth)
                if depth_stream:
                    vp = depth_stream.as_video_stream_profile()
                    print(f"  Stream de profundidade ativo:")
                    print(f"    Resolução: {vp.width()}x{vp.height()}")
                    print(f"    FPS: {vp.fps()}")
                    print(f"    Formato: {vp.format()}")
                
                # Testa aquisição de frames
                print("  Testando aquisição de frames...")
                for i in range(5):
                    frames = self.pipeline_lidar.wait_for_frames(timeout_ms=5000)
                    depth = frames.get_depth_frame()
                    if depth:
                        print(f"    Frame {i+1}/5: ✓ {depth.get_width()}x{depth.get_height()}")
                    else:
                        print(f"    Frame {i+1}/5: ✗ falhou")
                
                self.lidar_started = True
                print("✓✓✓ LiDAR L515 INICIADO COM SUCESSO!\n")
                
            except Exception as e:
                print(f"\n✗✗✗ ERRO ao iniciar LiDAR: {str(e)}")
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
            print("⚠ LiDAR não será iniciado (serial não identificado)")
        
        # Inicia Câmera se disponível
        if self.camera_serial:
            try:
                print(f"\n🔄 Iniciando Câmera D435 (Serial: {self.camera_serial})...")
                
                if self.pipeline_camera:
                    try:
                        self.pipeline_camera.stop()
                    except:
                        pass
                
                self.pipeline_camera = rs.pipeline()
                config_camera = rs.config()
                config_camera.enable_device(self.camera_serial)
                config_camera.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
                config_camera.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
                
                profile = self.pipeline_camera.start(config_camera)
                
                color_stream = profile.get_stream(rs.stream.color)
                depth_stream = profile.get_stream(rs.stream.depth)
                
                print(f"  ✓ Streams ativos:")
                if color_stream:
                    print(f"    Color: {color_stream.as_video_stream_profile().width()}x{color_stream.as_video_stream_profile().height()}")
                if depth_stream:
                    print(f"    Depth: {depth_stream.as_video_stream_profile().width()}x{depth_stream.as_video_stream_profile().height()}")
                
                # Testa frames
                print("  Testando aquisição de frames...")
                for i in range(3):
                    frames = self.pipeline_camera.wait_for_frames(timeout_ms=2000)
                    if frames.get_color_frame() and frames.get_depth_frame():
                        print(f"    Frame {i+1}/3: ✓")
                    else:
                        print(f"    Frame {i+1}/3: ✗")
                
                self.camera_started = True
                print("✓✓✓ CÂMERA D435 INICIADA COM SUCESSO!\n")
                
            except Exception as e:
                print(f"\n✗✗✗ ERRO ao iniciar câmera: {str(e)}")
                import traceback
                traceback.print_exc()
                if self.pipeline_camera:
                    try:
                        self.pipeline_camera.stop()
                    except:
                        pass
                self.pipeline_camera = None
                self.camera_started = False
        else:
            print("⚠ Câmera não será iniciada (serial não identificado)")
        
        print(f"\n{'='*50}")
        print("STATUS FINAL:")
        print(f"  LiDAR: {'✓ FUNCIONANDO' if self.lidar_started else '✗ OFFLINE'}")
        print(f"  Câmera: {'✓ FUNCIONANDO' if self.camera_started else '✗ OFFLINE'}")
        
        if self.camera_started and not self.lidar_started:
            print(f"\n⚠️  MODO: NAVEGAÇÃO APENAS COM CÂMERA D435")
        elif self.lidar_started and not self.camera_started:
            print(f"\n⚠️  MODO: NAVEGAÇÃO APENAS COM LIDAR L515")
        
        print(f"{'='*50}\n")
        
        if self.camera_started or self.lidar_started:
            if self.camera_started:
                print("✓✓✓ SISTEMA PRONTO PARA NAVEGAÇÃO AUTÔNOMA")
            return True
        else:
            print("✗✗✗ FALHA: Nenhum sensor disponível")
            return False
    
    def get_lidar_data(self):
        """Obtém dados do LiDAR"""
        if not self.lidar_started or not self.pipeline_lidar:
            return None
        
        try:
            frames = self.pipeline_lidar.wait_for_frames(timeout_ms=1000)
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                return None
            
            depth_image = np.asanyarray(depth_frame.get_data())
            return depth_image
        except Exception as e:
            print(f"Erro ao obter dados do LiDAR: {e}")
            return None
    
    def get_camera_data(self):
        """Obtém dados da câmera"""
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
    
    def stop(self):
        """Para todos os sensores"""
        self.cleanup()


class ObjectTracker:
    """Rastreia objetos detectados pela câmera"""
    
    def __init__(self, max_disappeared=10, min_area=5000, max_distance=2.0, min_distance=0.5):
        self.next_object_id = 0
        self.objects = {}
        self.disappeared = {}
        self.centroids = {}
        self.max_disappeared = max_disappeared
        self.min_area = min_area
        self.max_distance = max_distance
        self.min_distance = min_distance
        self.frame_counter = 0
        self.stable_frames = 3
        self.candidate_objects = {}
        
    def detect_objects(self, depth_image, depth_scale=0.001):
        """Detecta objetos usando dados de profundidade"""
        if depth_image is None:
            return []
        
        depth_meters = depth_image.astype(float) * depth_scale
        valid_mask = (depth_meters > self.min_distance) & (depth_meters < self.max_distance)
        
        if not np.any(valid_mask):
            return []
        
        depth_normalized = ((depth_meters - self.min_distance) / 
                          (self.max_distance - self.min_distance) * 255).astype(np.uint8)
        depth_normalized[~valid_mask] = 0
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        depth_clean = cv2.morphologyEx(depth_normalized, cv2.MORPH_CLOSE, kernel)
        depth_clean = cv2.morphologyEx(depth_clean, cv2.MORPH_OPEN, kernel)
        
        _, binary = cv2.threshold(depth_clean, 30, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            roi = depth_meters[y:y+h, x:x+w]
            valid_depths = roi[roi > 0]
            
            if len(valid_depths) < 100:
                continue
            if valid_depths.std() > 0.3:
                continue
            
            bbox_area = w * h
            fill_ratio = area / bbox_area if bbox_area > 0 else 0
            if fill_ratio < 0.3:
                continue
            
            cx = x + w // 2
            cy = y + h // 2
            avg_depth = np.median(valid_depths)
            
            detected.append({
                'bbox': (x, y, x+w, y+h),
                'centroid': (cx, cy),
                'depth': avg_depth,
                'area': area
            })
        
        return detected
    
    def update(self, depth_image, depth_scale=0.001):
        """Atualiza rastreamento com novo frame"""
        self.frame_counter += 1
        detections = self.detect_objects(depth_image, depth_scale)
        
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    del self.objects[object_id]
                    del self.disappeared[object_id]
                    del self.centroids[object_id]
            return
        
        input_centroids = np.array([d['centroid'] for d in detections])
        
        if len(self.objects) == 0:
            for detection in detections:
                centroid = detection['centroid']
                if centroid not in self.candidate_objects:
                    self.candidate_objects[centroid] = {'count': 1, 'data': detection}
                else:
                    self.candidate_objects[centroid]['count'] += 1
                    if self.candidate_objects[centroid]['count'] >= self.stable_frames:
                        self._register(detection)
                        del self.candidate_objects[centroid]
        else:
            object_ids = list(self.objects.keys())
            object_centroids = np.array([self.centroids[oid] for oid in object_ids])
            
            D = distance.cdist(object_centroids, input_centroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > 100:
                    continue
                
                object_id = object_ids[row]
                detection = detections[col]
                
                self.objects[object_id] = detection
                self.centroids[object_id] = detection['centroid']
                self.disappeared[object_id] = 0
                
                used_rows.add(row)
                used_cols.add(col)
            
            unused_rows = set(range(D.shape[0])) - used_rows
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    del self.objects[object_id]
                    del self.disappeared[object_id]
                    del self.centroids[object_id]
            
            unused_cols = set(range(D.shape[1])) - used_cols
            for col in unused_cols:
                detection = detections[col]
                centroid = detection['centroid']
                if centroid not in self.candidate_objects:
                    self.candidate_objects[centroid] = {'count': 1, 'data': detection}
                else:
                    self.candidate_objects[centroid]['count'] += 1
                    if self.candidate_objects[centroid]['count'] >= self.stable_frames:
                        self._register(detection)
                        del self.candidate_objects[centroid]
    
    def _register(self, detection):
        """Registra novo objeto"""
        self.objects[self.next_object_id] = detection
        self.centroids[self.next_object_id] = detection['centroid']
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1
    
    def get_tracked_objects(self):
        """Retorna objetos rastreados"""
        return [
            {
                'id': str(obj_id),
                'bbox': self.objects[obj_id]['bbox'],
                'centroid': self.centroids[obj_id],
                'depth': self.objects[obj_id]['depth'],
                'area': self.objects[obj_id]['area']
            }
            for obj_id in self.objects.keys()
        ]


class ObstacleDetector:
    """Detecta obstáculos usando dados dos sensores"""
    
    def __init__(self, safe_distance=0.5, height_threshold=1.5):
        self.safe_distance = safe_distance
        self.height_threshold = height_threshold
        
    def analyze_lidar(self, depth_image):
        """Analisa dados do LiDAR para obstáculos no chão"""
        if depth_image is None:
            return None
        
        height, width = depth_image.shape
        depth_meters = depth_image.astype(float) * 0.001
        
        third = width // 3
        left_region = depth_meters[:, :third]
        center_region = depth_meters[:, third:2*third]
        right_region = depth_meters[:, 2*third:]
        
        def check_region(region):
            valid = region[(region > 0) & (region < 10)]
            if len(valid) > 0:
                min_dist = np.min(valid)
                return {
                    'blocked': min_dist < self.safe_distance,
                    'distance': float(min_dist)
                }
            return {'blocked': False, 'distance': 10.0}
        
        left_status = check_region(left_region)
        center_status = check_region(center_region)
        right_status = check_region(right_region)
        
        return {
            'left': left_status['blocked'],
            'center': center_status['blocked'],
            'right': right_status['blocked'],
            'distances': {
                'left': left_status['distance'],
                'center': center_status['distance'],
                'right': right_status['distance']
            },
            'sensor': 'L515'
        }
    
    def analyze_height(self, depth_image, depth_scale=0.001):
        """Analisa altura dos obstáculos usando câmera"""
        if depth_image is None:
            return None
        
        height, width = depth_image.shape
        depth_meters = depth_image.astype(float) * depth_scale
        
        roi_top = int(height * 0.3)
        roi_bottom = int(height * 0.7)
        roi = depth_meters[roi_top:roi_bottom, :]
        
        third = width // 3
        left_region = roi[:, :third]
        center_region = roi[:, third:2*third]
        right_region = roi[:, 2*third:]
        
        def check_height_region(region):
            valid = region[(region > 0.1) & (region < 3.0)]
            if len(valid) > 100:
                min_dist = np.min(valid)
                return {
                    'blocked': min_dist < 0.8,
                    'distance': float(min_dist)
                }
            return {'blocked': False, 'distance': 3.0}
        
        left_status = check_height_region(left_region)
        center_status = check_height_region(center_region)
        right_status = check_height_region(right_region)
        
        return {
            'left': left_status['blocked'],
            'center': center_status['blocked'],
            'right': right_status['blocked'],
            'distances': {
                'left': left_status['distance'],
                'center': center_status['distance'],
                'right': right_status['distance']
            },
            'sensor': 'D435'
        }


class AutonomousNavigator:
    """Sistema de navegação autônoma"""
    
    def __init__(self):
        self.current_state = 'moving'
        self.base_speed = 100
        self.move_counter = 0
        self.rotation_counter = 0
        self.free_path_counter = 0
        self.max_moves_before_rotation = 8
        self.rotation_steps = 3
        
    def decide_movement(self, ground_obstacles, height_obstacles):
        """Decide próximo movimento"""
        distances = {
            'left': 10.0,
            'center': 10.0,
            'right': 10.0
        }
        
        sensor_mode = "none"
        if ground_obstacles and height_obstacles:
            sensor_mode = "both"
        elif ground_obstacles:
            sensor_mode = "lidar"
        elif height_obstacles:
            sensor_mode = "camera"
        
        if ground_obstacles:
            distances['left'] = min(distances['left'], ground_obstacles['distances']['left'])
            distances['center'] = min(distances['center'], ground_obstacles['distances']['center'])
            distances['right'] = min(distances['right'], ground_obstacles['distances']['right'])
        
        if height_obstacles:
            distances['left'] = min(distances['left'], height_obstacles['distances']['left'])
            distances['center'] = min(distances['center'], height_obstacles['distances']['center'])
            distances['right'] = min(distances['right'], height_obstacles['distances']['right'])
        
        if not ground_obstacles and not height_obstacles:
            return 'stop', 0, {}
        
        detection_info = {
            'mode': sensor_mode,
            'state': self.current_state,
            'distances': distances.copy(),
            'free_moves': self.free_path_counter
        }
        
        # Estado de rotação
        if self.current_state == 'rotating':
            self.rotation_counter += 1
            speed = int(self.base_speed * 0.6)
            
            if self.rotation_counter <= self.rotation_steps:
                return 'rotate_right', speed, detection_info
            else:
                self.rotation_counter = 0
                self.free_path_counter = 0
                self.current_state = 'moving'
                return 'stop', 0, detection_info
        
        # Estado de movimento
        elif self.current_state == 'moving':
            self.move_counter += 1
            
            obstacle_detected = (
                distances['center'] < 0.8 or 
                distances['left'] < 0.6 or 
                distances['right'] < 0.6
            )
            
            if obstacle_detected:
                self.free_path_counter = 0
                
                if distances['center'] < 0.8:
                    if distances['right'] > distances['left'] and distances['right'] > 0.8:
                        speed = int(self.base_speed * 0.7)
                        return 'right', speed, detection_info
                    elif distances['left'] > 0.8:
                        speed = int(self.base_speed * 0.7)
                        return 'left', speed, detection_info
                    else:
                        speed = int(self.base_speed * 0.6)
                        return 'backward', speed, detection_info
                
                elif distances['left'] < 0.6:
                    speed = int(self.base_speed * 0.6)
                    return 'right', speed, detection_info
                
                elif distances['right'] < 0.6:
                    speed = int(self.base_speed * 0.6)
                    return 'left', speed, detection_info
            
            else:
                self.free_path_counter += 1
                
                if self.free_path_counter >= self.max_moves_before_rotation:
                    self.current_state = 'rotating'
                    self.rotation_counter = 0
                    return 'stop', 0, detection_info
                else:
                    speed = int(self.base_speed * 0.8)
                    return 'forward', speed, detection_info
        
        return 'stop', 0, detection_info


class RobotController:
    """Controla o robô via Arduino"""
    
    def __init__(self):
        self.serial_port = None
        self.speed = 150
        
    def connect(self, port):
        """Conecta ao Arduino"""
        try:
            if self.serial_port:
                self.serial_port.close()
            
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            print(f"✓ Conectado ao Arduino na porta {port}")
            return True
        except Exception as e:
            print(f"✗ Erro ao conectar: {e}")
            return False
    
    def is_connected(self):
        """Verifica se está conectado"""
        return self.serial_port is not None and self.serial_port.is_open
    
    def send_command(self, m1, m2, m3):
        """Envia comando direto para os motores"""
        if not self.is_connected():
            return False
        
        try:
            command = f"{m1},{m2},{m3}\n"
            self.serial_port.write(command.encode())
            return True
        except Exception as e:
            print(f"✗ Erro ao enviar comando: {e}")
            return False
    
    def move(self, direction, speed):
        """Move o robô em uma direção"""
        commands = {
            'forward': (0, -speed, speed),
            'backward': (0, speed, -speed),
            'left': (speed, -speed, speed),
            'right': (-speed, -speed, speed),
            'rotate_right': (-speed, -speed, -speed),
            'stop': (0, 0, 0)
        }
        
        if direction in commands:
            m1, m2, m3 = commands[direction]
            return self.send_command(m1, m2, m3)
        return False
    
    def get_available_ports(self):
        """Lista portas seriais disponíveis"""
        try:
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except Exception as e:
            print(f"✗ Erro ao listar portas: {e}")
            return []


class WebSocketServer:
    """Servidor WebSocket para comunicação com interface web"""
    
    def __init__(self, robot_controller, realsense_controller, obstacle_detector, navigator):
        self.robot = robot_controller
        self.sensors = realsense_controller
        self.detector = obstacle_detector
        self.navigator = navigator
        
        # Tracking
        if YOLO_AVAILABLE:
            self.yolo_tracker = MultiCameraTracker()
            self.use_yolo = False
        else:
            self.yolo_tracker = None
            self.use_yolo = False
        
        self.basic_tracker = ObjectTracker()
        
        self.clients = set()
        self.autonomous_mode = False
        self.running = True
        self.tablet_connected = False
        self.robot_moving = False
        
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
            ports = self.robot.get_available_ports()
            await self.send_to_all({'type': 'ports_list', 'ports': ports})
            
        elif cmd_type == 'connect_serial':
            port = data.get('port')
            success = self.robot.connect(port)
            await self.send_to_all({
                'type': 'serial_status', 
                'connected': success,
                'port': port if success else None
            })
            
        elif cmd_type == 'move':
            if 'm1' in data and 'm2' in data and 'm3' in data:
                self.robot.send_command(data['m1'], data['m2'], data['m3'])
                self.robot_moving = any([data['m1'] != 0, data['m2'] != 0, data['m3'] != 0])
            else:
                direction = data.get('direction')
                speed = data.get('speed', 150)
                self.robot.move(direction, speed)
                self.robot_moving = direction != 'stop'
            
        elif cmd_type == 'set_autonomous':
            self.autonomous_mode = data.get('enabled', False)
            speed = data.get('speed', 100)
            self.navigator.base_speed = speed
            await self.send_to_all({'type': 'autonomous_status', 'enabled': self.autonomous_mode})
        
        elif cmd_type == 'set_autonomous_speed':
            speed = data.get('speed', 100)
            self.navigator.base_speed = speed
        
        elif cmd_type == 'toggle_yolo':
            if self.yolo_tracker:
                self.use_yolo = data.get('enabled', False)
                if self.use_yolo:
                    success = self.yolo_tracker.find_and_start_cameras()
                    if not success:
                        self.use_yolo = False
                        await self.send_to_all({
                            'type': 'yolo_status',
                            'enabled': False,
                            'error': 'Falha ao iniciar câmeras'
                        })
                        return
                else:
                    self.yolo_tracker.cleanup()
                
                await self.send_to_all({'type': 'yolo_status', 'enabled': self.use_yolo})
        
        elif cmd_type == 'robot_face_heartbeat':
            self.tablet_connected = True
    
    async def sensor_loop(self):
        """Loop principal de leitura dos sensores"""
        print("\n🔄 Iniciando loop de sensores...")
        last_tablet_check = asyncio.get_event_loop().time()
        
        while self.running:
            try:
                loop_start = asyncio.get_event_loop().time()
                
                if loop_start - last_tablet_check > 5:
                    self.tablet_connected = False
                    last_tablet_check = loop_start
                
                message = {
                    'type': 'sensor_data',
                    'timestamp': loop_start,
                    'tablet_connected': self.tablet_connected,
                    'robot_moving': self.robot_moving
                }
                
                # MODO YOLO
                if self.use_yolo and self.yolo_tracker:
                    try:
                        camera_frames = self.yolo_tracker.process_frame()
                        tracked_objects = self.yolo_tracker.get_tracked_objects()
                        
                        for camera_name, data in camera_frames.items():
                            annotated = data['annotated']
                            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            image_b64 = base64.b64encode(buffer).decode('utf-8')
                            message[f'{camera_name.lower()}_image'] = image_b64
                        
                        message['tracked_objects'] = tracked_objects
                        message['tracking_mode'] = 'yolo'
                    except KeyboardInterrupt:
                        raise  # Permite Ctrl+C
                    except Exception as e:
                        print(f"❌ Erro no YOLO tracking: {e}")
                        import traceback
                        traceback.print_exc()
                        message['tracking_mode'] = 'error'
                
                # MODO BÁSICO
                else:
                    if self.sensors.camera_started:
                        color_image, depth_image = self.sensors.get_camera_data()
                        
                        if color_image is not None:
                            self.basic_tracker.update(depth_image, 0.001)
                            tracked = self.basic_tracker.get_tracked_objects()
                            
                            annotated = color_image.copy()
                            for obj in tracked:
                                x1, y1, x2, y2 = obj['bbox']
                                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                label = f"ID:{obj['id']} {obj['depth']:.2f}m"
                                cv2.putText(annotated, label, (x1, y1-10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            message['camera_image'] = base64.b64encode(buffer).decode('utf-8')
                            message['tracked_objects'] = tracked
                        
                        if depth_image is not None:
                            height_obstacles = self.detector.analyze_height(depth_image, 0.001)
                            message['height_obstacles'] = height_obstacles
                    
                    message['tracking_mode'] = 'basic'
                
                # NAVEGAÇÃO AUTÔNOMA
                if self.autonomous_mode and self.robot.is_connected():
                    ground_obstacles = None
                    height_obstacles = message.get('height_obstacles')
                    
                    if ground_obstacles or height_obstacles:
                        direction, speed, nav_info = self.navigator.decide_movement(
                            ground_obstacles, height_obstacles
                        )
                        
                        if direction and speed > 0:
                            self.robot.move(direction, speed)
                            self.robot_moving = True
                            message['navigation'] = {
                                'direction': direction,
                                'speed': speed,
                                'info': nav_info
                            }
                        elif direction == 'stop':
                            self.robot.move('stop', 0)
                            self.robot_moving = False
                
                await self.send_to_all(message)
                
                elapsed = asyncio.get_event_loop().time() - loop_start
                sleep_time = max(0.05, 0.1 - elapsed)
                await asyncio.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("\n⚠️  Interrupção detectada, parando loop...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Erro no loop de sensores: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(0.5)
    
    async def start_server(self, host='127.0.0.1', port=8765):
        """Inicia servidor WebSocket"""
        print(f"\n🚀 Iniciando servidor WebSocket em {host}:{port}")
        sensor_task = asyncio.create_task(self.sensor_loop())
        async with websockets.serve(self.handle_client, host, port):
            print(f"✓ Servidor WebSocket ativo!")
            await asyncio.Future()


def main():
    """Função principal"""
    print("\n" + "="*70)
    print("  SISTEMA DE NAVEGAÇÃO AUTÔNOMA - ROBÔ TRI-OMNI")
    print("  Intel RealSense L515 + D435")
    if YOLO_AVAILABLE:
        print("  YOLO Tracking Disponível")
    print("="*70)
    
    # NÃO usamos mais RealSenseController para iniciar câmeras,
    # porque o código da Intel está dando o erro "bad optional access".
    # Em vez disso, deixamos o próprio módulo YOLO (MultiCameraTracker)
    # cuidar de encontrar e iniciar L515 e D435, exatamente como no
    # script que você mandou.
    realsense = RealSenseController()  # mantido apenas para futura integração de LiDAR
    detector = ObstacleDetector()
    navigator = AutonomousNavigator()
    robot = RobotController()
    server = WebSocketServer(robot, realsense, detector, navigator)
    
    try:
        print("\n📡 Sensores RealSense serão iniciados pelo módulo YOLO quando você ativar o tracking na interface.")
        
        print(f"\n{'='*70}")
        print("✓ Sistema pronto para uso!")
        print(f"  - Acesse a interface web no preview do Lovable")
        print(f"  - Use os controles para mover o robô manualmente")
        print(f"  - Ative o modo autônomo para navegação com desvio")
        if YOLO_AVAILABLE:
            print(f"  - YOLO Tracking (L515 + D435) será iniciado ao ativar o switch de YOLO")
        print(f"{'='*70}\n")
        
        asyncio.run(server.start_server())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário")
    finally:
        print("\n🧹 Limpando recursos...")
        realsense.cleanup()
        if server.yolo_tracker:
            server.yolo_tracker.cleanup()
        if robot.is_connected():
            robot.move('stop', 0)
        print("✓ Sistema encerrado\n")


if __name__ == "__main__":
    main()
