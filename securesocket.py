import socket
import threading
import time


class SecureSocket(object):
	def __repr__(self):
		return f"SecureSocket object    hostadress: {self._HOSTADDRESS}    hostname: {self._HOSTNAME}    port: {self._PORT}"
	
	def __init__(self, PORT, HEADER, FORMAT, DISCONN_MSG):
		self._online = False
		self._PORT = PORT
		self._HOSTNAME = socket.gethostname()
		self._HOSTADDRESS = socket.gethostbyname(self._HOSTNAME)
		self._ADDR = (self._HOSTADDRESS, self._PORT)
		self._HEADER = HEADER
		self._FORMAT = FORMAT
		self._DISCONN_MSG = DISCONN_MSG
		self._conns = []
		self._master_thread = threading.Thread(target=self._master)
		
	def _setup_master_conn(self):
		self.conns = []
		self._master_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		

	def set_socket_status(self, online:bool):
		self._online = online
		if online:
			self._setup_master_conn()
			self._master_thread = threading.Thread(target=self._master)
			self._master_thread.start()
		else:
			for conn in self._conns:
				conn.start_disconn()
			self._master_conn.close()
			print("successfully closed the master connection")


	def _master(self):
		print(f"[STARTING] master is starting...")
		
	
	def remove_conn(self, conn_to_remove):
		self._conns.remove(conn_to_remove)

	def get_header(self):
		return self._HEADER
	
	def get_format(self):
		return self._FORMAT
	
	def get_disconn_msg(self):
		return self._DISCONN_MSG

class Server(SecureSocket):
	def __init__(self, PORT, HEADER, FORMAT, DISCONN_MSG):
		super().__init__(PORT, HEADER, FORMAT, DISCONN_MSG)
		
	def _setup_master_conn(self):
		super()._setup_master_conn()
		self._master_conn.bind(self._ADDR)
	

	def set_socket_status(self, online: bool):
		if not online:
			self._master_conn.shutdown(socket.SHUT_RDWR)
			print("we shut down master conn")

		super().set_socket_status(online)

	def _master(self):
		super()._master()
		self._master_conn.listen()
		print(f"[LISTENING] server is listening on {self._ADDR}")
		while self._online:
			try:
				conn, addr = self._master_conn.accept()
			except:
				continue # if we are unable to accept a connection, that's because the connection has been shutdown and comms should end
			self._conns.append(SecureConnection(self, conn, addr))
			print(f"[ACTIVE CONNECTIONS] {len(self._conns)}")



class Client(SecureSocket):
	def __init__(self, PORT, HEADER, FORMAT, DISCONN_MSG, TARGET_HOSTADDRESS):
		super().__init__(PORT, HEADER, FORMAT, DISCONN_MSG)
		self._TARGET_HOSTADDRESS = TARGET_HOSTADDRESS
		self._TARGET_ADDR = (self._TARGET_HOSTADDRESS, self._PORT)
		
	def _setup_master_conn(self):
		super()._setup_master_conn()
		self._master_conn.connect(self._TARGET_ADDR)

	def _master(self):
		super()._master()
		self._conns.append(SecureConnection(self, self._master_conn, self._TARGET_ADDR))
		while self._online:
			if len(self._conns) == 0:
				self.set_socket_status(False)
				break

	def send(self, msg):
		self._conns[0].send(msg)



class SecureConnection(object):
	def __init__(self, sock:SecureSocket, conn:socket.socket, addr):
		self._sock = sock
		self._conn = conn
		self._addr = addr
		self._connected = False

		self._conn.settimeout(0.1)

		self._conn_thread = threading.Thread(target=self._handle_conn)
		self._conn_thread.start()

	def _handle_conn(self):
		print(f"[NEW CONNECTION] {self._addr} connected.")

		self._connected = True
		while self._connected:
			try:
				msg_length_text = self._conn.recv(self._sock.get_header()).decode(self._sock.get_format())
			except:
				continue # if we can't receive anymore then that means this connection has shutdown

			if not msg_length_text:
				continue
			
			msg_length = int(msg_length_text)

			try:
				msg = self._conn.recv(msg_length).decode(self._sock.get_format())
			except:
				continue # if we can't receive anymore then that means this connection has shutdown

			print(f"[{self._addr}] {msg}")

			if msg == self._sock.get_disconn_msg():
				self._handle_disconn()


	
	def send(self, msg:str):
		print(f"sending message: {msg}")
		message = msg.encode(self._sock.get_format())
		msg_length = len(message)
		send_length = str(msg_length).encode(self._sock.get_format())
		send_length += b" " * (self._sock.get_header() - len(send_length))
		self._conn.send(send_length)
		self._conn.send(message)
		
	def start_disconn(self): # runs if we initiated the disconn
		print("we ended the connection")
		self.send(self._sock.get_disconn_msg())
		self._disconn()

	def _handle_disconn(self): # runs if the disconn was initiated by the other side
		print("they ended the connection")
		self._sock.remove_conn(self)
		self._disconn()

	def _disconn(self):
		self._conn.shutdown(socket.SHUT_RDWR)
		self._connected = False
		self._conn.close()
