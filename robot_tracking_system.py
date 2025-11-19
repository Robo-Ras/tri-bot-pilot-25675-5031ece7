"""
Sistema de Rastreamento de Objetos com YOLO
Integração com L515 e D435 para tracking avançado
"""

import time
import math
import uuid
import numpy as np
import cv2
import pyrealsense2 as rs
from ultralytics import YOLO
from filterpy.kalman import KalmanFilter

# Configurações do sistema
MODEL_PATH = "yolov8n.pt"
DETECTION_INTERVAL = 6
MIN_DIST = 0.25
MAX_DIST = 5.0
IOU_MATCH_THRESHOLD = 0.4
MAX_MISSED = 10
TRACKER_DIST_THRESHOLD_PIX = 120

class Camera:
    """Gerencia uma câmera RealSense individual"""
    
    def __init__(self, serial_number, name, depth_width, depth_height, color_width, color_height):
        self.serial_number = serial_number
        self.name = name
        self.depth_width = depth_width
        self.depth_height = depth_height
        self.color_width = color_width
        self.color_height = color_height
        self.pipeline = None
        self.align = None
        self.depth_scale = None
        self.profile = None
        
    def start(self):
        """Inicializa a câmera"""
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_device(self.serial_number)
        config.enable_stream(rs.stream.depth, self.depth_width, self.depth_height, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, self.color_width, self.color_height, rs.format.bgr8, 30)
        
        print(f"  Iniciando {self.name} (S/N: {self.serial_number})...")
        self.profile = self.pipeline.start(config)
        self.align = rs.align(rs.stream.color)
        self.depth_scale = self.profile.get_device().first_depth_sensor().get_depth_scale()
        print(f"  ✓ {self.name} - escala de profundidade: {self.depth_scale}")
        
    def get_frames(self):
        """Obtém frames alinhados da câmera"""
        if not self.pipeline:
            return None, None, None
            
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            aligned_frames = self.align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if depth_frame and color_frame:
                color = np.asanyarray(color_frame.get_data())
                depth = np.asanyarray(depth_frame.get_data())
                return color, depth, depth_frame
        except Exception as e:
            print(f"    Erro ao obter frames de {self.name}: {e}")
            
        return None, None, None
    
    def stop(self):
        """Para o pipeline da câmera"""
        if self.pipeline:
            self.pipeline.stop()
            self.pipeline = None

class TrackedObject:
    """Objeto rastreado com filtro de Kalman"""
    
    def __init__(self, bbox, cls, conf, class_name, camera_name=""):
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        
        # Filtro de Kalman para suavização
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.kf.x = np.array([cx, cy, 0., 0.])
        self.kf.F = np.array([[1,0,1,0],[0,1,0,1],[0,0,1,0],[0,0,0,1]])
        self.kf.H = np.array([[1,0,0,0],[0,1,0,0]])
        self.kf.P *= 50
        self.kf.R *= 1
        self.kf.Q *= 0.01
        
        self.bbox = bbox
        self.cls = cls
        self.conf = conf
        self.class_name = class_name
        self.id = str(uuid.uuid4())[:8]
        self.missed = 0
        self.history = []
        self.camera_name = camera_name
        self.depth = 0.0
        self.position_3d = (0, 0, 0)
        
    def predict(self):
        """Predição do filtro de Kalman"""
        self.kf.predict()
        
    def update(self, bbox, camera_name=""):
        """Atualiza o objeto com nova detecção"""
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        self.kf.update(np.array([cx, cy]))
        self.bbox = bbox
        self.missed = 0
        self.history.append((time.time(), bbox))
        if camera_name:
            self.camera_name = camera_name
            
    def current_center(self):
        """Retorna o centro atual do objeto"""
        return int(self.kf.x[0]), int(self.kf.x[1])
    
    def current_bbox(self):
        """Retorna a bounding box atual"""
        return self.bbox
    
    def to_dict(self):
        """Converte para dicionário para envio via WebSocket"""
        cx, cy = self.current_center()
        x1, y1, x2, y2 = self.bbox
        
        return {
            'id': self.id,
            'bbox': {
                'x': int(x1),
                'y': int(y1),
                'w': int(x2 - x1),
                'h': int(y2 - y1)
            },
            'centroid': {
                'x': int(cx),
                'y': int(cy)
            },
            'class': self.class_name,
            'confidence': float(self.conf),
            'camera': self.camera_name,
            'depth': float(self.depth),
            'position_3d': [float(x) for x in self.position_3d],
            'missed': self.missed
        }

class MultiCameraTracker:
    """Sistema de tracking com múltiplas câmeras"""
    
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)
        self.trackers = []
        self.frame_idx = 0
        self.cameras = []
        
    def find_and_start_cameras(self):
        """Encontra e inicializa todas as câmeras RealSense"""
        ctx = rs.context()
        
        for device in ctx.devices:
            serial = device.get_info(rs.camera_info.serial_number)
            name = device.get_info(rs.camera_info.name)
            print(f"  Câmera encontrada: {name} (S/N: {serial})")
            
            # Configurações específicas para cada tipo
            if 'L515' in name:
                camera = Camera(serial, "L515", 320, 240, 640, 480)
            elif 'D435' in name:
                camera = Camera(serial, "D435", 640, 480, 640, 480)
            else:
                camera = Camera(serial, name, 640, 480, 640, 480)
                
            try:
                camera.start()
                self.cameras.append(camera)
                time.sleep(0.5)
            except Exception as e:
                print(f"    ✗ Falha ao iniciar {name}: {e}")
        
        return len(self.cameras) > 0
    
    def process_frame(self):
        """Processa frames de todas as câmeras COM TRATAMENTO ROBUSTO DE ERROS"""
        all_detections = []
        camera_frames = {}
        
        try:
            # Coleta frames de todas as câmeras
            for camera in self.cameras:
                try:
                    color, depth, depth_frame = camera.get_frames()
                    if color is None or depth is None:
                        continue
                        
                    camera_frames[camera.name] = {
                        'color': color,
                        'depth': depth,
                        'depth_frame': depth_frame,
                        'depth_scale': camera.depth_scale,
                        'annotated': color.copy()
                    }
                    
                    # Detecção YOLO apenas em intervalos
                    if self.frame_idx % DETECTION_INTERVAL == 0:
                        try:
                            results = self.model(color, verbose=False)
                            for r in results:
                                for box in r.boxes:
                                    try:
                                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                        cls = int(box.cls[0])
                                        conf = float(box.conf[0])
                                        class_name = self.model.names[cls]
                                        
                                        all_detections.append({
                                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                                            'cls': cls,
                                            'class_name': class_name,
                                            'conf': conf,
                                            'camera': camera.name,
                                            'depth': depth,
                                            'depth_frame': depth_frame,
                                            'depth_scale': camera.depth_scale,
                                            'color_width': camera.color_width,
                                            'color_height': camera.color_height
                                        })
                                    except Exception as e:
                                        print(f"      Erro ao processar box: {e}")
                                        continue
                        except Exception as e:
                            print(f"    Erro na detecção YOLO para {camera.name}: {e}")
                            continue
                except Exception as e:
                    print(f"  Erro ao obter frames de {camera.name}: {e}")
                    continue
            
            # Atualiza trackers
            if self.frame_idx % DETECTION_INTERVAL == 0 and all_detections:
                try:
                    self._update_trackers(all_detections)
                except Exception as e:
                    print(f"  Erro ao atualizar trackers: {e}")
            else:
                for tr in self.trackers:
                    tr.predict()
                    tr.missed += 1
            
            # Remove trackers perdidos
            self.trackers = [t for t in self.trackers if t.missed <= MAX_MISSED]
            
            # Desenha anotações
            for camera_name, data in camera_frames.items():
                try:
                    self._draw_annotations(camera_name, data)
                except Exception as e:
                    print(f"  Erro ao desenhar anotações em {camera_name}: {e}")
            
            self.frame_idx += 1
            
        except Exception as e:
            print(f"ERRO CRÍTICO no process_frame: {e}")
            import traceback
            traceback.print_exc()
        
        return camera_frames
    
    def _update_trackers(self, detections):
        """Atualiza trackers com novas detecções"""
        assigned = set()
        
        for detection in detections:
            dbox = detection['bbox']
            dcls = detection['cls']
            dconf = detection['conf']
            dclass_name = detection['class_name']
            camera_name = detection['camera']
            depth = detection['depth']
            depth_scale = detection['depth_scale']
            depth_frame = detection['depth_frame']
            color_w = detection.get('color_width', depth.shape[1])
            color_h = detection.get('color_height', depth.shape[0])
            
            # Centro do bbox nas coordenadas da imagem colorida
            cx_color = (dbox[0] + dbox[2]) // 2
            cy_color = (dbox[1] + dbox[3]) // 2
            
            # Escala coordenadas para resolução do mapa de profundidade
            depth_h, depth_w = depth.shape[0], depth.shape[1]
            cx = int(cx_color * depth_w / color_w)
            cy = int(cy_color * depth_h / color_h)
            
            # Verifica limites
            if cx < 0 or cx >= depth_w or cy < 0 or cy >= depth_h:
                continue
                
            dist = depth[cy, cx] * depth_scale
            if math.isnan(dist) or dist <= 0:
                continue
            if dist < MIN_DIST or dist > MAX_DIST:
                continue
            
            # Calcula posição 3D
            try:
                depth_intrin = depth_frame.get_profile().as_video_stream_profile().get_intrinsics()
                pos_3d = rs.rs2_deproject_pixel_to_point(depth_intrin, [cx, cy], dist)
            except:
                pos_3d = (0, 0, 0)
            
            # Encontra tracker mais próximo (em coordenadas da imagem colorida)
            best = None
            best_dist = TRACKER_DIST_THRESHOLD_PIX + 1
            
            for tr in self.trackers:
                if tr.camera_name != camera_name:
                    continue
                tx, ty = tr.current_center()
                d = math.hypot(tx - cx_color, ty - cy_color)
                if d < best_dist:
                    best_dist = d
                    best = tr
            
            if best and best_dist < TRACKER_DIST_THRESHOLD_PIX:
                best.update(dbox, camera_name)
                best.depth = dist
                best.position_3d = pos_3d
                assigned.add(id(best))
            else:
                newt = TrackedObject(dbox, dcls, dconf, dclass_name, camera_name)
                newt.depth = dist
                newt.position_3d = pos_3d
                self.trackers.append(newt)
        
        # Marca não atribuídos
        for tr in self.trackers:
            if id(tr) not in assigned:
                tr.missed += 1
    
    def _draw_annotations(self, camera_name, data):
        """Desenha anotações nos frames"""
        annotated = data['annotated']
        depth = data['depth']
        
        for tr in self.trackers:
            if tr.camera_name != camera_name or tr.missed > 3:
                continue
                
            x1, y1, x2, y2 = map(int, tr.current_bbox())
            cx, cy = tr.current_center()
            
            # Cor baseada na câmera
            color = (0, 255, 0) if tr.camera_name == camera_name else (255, 255, 0)
            
            # Label
            label = f"{tr.class_name} #{tr.id} {tr.conf:.2f} {tr.depth:.2f}m"
            
            # Desenha
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, label, (x1, max(10, y1-6)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Posição 3D
            x3d, y3d, z3d = tr.position_3d
            if not any(math.isnan(v) for v in (x3d, y3d, z3d)):
                text3d = f"X:{x3d:.2f} Y:{y3d:.2f} Z:{z3d:.2f}m"
                cv2.putText(annotated, text3d, (x1, y2+15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 200), 1)
            
            cv2.circle(annotated, (cx, cy), 4, (0, 0, 255), -1)
    
    def get_tracked_objects(self):
        """Retorna lista de objetos rastreados"""
        return [tr.to_dict() for tr in self.trackers if tr.missed < 5]
    
    def cleanup(self):
        """Limpa recursos COM TRATAMENTO DE ERRO"""
        print("  Parando câmeras...")
        for camera in self.cameras:
            try:
                if camera.pipeline:
                    print(f"    Parando {camera.name}...")
                    camera.stop()
                    print(f"    ✓ {camera.name} parado")
            except Exception as e:
                print(f"    ⚠ Erro ao parar {camera.name}: {e}")
                # Continua mesmo com erro
        self.cameras = []
        print("  ✓ Limpeza concluída")

def iou(a, b):
    """Calcula Intersection over Union"""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    xi1 = max(ax1, bx1)
    yi1 = max(ay1, by1)
    xi2 = min(ax2, bx2)
    yi2 = min(ay2, by2)
    iw = max(0, xi2 - xi1)
    ih = max(0, yi2 - yi1)
    inter = iw * ih
    areaA = (ax2 - ax1) * (ay2 - ay1)
    areaB = (bx2 - bx1) * (by2 - by1)
    union = areaA + areaB - inter
    return inter / union if union > 0 else 0
