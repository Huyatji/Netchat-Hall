# -*- coding: utf-8 -*-
import socket
import threading
import json
import os
import sys
import time,shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

def havewt():
    return shutil.which("wt") is not None

class ChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sala de chat en línea")
        self.root.iconbitmap("cil.ico")
        self.root.geometry("1000x650")
        self.lang_dict={
            "zh": {
                "used_user_name": "用户名已被使用，请更换用户名重试{}",
                "usr_not_exist": "用户 {} 不存在或已离线",
                "kicked": "你已被踢出服务器{}",
                "welcome_join": "欢迎 {} 加入服务器"
            },
            "en": {
                "used_user_name": "Username already in use, please choose another {}",
                "usr_not_exist": "User {} does not exist or is offline",
                "kicked": "You have been kicked from the server {}",
                "welcome_join": "Welcome {} to the server"
            },
            "fr": {
                "used_user_name": "Nom d'utilisateur déjà utilisé, veuillez en choisir un autre {}",
                "usr_not_exist": "L'utilisateur {} n'existe pas ou est hors ligne",
                "kicked": "Vous avez été expulsé du serveur {}",
                "welcome_join": "Bienvenue {} sur le serveur"
            },
            "ru": {
                "used_user_name": "Имя пользователя уже используется, выберите другое {}",
                "usr_not_exist": "Пользователь {} не существует или не в сети",
                "kicked": "Вы были исключены с сервера {}",
                "welcome_join": "Добро пожаловать {} на сервер"
            },
            "es": {
                "used_user_name": "Nombre de usuario ya en uso, por favor elija otro {}",
                "usr_not_exist": "El usuario {} no existe o está desconectado",
                "kicked": "Has sido expulsado del servidor {}",
                "welcome_join": "Bienvenido {} al servidor"
            },
            "ar": {
                "used_user_name": "اسم المستخدم قيد الاستخدام بالفعل، يرجى اختيار اسم آخر {}",
                "usr_not_exist": "المستخدم {} غير موجود أو غير متصل",
                "kicked": "لقد تم طردك من الخادم {}",
                "welcome_join": "مرحباً {} في الخادم"
            }
        }
        self.client = None
        self.username = ""
        self.buffer_size = 4096
        self.receive_thread = None
        if os.name == 'nt' and sys.getwindowsversion().major >= 6:
            if havewt(): self.fnt='Cascadia Code'
            else: self.fnt='Consolas'
        else:
            self.fnt='TkDefaultFont'
        
        self.setup_login_ui()
    
    def setup_login_ui(self):
        """Configurar la interfaz de inicio de sesión"""
        self.login_frame = ttk.Frame(self.root, padding="20")
        self.login_frame.pack(expand=True)
        
        ttk.Label(self.login_frame, text="Bienvenido a la sala de chat", font=(self.fnt, 18, 'bold')).pack(pady=20)
        
        ttk.Label(self.login_frame, text="Nombre de usuario:", font=(self.fnt, 11)).pack(pady=5)
        self.username_entry = ttk.Entry(self.login_frame, width=30, font=(self.fnt, 11))
        self.username_entry.pack(pady=5)
        self.username_entry.focus()
        
        ttk.Label(self.login_frame, text="Dirección del servidor:", font=(self.fnt, 11)).pack(pady=5)
        self.host_entry = ttk.Entry(self.login_frame, width=30, font=(self.fnt, 11))
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(pady=5)
        
        ttk.Label(self.login_frame, text="Puerto:", font=(self.fnt, 11)).pack(pady=5)
        self.port_entry = ttk.Entry(self.login_frame, width=30, font=(self.fnt, 11))
        self.port_entry.insert(0, "55555")
        self.port_entry.pack(pady=5)
        
        ttk.Button(self.login_frame, text="Conectar", command=self.connect_to_server).pack(pady=20)
        
        # Vincular la tecla Enter al botón de conexión
        self.root.bind('<Return>', lambda e: self.connect_to_server())
    
    def setup_chat_ui(self):
        """Configurar la interfaz de chat"""
        # Destruir la interfaz de inicio de sesión
        self.login_frame.destroy()
        
        # ⭐ Desvincular la tecla Enter del inicio de sesión
        self.root.unbind('<Return>')
        
        # Crear contenedor principal
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Izquierda: lista de usuarios
        left_frame = ttk.Frame(main_container, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        ttk.Label(left_frame, text="Usuarios en línea", font=(self.fnt, 11, 'bold')).pack(pady=5)
        
        self.user_listbox = tk.Listbox(left_frame, font=(self.fnt, 10))
        self.user_listbox.pack(fill=tk.BOTH, expand=True)
        self.user_listbox.bind('<Double-Button-1>', self.start_private_chat)
        
        # Derecha: área de chat
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Área de visualización de mensajes
        self.chat_display = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                       font=(self.fnt, 10), state='disabled')
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Configurar estilos de mensajes
        self.chat_display.tag_config('system', foreground='gray')
        self.chat_display.tag_config('private', foreground='purple')
        self.chat_display.tag_config('file', foreground='blue')
        self.chat_display.tag_config('username', foreground='dark green', font=(self.fnt, 10, 'bold'))
        self.chat_display.tag_config('own_message', foreground='black')
        
        # Abajo: área de entrada
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Campo de entrada de mensajes
        self.message_entry = ttk.Entry(bottom_frame, font=(self.fnt, 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # ⭐ Vincular la tecla Enter del campo de mensaje al envío
        self.message_entry.bind('<Return>', self.send_message)
        
        # Botón de enviar
        ttk.Button(bottom_frame, text="Enviar", command=self.send_message).pack(side=tk.RIGHT, padx=2)
        
        # Botón de archivo
        ttk.Button(bottom_frame, text="📎 Archivo", command=self.send_file).pack(side=tk.RIGHT, padx=2)
        
        # Manejar cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Enfocar
        self.message_entry.focus()
    
    def connect_to_server(self):
        """Conectar al servidor"""
        username = self.username_entry.get().strip()
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not username:
            messagebox.showerror("Error", "Por favor, ingrese un nombre de usuario")
            return
        
        try:
            port = int(port)
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(10)
            self.client.connect((host, port))
            self.client.send(username.encode('utf-8'))
            
            self.username = username
            self.root.title(f"Sala de chat en línea - {username}")
            self.setup_chat_ui()
            
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            self.display_message(f"Conectado al servidor {host}:{port}", 'system')
            
        except socket.timeout:
            messagebox.showerror("Tiempo de espera agotado", "Tiempo de conexión agotado, verifique dirección y puerto")
        except ConnectionRefusedError:
            messagebox.showerror("Conexión rechazada", "El servidor rechazó la conexión, verifique si está iniciado")
        except Exception as e:
            messagebox.showerror("Fallo de conexión", f"No se pudo conectar: {str(e)}")
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
                self.client = None
    
    def receive_messages(self):
        """Recibir mensajes"""
        file_data_buffer = b''
        expecting_file = False
        expected_file_size = 0
        file_info = None
        
        while True:
            try:
                if not self.client:
                    break
                
                if expecting_file:
                    while len(file_data_buffer) < expected_file_size:
                        try:
                            chunk = self.client.recv(min(self.buffer_size, 
                                                         expected_file_size - len(file_data_buffer)))
                            if not chunk:
                                self.display_message("Transferencia de archivo interrumpida", 'system')
                                break
                            file_data_buffer += chunk
                        except socket.timeout:
                            continue
                        except Exception as e:
                            self.display_message(f"Error al recibir archivo: {str(e)}", 'system')
                            break
                    
                    if len(file_data_buffer) == expected_file_size:
                        self.save_received_file(file_info, file_data_buffer)
                    else:
                        self.display_message("Archivo recibido incompleto", 'system')
                    
                    file_data_buffer = b''
                    expecting_file = False
                    file_info = None
                    continue
                
                try:
                    data = self.client.recv(self.buffer_size)
                    if not data:
                        self.display_message("Desconectado del servidor", 'system')
                        break
                except socket.timeout:
                    continue
                except Exception as e:
                    self.display_message(f"Error al recibir datos: {str(e)}", 'system')
                    break
                
                message = data.decode('utf-8')
                
                try:
                    msg_data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                
                if msg_data['type'] == 'user_list':
                    self.update_user_list(msg_data['users'])
                
                elif msg_data['type'] == 'system':
                    self.display_message(self.lang_dict['es'][msg_data['lang_key']].format(msg_data['fmt']), 'system', msg_data.get('time'))

                
                elif msg_data['type'] == 'public':
                    self.display_message(f"{msg_data['username']}: {msg_data['message']}", 
                                       'public', msg_data['time'], msg_data['username'])
                
                elif msg_data['type'] == 'private':
                    self.display_message(f"[Privado] {msg_data['from']}: {msg_data['message']}", 
                                       'private', msg_data['time'])
                
                elif msg_data['type'] == 'file':
                    file_info = msg_data
                    try:
                        size_bytes = self.client.recv(8)
                        if len(size_bytes) == 8:
                            expected_file_size = int.from_bytes(size_bytes, byteorder='big')
                            expecting_file = True
                            self.display_message(f"Archivo recibido: {msg_data['filename']} ({expected_file_size} bytes)", 
                                               'file', msg_data['time'])
                        else:
                            self.display_message("Error en información de tamaño de archivo", 'system')
                    except Exception as e:
                        self.display_message(f"Error al preparar archivo: {str(e)}", 'system')
                    
            except Exception as e:
                if self.client:
                    self.display_message(f"Error de conexión: {str(e)}", 'system')
                break
    
    def display_message(self, message, msg_type='public', time=None, username=None):
        """Mostrar mensaje"""
        try:
            self.chat_display.configure(state='normal')
            
            if time:
                self.chat_display.insert(tk.END, f"[{time}] ", 'system')
            
            if msg_type == 'public' and username:
                if username == self.username:
                    self.chat_display.insert(tk.END, "Yo", 'own_message')
                else:
                    self.chat_display.insert(tk.END, username, 'username')
                self.chat_display.insert(tk.END, ": ")
                if ': ' in message:
                    msg_content = message.split(': ', 1)[1]
                else:
                    msg_content = message
                self.chat_display.insert(tk.END, msg_content + '\n')
            else:
                self.chat_display.insert(tk.END, message + '\n', msg_type)
            
            self.chat_display.see(tk.END)
            self.chat_display.configure(state='disabled')
        except Exception as e:
            print(f"Error al mostrar mensaje: {e}")
    
    def update_user_list(self, users):
        """Actualizar la lista de usuarios en línea"""
        try:
            self.user_listbox.delete(0, tk.END)
            for user in users:
                display_text = f"👤 {user}"
                if user == self.username:
                    display_text += " (Yo)"
                self.user_listbox.insert(tk.END, display_text)
        except Exception as e:
            print(f"Error al actualizar lista de usuarios: {e}")
    
    def send_message(self, event=None):
        """Enviar mensaje"""
        message = self.message_entry.get().strip()
        if not message or not self.client:
            return
        
        try:
            if message.startswith('/msg '):
                parts = message.split(' ', 2)
                if len(parts) >= 3:
                    target = parts[1]
                    msg = parts[2]
                    self.send_private_message(target, msg)
                else:
                    self.display_message("Uso: /msg nombre_usuario mensaje", 'system')
            else:
                data = json.dumps({
                    'type': 'public',
                    'message': message
                })
                self.client.send(data.encode('utf-8'))
                self.display_message(message, 'public', 
                                   datetime.now().strftime('%H:%M:%S'), self.username)
            
            self.message_entry.delete(0, tk.END)
        except Exception as e:
            self.display_message(f"Fallo al enviar: {str(e)}", 'system')
    
    def start_private_chat(self, event=None):
        """Iniciar chat privado"""
        selection = self.user_listbox.curselection()
        if selection:
            user_text = self.user_listbox.get(selection[0])
            target = user_text.replace("👤 ", "").replace(" (Yo)", "")
            
            if target != self.username:
                self.message_entry.delete(0, tk.END)
                self.message_entry.insert(0, f"/msg {target} ")
                self.message_entry.focus()
    
    def send_private_message(self, target, message):
        """Enviar mensaje privado"""
        data = json.dumps({
            'type': 'private',
            'to': target,
            'message': message
        })
        try:
            self.client.send(data.encode('utf-8'))
            self.display_message(f"[Privado → {target}] {message}", 'private', 
                               datetime.now().strftime('%H:%M:%S'))
        except Exception as e:
            self.display_message(f"Fallo al enviar: {str(e)}", 'system')
    
    def send_file(self):
        """Enviar archivo"""
        selection = self.user_listbox.curselection()
        target = None
        if selection:
            user_text = self.user_listbox.get(selection[0])
            target = user_text.replace("👤 ", "").replace(" (Yo)", "")
            if target == self.username:
                target = None
                if not messagebox.askyesno("Enviar archivo", "Ningún usuario seleccionado, ¿enviar a todos?"):
                    return
        
        filepath = filedialog.askopenfilename()
        if not filepath:
            return
        
        try:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            file_info = json.dumps({
                'type': 'file_start',
                'filename': filename,
                'size': file_size,
                'to': target
            })
            self.client.send(file_info.encode('utf-8'))
            
            # Pequeña pausa para que el servidor esté listo
            time.sleep(0.1)
            
            with open(filepath, 'rb') as f:
                self.client.sendall(f.read())
            
            if target:
                self.display_message(f"Archivo enviado a {target}: {filename} ({file_size} bytes)", 'file', 
                                   datetime.now().strftime('%H:%M:%S'))
            else:
                self.display_message(f"Archivo difundido: {filename} ({file_size} bytes)", 'file', 
                                   datetime.now().strftime('%H:%M:%S'))
            
        except Exception as e:
            messagebox.showerror("Fallo al enviar archivo", str(e))
    
    def save_received_file(self, file_info, file_data):
        """Guardar archivo recibido"""
        from_user = file_info.get('from', 'unknown')
        filename = file_info['filename']
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_name = f"received/{timestamp}_{from_user}_{filename}"
        
        os.makedirs('received', exist_ok=True)
        
        try:
            with open(save_name, 'wb') as f:
                f.write(file_data)
            self.display_message(f"Archivo guardado: {save_name} ({len(file_data)} bytes)", 'file')
        except Exception as e:
            self.display_message(f"Fallo al guardar: {str(e)}", 'system')
    
    def on_closing(self):
        """Cerrar ventana"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.root.destroy()
    
    def run(self):
        """Ejecutar el cliente"""
        self.root.mainloop()

if __name__ == "__main__":
    client = ChatClient()
    client.run()
