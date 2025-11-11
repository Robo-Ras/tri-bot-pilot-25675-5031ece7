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
            device_list.append({
                'name': name, 
                'serial': serial, 
                'product_line': product_line
            })
        
        return device_list
    
    def identify_devices(self):
        """Identifica e atribui dispositivos baseado no modelo"""
        devices = self.list_devices()
        
        for dev in devices:
            name = dev['name'].upper()
            product_line = dev.get('product_line', '').upper()
            
            # Busca por L515 usando nome e linha de produto
            if 'L515' in name or 'L5' in name or 'L500' in product_line:
                self.lidar_serial = dev['serial']
                print(f"\n✓ LiDAR L515 identificado!")
                print(f"  Nome: {dev['name']}")
                print(f"  Serial: {dev['serial']}")
            # Busca por D435 ou qualquer câmera RGB-D
            elif 'D435' in name or 'D4' in name or 'D400' in product_line:
                self.camera_serial = dev['serial']
                print(f"\n✓ Câmera D435 identificada!")
                print(f"  Nome: {dev['name']}")
                print(f"  Serial: {dev['serial']}")
        
        # Se não encontrou especificamente, usa os dispositivos disponíveis
        if not self.lidar_serial and len(devices) > 0:
            self.lidar_serial = devices[0]['serial']
            print(f"\n⚠ Usando {devices[0]['name']} como LiDAR (fallback)")
        
        if not self.camera_serial and len(devices) > 1:
            self.camera_serial = devices[1]['serial']
            print(f"\n⚠ Usando {devices[1]['name']} como Câmera (fallback)")
        elif not self.camera_serial and len(devices) == 1:
            # Se só tem um dispositivo, usa para ambos
            self.camera_serial = devices[0]['serial']
            print(f"\n⚠ Usando {devices[0]['name']} como Câmera também (fallback)")
        
        if not (self.lidar_serial or self.camera_serial):
            print("\n✗ Nenhum dispositivo RealSense pôde ser identificado!")
            print("  Tente desconectar e reconectar os sensores")
            print("  Verifique se os drivers estão instalados corretamente")
        
        return self.lidar_serial is not None or self.camera_serial is not None
    
    def start(self):
        """Inicia os sensores"""
        if not self.identify_devices():
            print("✗ Nenhum dispositivo RealSense disponível!")
            return False
        
        # Inicia LiDAR (embaixo do robô)
        if self.lidar_serial:
            try:
                self.pipeline_lidar = rs.pipeline()
                config_lidar = rs.config()
                config_lidar.enable_device(self.lidar_serial)
                config_lidar.enable_stream(rs.stream.depth, 1024, 768, rs.format.z16, 30)
                self.pipeline_lidar.start(config_lidar)
                self.lidar_started = True
                print("✓ LiDAR iniciado (posição: embaixo do robô)")
            except Exception as e:
                print(f"✗ Erro ao iniciar LiDAR: {e}")
                self.pipeline_lidar = None
        
        # Inicia Câmera (em cima do robô)
        if self.camera_serial:
            try:
                self.pipeline_camera = rs.pipeline()
                config_camera = rs.config()
                config_camera.enable_device(self.camera_serial)
                config_camera.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
                config_camera.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
                self.pipeline_camera.start(config_camera)
                self.camera_started = True
                print("✓ Câmera iniciada (posição: em cima do robô)")
            except Exception as e:
                print(f"✗ Erro ao iniciar câmera: {e}")
                self.pipeline_camera = None
        
        return self.lidar_started or self.camera_started
    
    def get_lidar_data(self):
        """Obtém dados do LiDAR (obstáculos no chão)"""
        if not self.lidar_started or not self.pipeline_lidar:
            return None
        
        try:
            frames = self.pipeline_lidar.wait_for_frames(timeout_ms=5000)
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                return None
            
            depth_image = np.asanyarray(depth_frame.get_data())
            return depth_image
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
        if self.lidar_started and self.pipeline_lidar:
            self.pipeline_lidar.stop()
            print("✓ LiDAR parado")
        if self.camera_started and self.pipeline_camera:
            self.pipeline_camera.stop()
            print("✓ Câmera parada")


class ObjectTracker:
    """Rastreia objetos detectados pela câmera"""
    
    def __init__(self, max_disappeared=30, min_area=500):
        self.next_object_id = 0
        self.objects = {}  # {id: centroid}
        self.disappeared = {}  # {id: frames_disappeared}
        self.max_disappeared = max_disappeared
        self.min_area = min_area
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=False
        )
        
    def detect_objects(self, frame, depth_frame=None):
        """Detecta objetos no frame usando subtração de fundo"""
        if frame is None:
            return []
        
        # Aplica subtração de fundo
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Remove ruído
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Encontra contornos
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            
            # Calcula bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calcula centroide
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
            
            # Obtém profundidade se disponível
            depth = None
            if depth_frame is not None:
                try:
                    depth_value = depth_frame[cy, cx]
                    if depth_value > 0:
                        depth = float(depth_value * 0.001)  # converte para metros
                except:
                    pass
            
            detected_objects.append({
                'bbox': (x, y, w, h),
                'centroid': (cx, cy),
                'area': int(area),
                'depth': depth
            })
        
        return detected_objects
    
    def update(self, detected_objects):
        """Atualiza tracking dos objetos"""
        # Se não há objetos detectados, incrementa contador de desaparecidos
        if len(detected_objects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    del self.objects[object_id]
                    del self.disappeared[object_id]
            return self.get_tracked_objects()
        
        # Se não há objetos sendo rastreados, registra todos
        if len(self.objects) == 0:
            for obj in detected_objects:
                self.register(obj)
        else:
            # Associa objetos detectados com objetos rastreados
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            
            detected_centroids = [obj['centroid'] for obj in detected_objects]
            
            # Calcula distância entre centroides
            D = distance.cdist(np.array(object_centroids), np.array(detected_centroids))
            
            # Encontra correspondências
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                
                if D[row, col] > 50:  # threshold de distância máxima
                    continue
                
                object_id = object_ids[row]
                self.objects[object_id] = detected_objects[col]
                self.disappeared[object_id] = 0
                
                used_rows.add(row)
                used_cols.add(col)
            
            # Marca objetos não associados como desaparecidos
            unused_rows = set(range(D.shape[0])) - used_rows
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    del self.objects[object_id]
                    del self.disappeared[object_id]
            
            # Registra novos objetos
            unused_cols = set(range(D.shape[1])) - used_cols
            for col in unused_cols:
                self.register(detected_objects[col])
        
        return self.get_tracked_objects()
    
    def register(self, obj):
        """Registra novo objeto"""
        self.objects[self.next_object_id] = obj
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1
    
    def get_tracked_objects(self):
        """Retorna lista de objetos rastreados"""
        tracked = []
        for object_id, obj_data in self.objects.items():
            x, y, w, h = obj_data['bbox']
            cx, cy = obj_data['centroid']
            tracked.append({
                'id': int(object_id),
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
        """Analisa dados da câmera (em cima) para verificar altura dos objetos"""
        if depth_image is None:
            return None
        
        # Converte para metros
        depth_meters = depth_image * 0.001
        
        # Analisa a região superior da imagem (objetos altos)
        height, width = depth_meters.shape
        upper_region = depth_meters[:height//2, :]
        
        # Divide em setores
        left_sector = upper_region[:, :width//3]
        center_sector = upper_region[:, width//3:2*width//3]
        right_sector = upper_region[:, 2*width//3:]
        
        # Detecta objetos altos próximos
        left_valid = left_sector[(left_sector > 0) & (left_sector < self.height_threshold)]
        center_valid = center_sector[(center_sector > 0) & (center_sector < self.height_threshold)]
        right_valid = right_sector[(right_sector > 0) & (right_sector < self.height_threshold)]
        
        left_min = np.min(left_valid) if len(left_valid) > 0 else 10.0
        center_min = np.min(center_valid) if len(center_valid) > 0 else 10.0
        right_min = np.min(right_valid) if len(right_valid) > 0 else 10.0
        
        height_obstacles = {
            'type': 'height',
            'left': bool(left_min < self.safe_distance),
            'center': bool(center_min < self.safe_distance),
            'right': bool(right_min < self.safe_distance),
            'distances': {
                'left': float(left_min),
                'center': float(center_min),
                'right': float(right_min)
            }
        }
        
        return height_obstacles


class AutonomousNavigator:
    """Sistema de navegação autônoma"""
    
    def __init__(self, obstacle_detector):
        self.detector = obstacle_detector
        self.current_state = 'idle'
        
    def decide_movement(self, ground_obstacles, height_obstacles):
        """Decide o movimento baseado nos obstáculos (chão e altura)"""
        # Combina informações de ambos os sensores
        obstacles_combined = {
            'left': False,
            'center': False,
            'right': False
        }
        
        if ground_obstacles:
            obstacles_combined['left'] |= ground_obstacles['left']
            obstacles_combined['center'] |= ground_obstacles['center']
            obstacles_combined['right'] |= ground_obstacles['right']
        
        if height_obstacles:
            obstacles_combined['left'] |= height_obstacles['left']
            obstacles_combined['center'] |= height_obstacles['center']
            obstacles_combined['right'] |= height_obstacles['right']
        
        # Decisão de movimento
        if not obstacles_combined['center']:
            # Caminho livre à frente
            return 'forward', 150
        elif not obstacles_combined['right']:
            # Desviar para direita
            return 'right', 120
        elif not obstacles_combined['left']:
            # Desviar para esquerda
            return 'left', 120
        else:
            # Obstáculos em todos os lados - recuar
            return 'backward', 100


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
        if direction == 'forward':
            return self.send_command(speed, speed, speed)
        elif direction == 'backward':
            return self.send_command(-speed, -speed, -speed)
        elif direction == 'left':
            return self.send_command(-speed, speed, 0)
        elif direction == 'right':
            return self.send_command(speed, -speed, 0)
        elif direction == 'stop':
            return self.send_command(0, 0, 0)
        return False
    
    def get_available_ports(self):
        """Lista portas seriais disponíveis"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]


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
        
        if cmd_type == 'connect':
            port = data.get('port')
            success = self.robot.connect(port)
            await self.send_to_all({'type': 'connection', 'status': success})
            
        elif cmd_type == 'move':
            direction = data.get('direction')
            speed = data.get('speed', 150)
            self.robot.move(direction, speed)
            
        elif cmd_type == 'set_autonomous':
            self.autonomous_mode = data.get('enabled', False)
            await self.send_to_all({'type': 'autonomous_status', 'enabled': self.autonomous_mode})
            
        elif cmd_type == 'get_ports':
            ports = self.robot.get_available_ports()
            await self.send_to_all({'type': 'ports', 'ports': ports})
    
    async def sensor_loop(self):
        """Loop principal de processamento dos sensores"""
        frame_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 20
        
        while self.running:
            try:
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
                
                # Navegação autônoma
                if self.autonomous_mode and (ground_obstacles or height_obstacles):
                    direction, speed = self.navigator.decide_movement(ground_obstacles, height_obstacles)
                    self.robot.move(direction, speed)
                
                # Prepara dados para enviar
                message = {
                    'type': 'sensor_data',
                    'timestamp': asyncio.get_event_loop().time(),
                    'ground_obstacles': ground_obstacles,
                    'height_obstacles': height_obstacles
                }
                
                # Tracking de objetos e envio do frame da câmera
                if color_image is not None:
                    # Detecta e rastreia objetos
                    detected = self.tracker.detect_objects(color_image, camera_depth)
                    tracked_objects = self.tracker.update(detected)
                    
                    if tracked_objects:
                        message['tracked_objects'] = tracked_objects
                    
                    # Envia frame da câmera (comprimido)
                    _, buffer = cv2.imencode('.jpg', color_image, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    image_base64 = base64.b64encode(buffer).decode('utf-8')
                    message['camera'] = image_base64
                
                # Reconstrução 3D a cada 10 frames
                frame_count += 1
                if frame_count % 10 == 0:
                    # Usa dados do LiDAR para reconstrução 3D
                    if lidar_data is not None:
                        pcd = self.sensors.create_point_cloud(lidar_data, None)
                        if pcd is not None:
                            # Serializa nuvem de pontos simplificada
                            points = np.asarray(pcd.points)
                            colors = np.asarray(pcd.colors)
                            
                            # Amostragem para reduzir tamanho
                            if len(points) > 1000:
                                indices = np.random.choice(len(points), 1000, replace=False)
                                points = points[indices]
                                colors = colors[indices]
                            
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
    sensors.start()
    
    detector = ObstacleDetector(safe_distance=0.8)
    navigator = AutonomousNavigator(detector)
    robot = RobotController()
    
    # Inicia servidor WebSocket
    server = WebSocketServer(robot, sensors, detector, navigator)
    
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
