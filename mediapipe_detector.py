"""
MediaPipe Object Detection Integration for L515
Integra detecção de objetos MediaPipe com o sistema de navegação autônoma
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import mediapipe as mp
from typing import List, Dict, Optional

class MediaPipeDetector:
    """Detector de objetos usando MediaPipe EfficientDet"""
    
    def __init__(self, model_path: str = "efficientdet_lite0.tflite"):
        """
        Inicializa o detector MediaPipe
        
        Args:
            model_path: Caminho para o modelo .tflite
        """
        self.mp_object_detector = mp.tasks.vision.ObjectDetector
        self.mp_base_options = mp.tasks.BaseOptions
        self.mp_object_detector_options = mp.tasks.vision.ObjectDetectorOptions
        self.mp_vision_running_mode = mp.tasks.vision.RunningMode
        
        # Configuração do detector
        options = self.mp_object_detector_options(
            base_options=self.mp_base_options(model_asset_path=model_path),
            max_results=5,
            running_mode=self.mp_vision_running_mode.IMAGE
        )
        
        self.detector = self.mp_object_detector.create_from_options(options)
        print("✓ MediaPipe detector inicializado")
    
    def detect_objects(self, color_img: np.ndarray, depth_img: np.ndarray, 
                      depth_scale: float) -> List[Dict]:
        """
        Detecta objetos na imagem e calcula suas distâncias
        
        Args:
            color_img: Imagem colorida (BGR)
            depth_img: Imagem de profundidade
            depth_scale: Escala de profundidade do sensor
            
        Returns:
            Lista de objetos detectados com informações
        """
        try:
            # Converter BGR para RGB para MediaPipe
            rgb_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)
            
            # Detecção
            result = self.detector.detect(mp_image)
            
            detected_objects = []
            for det in result.detections:
                bbox = det.bounding_box
                x = bbox.origin_x
                y = bbox.origin_y
                w = bbox.width
                h = bbox.height
                
                # Centro do objeto
                cx = int(x + w/2)
                cy = int(y + h/2)
                
                # Garantir que está dentro dos limites
                if 0 <= cy < depth_img.shape[0] and 0 <= cx < depth_img.shape[1]:
                    # Calcular distância
                    dist = depth_img[cy, cx] * depth_scale
                    
                    # Pegar melhor categoria
                    category = det.categories[0]
                    label = category.category_name
                    confidence = category.score
                    
                    obj_info = {
                        'label': label,
                        'confidence': float(confidence),
                        'distance': float(dist),
                        'bbox': {
                            'x': int(x),
                            'y': int(y),
                            'width': int(w),
                            'height': int(h)
                        }
                    }
                    
                    detected_objects.append(obj_info)
            
            return detected_objects
            
        except Exception as e:
            print(f"⚠️ Erro na detecção MediaPipe: {e}")
            return []
    
    def draw_detections(self, img: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Desenha as detecções na imagem
        
        Args:
            img: Imagem para desenhar
            detections: Lista de objetos detectados
            
        Returns:
            Imagem com detecções desenhadas
        """
        output = img.copy()
        
        for det in detections:
            bbox = det['bbox']
            x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
            label = det['label']
            dist = det['distance']
            confidence = det['confidence']
            
            # Bounding box
            cv2.rectangle(output, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Label com distância
            text = f"{label} {dist:.2f}m ({confidence*100:.0f}%)"
            cv2.putText(output, text,
                       (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 0), 2)
        
        return output
    
    def cleanup(self):
        """Limpa recursos do detector"""
        # MediaPipe gerencia recursos automaticamente
        pass


if __name__ == "__main__":
    """Teste standalone do detector"""
    
    # Inicializar detector
    detector = MediaPipeDetector()
    
    # Configurar L515
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 320, 240, rs.format.z16, 30)
    
    profile = pipeline.start(config)
    depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
    align = rs.align(rs.stream.color)
    
    print("✓ Detector funcionando. Pressione Q para sair.")
    
    try:
        while True:
            frames = pipeline.wait_for_frames()
            frames = align.process(frames)
            
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                continue
            
            color_img = np.asanyarray(color_frame.get_data())
            depth_img = np.asanyarray(depth_frame.get_data())
            
            # Detectar objetos
            detections = detector.detect_objects(color_img, depth_img, depth_scale)
            
            # Desenhar detecções
            output_img = detector.draw_detections(color_img, detections)
            
            # Mostrar
            cv2.imshow("L515 Object Detection + Distance", output_img)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        detector.cleanup()
        print("✓ Detector encerrado")
