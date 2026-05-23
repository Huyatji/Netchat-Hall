import socket
import threading
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime

class ChatServerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("聊天室服务器")
        self.root.iconbitmap("svr.ico")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 服务器相关
        self.server = None
        self.clients = {}
        self.buffer_size = 4096
        self.is_running = False
        self.server_thread = None
        self.lock = threading.Lock()
        
        if os.name == 'nt' and sys.getwindowsversion().major >= 6:
            self.fnt='Microsoft Yahei UI'
        else:
            self.fnt='TkDefaultFont'
        
        self.setup_ui()
        self.get_local_ip()
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """设置GUI界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部：服务器配置
        config_frame = ttk.LabelFrame(main_frame, text="服务器配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # IP地址
        ttk.Label(config_frame, text="IP地址:", font=(self.fnt, 10)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip_var = tk.StringVar()
        self.ip_combo = ttk.Combobox(config_frame, textvariable=self.ip_var, state='readonly', 
                                      width=20, font=(self.fnt, 10))
        self.ip_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(config_frame, text="刷新", command=self.get_local_ip, width=8).grid(row=0, column=2, padx=5, pady=5)
        
        # 端口
        ttk.Label(config_frame, text="端口:", font=(self.fnt, 10)).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        self.port_var = tk.StringVar(value="55555")
        self.port_spinbox = ttk.Spinbox(config_frame, from_=1024, to=65535, textvariable=self.port_var,
                                         width=10, font=(self.fnt, 10))
        self.port_spinbox.grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        
        # 启动/停止按钮
        self.start_button = ttk.Button(config_frame, text="▶ 启动服务器", command=self.toggle_server, width=15)
        self.start_button.grid(row=0, column=5, padx=10, pady=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="● 服务器未启动")
        status_label = ttk.Label(config_frame, textvariable=self.status_var, 
                                 font=(self.fnt, 10, 'bold'))
        status_label.grid(row=0, column=6, padx=20, pady=5)
        
        # 中间：客户端列表和信息
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：在线客户端列表
        clients_frame = ttk.LabelFrame(middle_frame, text="在线客户端", padding="5")
        clients_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        columns = ('用户名', 'IP地址', '连接时间')
        self.clients_tree = ttk.Treeview(clients_frame, columns=columns, show='headings', height=8)
        
        self.clients_tree.heading('用户名', text='用户名')
        self.clients_tree.heading('IP地址', text='IP地址')
        self.clients_tree.heading('连接时间', text='连接时间')
        
        self.clients_tree.column('用户名', width=120)
        self.clients_tree.column('IP地址', width=150)
        self.clients_tree.column('连接时间', width=120)
        
        clients_scroll = ttk.Scrollbar(clients_frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=clients_scroll.set)
        
        self.clients_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        clients_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右侧：日志显示
        log_frame = ttk.LabelFrame(middle_frame, text="服务器日志", padding="5")
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                      font=('Consolas', 9), state='disabled')
        self.log_display.pack(fill=tk.BOTH, expand=True)
        
        self.log_display.tag_config('info', foreground='blue')
        self.log_display.tag_config('warning', foreground='orange')
        self.log_display.tag_config('error', foreground='red')
        self.log_display.tag_config('success', foreground='green')
        self.log_display.tag_config('timestamp', foreground='gray')
        
        # 底部：统计信息
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.stats_var = tk.StringVar(value="当前在线: 0")
        ttk.Label(stats_frame, textvariable=self.stats_var, font=(self.fnt, 9)).pack(side=tk.LEFT)
        
        ttk.Label(stats_frame, text="双击客户端可踢出", font=(self.fnt, 9)).pack(side=tk.RIGHT)
        
        self.clients_tree.bind('<Double-Button-1>', self.kick_client)
    
    def get_local_ip(self):
        """获取本机局域网IP地址"""
        ip_list = []
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip != '127.0.0.1':
                ip_list.append(local_ip)
            
            for iface in socket.getaddrinfo(hostname, None):
                ip = iface[4][0]
                if ip not in ip_list and not ip.startswith('127.'):
                    ip_list.append(ip)
        except:
            pass
        
        if not ip_list:
            ip_list = ['127.0.0.1']
        
        ip_list.insert(0, '0.0.0.0')
        
        self.ip_combo['values'] = ip_list
        if ip_list:
            self.ip_combo.set(ip_list[0])
        
        self.log(f"检测到本地IP地址: {', '.join(ip_list[1:] if len(ip_list) > 1 else ip_list)}", 'info')
    
    def toggle_server(self):
        """启动/停止服务器"""
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """启动服务器"""
        host = self.ip_var.get()
        port_str = self.port_var.get()
        
        try:
            port = int(port_str)
            if port < 1024 or port > 65535:
                raise ValueError("端口范围: 1024-65535")
        except ValueError as e:
            messagebox.showerror("端口错误", str(e))
            return
        
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((host, port))
            self.server.listen(5)
            self.server.settimeout(1)
            
            self.is_running = True
            self.update_ui_state(True)
            
            self.log(f"服务器启动成功 - {host}:{port}", 'success')
            self.status_var.set("● 服务器运行中")
            
            self.server_thread = threading.Thread(target=self.accept_clients)
            self.server_thread.daemon = True
            self.server_thread.start()
            
        except Exception as e:
            self.log(f"启动失败: {str(e)}", 'error')
            messagebox.showerror("启动失败", str(e))
            if self.server:
                self.server.close()
                self.server = None
    
    def stop_server(self):
        """停止服务器"""
        self.log("正在关闭服务器...", 'warning')
        self.is_running = False
        
        with self.lock:
            for client_socket in list(self.clients.keys()):
                self.remove_client(client_socket, "服务器关闭")
        
        if self.server:
            try:
                self.server.close()
            except:
                pass
            self.server = None
        
        self.update_ui_state(False)
        self.status_var.set("● 服务器未启动")
        self.log("服务器已停止", 'info')
    
    def update_ui_state(self, running):
        """更新UI状态"""
        if running:
            self.start_button.configure(text="■ 停止服务器")
            self.ip_combo.configure(state='disabled')
            self.port_spinbox.configure(state='disabled')
        else:
            self.start_button.configure(text="▶ 启动服务器")
            self.ip_combo.configure(state='readonly')
            self.port_spinbox.configure(state='!disabled')
    
    def accept_clients(self):
        """接受客户端连接"""
        while self.is_running:
            try:
                client_socket, address = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    self.log(f"接受连接时出错: {str(e)}", 'error')
                break
    
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        username = None
        try:
            data = client_socket.recv(self.buffer_size)
            if not data:
                return
            
            username = data.decode('utf-8')
            
            with self.lock:
                for info in self.clients.values():
                    if info['username'] == username:
                        error_msg = json.dumps({
                            'type': 'system',
                            'lang_key': 'used_user_name', # '用户名已被使用，请更换用户名重试'
                            'fmt':''
                        })
                        client_socket.send(error_msg.encode('utf-8'))
                        client_socket.close()
                        self.log(f"用户名 {username} 重复，拒绝连接", 'warning')
                        return
                
                connect_time = datetime.now().strftime('%H:%M:%S')
                self.clients[client_socket] = {
                    'username': username,
                    'address': f"{address[0]}:{address[1]}",
                    'connect_time': connect_time
                }
            
            self.root.after(0, self.add_client_to_list, username, address[0], connect_time)
            
            self.log(f"新客户端连接: {username} 从 {address[0]}:{address[1]}", 'success')
            
            welcome_msg = json.dumps({
                'type': 'system',
                'lang_key': 'welcome_join',
                'fmt':username,
                'time': datetime.now().strftime('%H:%M:%S')
            })
            self.broadcast(welcome_msg, client_socket)
            self.update_user_list()
            
            while self.is_running:
                try:
                    data = client_socket.recv(self.buffer_size)
                    if not data:
                        break
                    
                    message = data.decode('utf-8')
                    
                    try:
                        msg_data = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    
                    if msg_data['type'] == 'public':
                        msg = json.dumps({
                            'type': 'public',
                            'username': username,
                            'message': msg_data['message'],
                            'time': datetime.now().strftime('%H:%M:%S')
                        })
                        self.broadcast(msg, client_socket)
                        self.log(f"[公共消息] {username}: {msg_data['message'][:50]}", 'info')
                    
                    elif msg_data['type'] == 'private':
                        msg = json.dumps({
                            'type': 'private',
                            'from': username,
                            'message': msg_data['message'],
                            'time': datetime.now().strftime('%H:%M:%S')
                        })
                        success = self.send_private_message(msg, msg_data['to'], client_socket)
                        if not success:
                            error_msg = json.dumps({
                                'type': 'system',
                                'lang_key': "usr_not_exist", #f'用户 {msg_data["to"]} 不存在或已离线'
                                'fmt':msg_data["to"]
                            })
                            client_socket.send(error_msg.encode('utf-8'))
                            self.log(f"私聊失败: 用户 {msg_data['to']} 不存在", 'warning')
                        else:
                            self.log(f"[私聊] {username} -> {msg_data['to']}: {msg_data['message'][:50]}", 'info')
                    
                    elif msg_data['type'] == 'file_start':
                        self.log(f"[文件传输] {username} 正在发送文件: {msg_data['filename']}", 'info')
                        self.handle_file_receive(client_socket, username, msg_data)
                        
                except Exception as e:
                    if self.is_running:
                        self.log(f"处理消息时出错: {str(e)}", 'error')
                    break
                    
        except Exception as e:
            self.log(f"客户端处理错误: {str(e)}", 'error')
        finally:
            if username:
                self.remove_client(client_socket, "断开连接")
            else:
                try:
                    client_socket.close()
                except:
                    pass
    
    def handle_file_receive(self, client_socket, username, data):
        """处理文件接收和转发"""
        try:
            file_size = data['size']
            target = data.get('to')
            
            file_data = b''
            while len(file_data) < file_size:
                chunk = client_socket.recv(min(self.buffer_size, file_size - len(file_data)))
                if not chunk:
                    break
                file_data += chunk
            
            if target:
                file_msg = json.dumps({
                    'type': 'file',
                    'from': username,
                    'filename': data['filename'],
                    'size': file_size,
                    'time': datetime.now().strftime('%H:%M:%S')
                })
                
                with self.lock:
                    for client, info in self.clients.items():
                        if info['username'] == target:
                            try:
                                client.send(file_msg.encode('utf-8'))
                                client.send(file_size.to_bytes(8, byteorder='big'))
                                client.send(file_data)
                                self.log(f"[文件] {username} -> {target}: {data['filename']} ({file_size} bytes)", 'info')
                                break
                            except:
                                self.remove_client(client, "发送文件失败")
            else:
                file_msg = json.dumps({
                    'type': 'file',
                    'from': username,
                    'filename': data['filename'],
                    'size': file_size,
                    'time': datetime.now().strftime('%H:%M:%S')
                })
                
                with self.lock:
                    for client in list(self.clients.keys()):
                        if client != client_socket:
                            try:
                                client.send(file_msg.encode('utf-8'))
                                client.send(file_size.to_bytes(8, byteorder='big'))
                                client.send(file_data)
                            except:
                                self.remove_client(client, "发送文件失败")
                
                self.log(f"[文件广播] {username}: {data['filename']} ({file_size} bytes)", 'info')
                    
        except Exception as e:
            self.log(f"文件传输错误: {str(e)}", 'error')
    
    def broadcast(self, message, sender_socket=None):
        """广播消息给所有客户端"""
        failed_clients = []
        
        with self.lock:
            for client in list(self.clients.keys()):
                if client != sender_socket:
                    try:
                        client.send(message.encode('utf-8'))
                    except:
                        failed_clients.append(client)
        
        for client in failed_clients:
            self.remove_client(client, "消息发送失败")
    
    def send_private_message(self, message, target_username, sender_socket):
        """发送私聊消息"""
        with self.lock:
            for client, info in self.clients.items():
                if info['username'] == target_username:
                    try:
                        client.send(message.encode('utf-8'))
                        return True
                    except:
                        self.remove_client(client, "发送私聊消息失败")
                        return False
        return False
    
    def update_user_list(self):
        """更新所有客户端的在线用户列表"""
        with self.lock:
            users = [info['username'] for info in self.clients.values()]
            user_list_msg = json.dumps({
                'type': 'user_list',
                'users': users
            })
            
            failed_clients = []
            for client in list(self.clients.keys()):
                try:
                    client.send(user_list_msg.encode('utf-8'))
                except:
                    failed_clients.append(client)
            
            for client in failed_clients:
                self.remove_client(client, "更新用户列表失败")
    
    def remove_client(self, client_socket, reason=""):
        """移除客户端"""
        with self.lock:
            if client_socket in self.clients:
                username = self.clients[client_socket]['username']
                address = self.clients[client_socket]['address']
                del self.clients[client_socket]
                
                try:
                    client_socket.close()
                except:
                    pass
                
                self.root.after(0, self.remove_client_from_list, username)
                
                leave_msg = json.dumps({
                    'type': 'system',
                    'message': f'{username} 离开了聊天室',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
                
                if reason:
                    self.log(f"客户端断开: {username} ({address}) - {reason}", 'warning')
                else:
                    self.log(f"客户端断开: {username} ({address})", 'info')
                
                self.broadcast(leave_msg)
                self.update_user_list()
    
    def add_client_to_list(self, username, ip, time):
        """添加客户端到列表"""
        self.clients_tree.insert('', 'end', values=(username, ip, time))
        self.update_stats()
    
    def remove_client_from_list(self, username):
        """从列表中移除客户端"""
        for item in self.clients_tree.get_children():
            if self.clients_tree.item(item)['values'][0] == username:
                self.clients_tree.delete(item)
                break
        self.update_stats()
    
    def kick_client(self, event):
        """踢出客户端"""
        selection = self.clients_tree.selection()
        if selection:
            username = self.clients_tree.item(selection[0])['values'][0]
            if messagebox.askyesno("踢出客户端", f"确定要踢出 {username} 吗？"):
                with self.lock:
                    for client_socket, info in list(self.clients.items()):
                        if info['username'] == username:
                            try:
                                kick_msg = json.dumps({
                                    'type': 'system',
                                    'message': 'kicked',
                                    'fmt':''
                                })
                                client_socket.send(kick_msg.encode('utf-8'))
                            except:
                                pass
                            self.remove_client(client_socket, "被管理员踢出")
                            break
    
    def update_stats(self):
        """更新统计信息"""
        online_count = len(self.clients)
        self.stats_var.set(f"当前在线: {online_count}")
    
    def log(self, message, tag=''):
        """添加日志"""
        self.log_display.configure(state='normal')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        self.log_display.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        if tag:
            self.log_display.insert(tk.END, f"{message}\n", tag)
        else:
            self.log_display.insert(tk.END, f"{message}\n")
        
        self.log_display.see(tk.END)
        self.log_display.configure(state='disabled')
    
    def on_closing(self):
        """关闭窗口"""
        if self.is_running:
            if messagebox.askyesno("关闭服务器", "服务器正在运行，确定要关闭吗？"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """运行服务器GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    server_gui = ChatServerGUI()
    server_gui.run()
