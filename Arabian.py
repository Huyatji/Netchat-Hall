import socket
import threading
import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

class ChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("غرفة الدردشة الشبكية")  # 网络聊天室
        
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
        if os.name == 'nt' and sys.getwindowsversion().major >= 5:
            self.fnt='Tahoma'
        else:
            self.fnt='TkDefaultFont'
        
        self.setup_login_ui()
    
    def setup_login_ui(self):
        """设置登录界面"""
        self.login_frame = ttk.Frame(self.root, padding="20")
        self.login_frame.pack(expand=True)
        
        ttk.Label(self.login_frame, text="مرحباً بك في غرفة الدردشة", font=(self.fnt, 18, 'bold')).pack(pady=20)  # 欢迎来到聊天室
        
        ttk.Label(self.login_frame, text="اسم المستخدم:", font=(self.fnt, 11)).pack(pady=5)  # 用户名
        self.username_entry = ttk.Entry(self.login_frame, width=30, font=(self.fnt, 11))
        self.username_entry.pack(pady=5)
        self.username_entry.focus()
        
        ttk.Label(self.login_frame, text="عنوان الخادم:", font=(self.fnt, 11)).pack(pady=5)  # 服务器地址
        self.host_entry = ttk.Entry(self.login_frame, width=30, font=(self.fnt, 11))
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(pady=5)
        
        ttk.Label(self.login_frame, text="المنفذ:", font=(self.fnt, 11)).pack(pady=5)  # 端口
        self.port_entry = ttk.Entry(self.login_frame, width=30, font=(self.fnt, 11))
        self.port_entry.insert(0, "55555")
        self.port_entry.pack(pady=5)
        
        ttk.Button(self.login_frame, text="اتصال", command=self.connect_to_server).pack(pady=20)  # 连接
        
        # 绑定回车键到连接按钮
        self.root.bind('<Return>', lambda e: self.connect_to_server())
    
    def setup_chat_ui(self):
        """设置聊天界面"""
        # 销毁登录界面
        self.login_frame.destroy()
        
        # ⭐ 解绑登录时的回车键
        self.root.unbind('<Return>')
        
        # 创建主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧：用户列表
        left_frame = ttk.Frame(main_container, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        ttk.Label(left_frame, text="المستخدمون المتصلون", font=(self.fnt, 11, 'bold')).pack(pady=5)  # 在线用户
        
        self.user_listbox = tk.Listbox(left_frame, font=(self.fnt, 10))
        self.user_listbox.pack(fill=tk.BOTH, expand=True)
        self.user_listbox.bind('<Double-Button-1>', self.start_private_chat)
        
        # 右侧：聊天区域
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 聊天消息显示区域
        self.chat_display = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, 
                                                       font=(self.fnt, 10), state='disabled')
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # 配置消息标签
        self.chat_display.tag_config('system', foreground='gray')
        self.chat_display.tag_config('private', foreground='purple')
        self.chat_display.tag_config('file', foreground='blue')
        self.chat_display.tag_config('username', foreground='dark green', font=(self.fnt, 10, 'bold'))
        self.chat_display.tag_config('own_message', foreground='black')
        
        # 底部：输入区域
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 消息输入框
        self.message_entry = ttk.Entry(bottom_frame, font=(self.fnt, 10))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # ⭐ 绑定消息输入框的回车键到发送消息
        self.message_entry.bind('<Return>', self.send_message)
        
        # 发送按钮
        ttk.Button(bottom_frame, text="إرسال", command=self.send_message).pack(side=tk.RIGHT, padx=2)  # 发送
        
        # 文件按钮
        ttk.Button(bottom_frame, text="📎 ملف", command=self.send_file).pack(side=tk.RIGHT, padx=2)  # 📎 文件
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 获取输入焦点
        self.message_entry.focus()
    
    def connect_to_server(self):
        """连接到服务器"""
        username = self.username_entry.get().strip()
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        
        if not username:
            messagebox.showerror("خطأ", "الرجاء إدخال اسم المستخدم")  # 错误 / 请输入用户名
            return
        
        try:
            port = int(port)
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(10)
            self.client.connect((host, port))
            self.client.send(username.encode('utf-8'))
            
            self.username = username
            self.root.title(f"غرفة الدردشة الشبكية - {username}")  # 网络聊天室 - {用户名}
            self.setup_chat_ui()
            
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            self.display_message(f"تم الاتصال بالخادم {host}:{port}", 'system')  # 成功连接到服务器 {host}:{port}
            
        except socket.timeout:
            messagebox.showerror("انتهاء المهلة", "انتهت مهلة الاتصال بالخادم، يرجى التحقق من عنوان الخادم والمنفذ")  # 连接超时 / 连接服务器超时...
        except ConnectionRefusedError:
            messagebox.showerror("رفض الاتصال", "الخادم رفض الاتصال، يرجى التأكد من تشغيل الخادم")  # 连接被拒绝 / 服务器拒绝连接...
        except Exception as e:
            messagebox.showerror("فشل الاتصال", f"تعذر الاتصال بالخادم: {str(e)}")  # 连接失败 / 无法连接到服务器...
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
                self.client = None
    
    def receive_messages(self):
        """接收消息"""
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
                                self.display_message("انقطع نقل الملف", 'system')  # 文件传输中断
                                break
                            file_data_buffer += chunk
                        except socket.timeout:
                            continue
                        except Exception as e:
                            self.display_message(f"خطأ في استلام الملف: {str(e)}", 'system')  # 文件接收错误
                            break
                    
                    if len(file_data_buffer) == expected_file_size:
                        self.save_received_file(file_info, file_data_buffer)
                    else:
                        self.display_message(f"استلام الملف غير مكتمل", 'system')  # 文件接收不完整
                    
                    file_data_buffer = b''
                    expecting_file = False
                    file_info = None
                    continue
                
                try:
                    data = self.client.recv(self.buffer_size)
                    if not data:
                        self.display_message("تم قطع الاتصال بالخادم", 'system')  # 与服务器断开连接
                        break
                except socket.timeout:
                    continue
                except Exception as e:
                    self.display_message(f"خطأ في استلام البيانات: {str(e)}", 'system')  # 接收数据错误
                    break
                
                message = data.decode('utf-8')
                
                try:
                    msg_data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                
                if msg_data['type'] == 'user_list':
                    self.update_user_list(msg_data['users'])
                
                elif msg_data['type'] == 'system':
                    self.display_message(self.lang_dict['ar'][msg_data['lang_key']].format(msg_data['fmt']), 'system', msg_data.get('time'))
                    
                elif msg_data['type'] == 'public':
                    self.display_message(f"{msg_data['username']}: {msg_data['message']}", 
                                       'public', msg_data['time'], msg_data['username'])
                
                elif msg_data['type'] == 'private':
                    self.display_message(f"[خاص] {msg_data['from']}: {msg_data['message']}",  # [私聊] → [خاص]
                                       'private', msg_data['time'])
                
                elif msg_data['type'] == 'file':
                    file_info = msg_data
                    try:
                        size_bytes = self.client.recv(8)
                        if len(size_bytes) == 8:
                            expected_file_size = int.from_bytes(size_bytes, byteorder='big')
                            expecting_file = True
                            self.display_message(f"تم استلام ملف: {msg_data['filename']} ({expected_file_size} بايت)",  # 收到文件: ... bytes
                                               'file', msg_data['time'])
                        else:
                            self.display_message("معلومات حجم الملف غير صحيحة", 'system')  # 文件大小信息错误
                    except Exception as e:
                        self.display_message(f"خطأ في التحضير لاستلام الملف: {str(e)}", 'system')  # 文件接收准备错误
                    
            except Exception as e:
                if self.client:
                    self.display_message(f"خطأ في الاتصال: {str(e)}", 'system')  # 连接错误
                break
    
    def display_message(self, message, msg_type='public', time=None, username=None):
        """显示消息"""
        try:
            self.chat_display.configure(state='normal')
            
            if time:
                self.chat_display.insert(tk.END, f"[{time}] ", 'system')
            
            if msg_type == 'public' and username:
                if username == self.username:
                    self.chat_display.insert(tk.END, "أنا", 'own_message')  # 我 → أنا
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
            print(f"خطأ في عرض الرسالة: {e}")  # 显示消息错误
    
    def update_user_list(self, users):
        """更新在线用户列表"""
        try:
            self.user_listbox.delete(0, tk.END)
            for user in users:
                display_text = f"👤 {user}"
                if user == self.username:
                    display_text += " (أنا)"  # (我) → (أنا)
                self.user_listbox.insert(tk.END, display_text)
        except Exception as e:
            print(f"خطأ في تحديث قائمة المستخدمين: {e}")  # 更新用户列表错误
    
    def send_message(self, event=None):
        """发送消息"""
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
                    self.display_message("الاستخدام: /msg اسم_المستخدم نص_الرسالة", 'system')  # 用法: /msg 用户名 消息内容
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
            self.display_message(f"فشل الإرسال: {str(e)}", 'system')  # 发送失败
    
    def start_private_chat(self, event=None):
        """开始私聊"""
        selection = self.user_listbox.curselection()
        if selection:
            user_text = self.user_listbox.get(selection[0])
            target = user_text.replace("👤 ", "").replace(" (أنا)", "")
            
            if target != self.username:
                self.message_entry.delete(0, tk.END)
                self.message_entry.insert(0, f"/msg {target} ")
                self.message_entry.focus()
    
    def send_private_message(self, target, message):
        """发送私聊消息"""
        data = json.dumps({
            'type': 'private',
            'to': target,
            'message': message
        })
        try:
            self.client.send(data.encode('utf-8'))
            self.display_message(f"[خاص → {target}] {message}", 'private',  # [私聊 → {target}] → [خاص → {target}]
                               datetime.now().strftime('%H:%M:%S'))
        except Exception as e:
            self.display_message(f"فشل الإرسال: {str(e)}", 'system')  # 发送失败
    
    def send_file(self):
        """发送文件"""
        selection = self.user_listbox.curselection()
        target = None
        if selection:
            user_text = self.user_listbox.get(selection[0])
            target = user_text.replace("👤 ", "").replace(" (أنا)", "")
            if target == self.username:
                target = None
                if not messagebox.askyesno("إرسال ملف", "لم يتم تحديد مستخدم، هل تريد الإرسال للجميع؟"):  # 发送文件 / 未选择用户，发送给所有人?
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
            
            # 短暂延迟确保服务器准备好接收
            time.sleep(0.1)
            
            with open(filepath, 'rb') as f:
                self.client.sendall(f.read())
            
            if target:
                self.display_message(f"تم إرسال الملف إلى {target}: {filename} ({file_size} بايت)", 'file',  # 文件已发送给 {target}: ...
                                   datetime.now().strftime('%H:%M:%S'))
            else:
                self.display_message(f"تم بث الملف: {filename} ({file_size} بايت)", 'file',  # 文件已广播: ...
                                   datetime.now().strftime('%H:%M:%S'))
            
        except Exception as e:
            messagebox.showerror("فشل إرسال الملف", str(e))  # 文件发送失败
    
    def save_received_file(self, file_info, file_data):
        """保存接收到的文件"""
        from_user = file_info.get('from', 'unknown')
        filename = file_info['filename']
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_name = f"received/{timestamp}_{from_user}_{filename}"
        
        os.makedirs('received', exist_ok=True)
        
        try:
            with open(save_name, 'wb') as f:
                f.write(file_data)
            self.display_message(f"تم حفظ الملف: {save_name} ({len(file_data)} بايت)", 'file')  # 文件已保存: ...
        except Exception as e:
            self.display_message(f"فشل حفظ الملف: {str(e)}", 'system')  # 文件保存失败
    
    def on_closing(self):
        """关闭窗口"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.root.destroy()
    
    def run(self):
        """运行客户端"""
        self.root.mainloop()

if __name__ == "__main__":
    client = ChatClient()
    client.run()
