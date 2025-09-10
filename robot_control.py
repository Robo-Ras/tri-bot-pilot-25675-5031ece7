import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import time

class RobotController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Controle do Robô")
        self.root.geometry("400x500")
        
        self.serial_connection = None
        self.speed = 200  # Velocidade padrão
        
        self.setup_ui()
        self.setup_serial()
    
    def setup_ui(self):
        # Frame para conexão serial
        serial_frame = ttk.Frame(self.root)
        serial_frame.pack(pady=10)
        
        ttk.Label(serial_frame, text="Porta Serial:").pack()
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(serial_frame, textvariable=self.port_var)
        self.port_combo.pack()
        
        ttk.Button(serial_frame, text="Conectar", command=self.connect_serial).pack(pady=5)
        ttk.Button(serial_frame, text="Atualizar Portas", command=self.refresh_ports).pack()
        
        # Status da conexão
        self.status_label = ttk.Label(serial_frame, text="Desconectado", foreground="red")
        self.status_label.pack()
        
        # Frame para controle de velocidade
        speed_frame = ttk.Frame(self.root)
        speed_frame.pack(pady=10)
        
        ttk.Label(speed_frame, text="Velocidade:").pack()
        self.speed_scale = tk.Scale(speed_frame, from_=0, to=255, orient=tk.HORIZONTAL, command=self.update_speed)
        self.speed_scale.set(200)
        self.speed_scale.pack()
        
        # Frame para botões de controle
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=20)
        
        # Botão para frente
        ttk.Button(control_frame, text="FRENTE", command=self.move_forward, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        # Botões esquerda e direita
        ttk.Button(control_frame, text="ESQUERDA", command=self.move_left, width=10).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="PARAR", command=self.stop, width=10).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(control_frame, text="DIREITA", command=self.move_right, width=10).grid(row=1, column=2, padx=5, pady=5)
        
        # Botão para trás
        ttk.Button(control_frame, text="TRÁS", command=self.move_backward, width=10).grid(row=2, column=1, padx=5, pady=5)
        
        # Bind das teclas
        self.root.bind('<KeyPress>', self.key_press)
        self.root.bind('<KeyRelease>', self.key_release)
        self.root.focus_set()
    
    def setup_serial(self):
        self.refresh_ports()
    
    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)
    
    def connect_serial(self):
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            port = self.port_var.get()
            if port:
                self.serial_connection = serial.Serial(port, 9600, timeout=1)
                time.sleep(2)  # Aguarda o Arduino resetar
                self.status_label.config(text="Conectado", foreground="green")
            else:
                self.status_label.config(text="Selecione uma porta", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"Erro: {str(e)}", foreground="red")
    
    def update_speed(self, value):
        self.speed = int(value)
    
    def send_command(self, m1, m2, m3):
        if self.serial_connection and self.serial_connection.is_open:
            try:
                command = f"{m1},{m2},{m3}\n"
                self.serial_connection.write(command.encode())
                print(f"Enviado: M1={m1}, M2={m2}, M3={m3}")
            except Exception as e:
                print(f"Erro ao enviar comando: {e}")
    
    def move_forward(self):
        # Para frente: m1 parado, m2 para frente, m3 para trás
        self.send_command(0, self.speed, -self.speed)
    
    def move_backward(self):
        # Para trás: m1 parado, m2 para trás, m3 para frente
        self.send_command(0, -self.speed, self.speed)
    
    def move_right(self):
        # Para direita: m2 parado, m1 para trás, m3 para frente
        self.send_command(-self.speed, 0, self.speed)
    
    def move_left(self):
        # Para esquerda: m3 parado, m1 para frente, m2 para trás
        self.send_command(self.speed, -self.speed, 0)
    
    def stop(self):
        # Parar todos os motores
        self.send_command(0, 0, 0)
    
    def key_press(self, event):
        key = event.keysym.lower()
        if key == 'w' or key == 'up':
            self.move_forward()
        elif key == 's' or key == 'down':
            self.move_backward()
        elif key == 'a' or key == 'left':
            self.move_left()
        elif key == 'd' or key == 'right':
            self.move_right()
        elif key == 'space':
            self.stop()
    
    def key_release(self, event):
        # Opcional: parar quando soltar a tecla
        pass
    
    def run(self):
        try:
            self.root.mainloop()
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()

if __name__ == "__main__":
    controller = RobotController()
    controller.run()
