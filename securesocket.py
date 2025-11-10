import socket
import threading
import time
import rsa

# these keys are used for data transfer during the initial handshake in a connection, before the two parties have exchanged new randomly generated keys

with open("default-public.pem","rb") as f:
	DEFAULT_PUBLIC_KEY = rsa.PublicKey.load_pkcs1(f.read())

with open("default-private.pem","rb") as f:
	DEFAULT_PRIVATE_KEY = rsa.PrivateKey.load_pkcs1(f.read())

print(rsa.decrypt(rsa.encrypt("test message".encode("utf-8"), DEFAULT_PUBLIC_KEY), DEFAULT_PRIVATE_KEY).decode("utf-8"))

class SecureSocket(object):
	def __repr__(self):
		return f"SecureSocket object    hostadress: {self._HOSTADDRESS}    hostname: {self._HOSTNAME}    port: {self._PORT}"
	
	def __init__(self, PORT, HEADER, FORMAT, DISCONN_MSG, HANDSHAKE_MSG):
		self._online = False
		self._PORT = PORT
		self._HOSTNAME = socket.gethostname()
		self._HOSTADDRESS = socket.gethostbyname(self._HOSTNAME)
		self._ADDR = (self._HOSTADDRESS, self._PORT)
		self._HEADER = HEADER
		self._FORMAT = FORMAT
		self._DISCONN_MSG = DISCONN_MSG
		self._HANDSHAKE_MSG = HANDSHAKE_MSG
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
				conn.start_disconn(False)
			self._master_conn.close()
			self._conns = []
			print("successfully closed the master connection")


	def _master(self):
		print(f"[STARTING] master is starting...")
		
	
	
	def remove_conn(self, conn_to_remove):
		try:
			self._conns.remove(conn_to_remove)
		except:
			raise Exception(f"Cannot remove {conn_to_remove} from {self._conns}")

	def get_header(self):
		return self._HEADER
	
	def get_format(self):
		return self._FORMAT
	
	def get_disconn_msg(self):
		return self._DISCONN_MSG
	
	def get_handshake_msg(self):
		return self._HANDSHAKE_MSG
	

class Server(SecureSocket):
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
	def __init__(self, PORT, HEADER, FORMAT, DISCONN_MSG, HANDSHAKE_MSG, TARGET_HOSTADDRESS):
		super().__init__(PORT, HEADER, FORMAT, DISCONN_MSG, HANDSHAKE_MSG)
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

	def get_conn(self):
		if len(self._conns) == 0:
			raise Exception("There is no active connection")
		return self._conns[0]



class SecureConnection(object):
	def __init__(self, sock:SecureSocket, conn:socket.socket, addr):
		self._sock = sock
		self._conn = conn
		self._addr = addr
		self._connected = False

		

		self._public_key = DEFAULT_PUBLIC_KEY
		self._private_key = DEFAULT_PRIVATE_KEY
		self._recipient_public_key = DEFAULT_PUBLIC_KEY

		self._conn_thread = threading.Thread(target=self._handle_conn)
		self._conn_thread.start()

	def _handle_conn(self):
		print(f"[NEW CONNECTION] {self._addr} connected.")
		self._connected = True

		if type(self._sock) == Server:
			if not self._start_handshake():
				self.start_disconn(True)


		while self._connected:
			try:
				msg = self._receive()
			except:
				continue # if we can't receive anymore then that means this connection has shutdown

			print(f"[{self._addr}] {msg}")

			if msg == self._sock.get_disconn_msg():
				self._handle_disconn()
			elif msg == self._sock.get_handshake_msg():
				self._handle_handshake()

	def _receive(self):
		print("we are getting a brand new message")
		encrypted_msg_length_bytes = self._conn.recv(128)
		print(f"received length of message {encrypted_msg_length_bytes}\n")
		msg_length_bytes = rsa.decrypt(encrypted_msg_length_bytes, DEFAULT_PRIVATE_KEY)
		print(f"decrypted length of message {msg_length_bytes}\n")
		msg_length_text = msg_length_bytes.decode(self._sock.get_format())

		if not msg_length_text:
			return ""
		print(f"message is {msg_length_text} bits long")
		msg_length = int(msg_length_text)

		encrypted_message = self._conn.recv(128)
		print(f"received message {encrypted_message}\n")
		message = rsa.decrypt(encrypted_message, DEFAULT_PRIVATE_KEY).decode(self._sock.get_format())

		return message


	def send(self, msg:str):
		if not self._connected:
			raise Exception("Cannot send as not connected")
		print(f"sending message: {msg}")
		
		message = msg.encode(self._sock.get_format())
		encrypted_message = rsa.encrypt(message, DEFAULT_PUBLIC_KEY)
		
		msg_length = len(encrypted_message)
		send_length = str(msg_length).encode(self._sock.get_format())
		send_length += b" " * (self._sock.get_header() - len(send_length))
		
		encrypted_send_length = rsa.encrypt(send_length, DEFAULT_PUBLIC_KEY)

		self._conn.send(encrypted_send_length)
		print(f"sent length {rsa.decrypt(encrypted_send_length, DEFAULT_PRIVATE_KEY)}\n")
		time.sleep(0.1)
		self._conn.send(encrypted_message)
		print(f"sent msg {rsa.decrypt(encrypted_message, DEFAULT_PRIVATE_KEY)}\n")
		time.sleep(0.1)


	def _start_handshake(self):
		try:
			self.send(self._sock.get_handshake_msg())
			print("handshake message sent!")
			
			response = self._receive()
			print(response)
			
			if response != self._sock.get_handshake_msg():
				return False
			
			#self._public_key, self._private_key = rsa.newkeys(1024)

			
			return True
		except Exception as e:
			print(f"Handshake failed: {e}")
			return False

	def _handle_handshake(self):
		self.send(self._sock.get_handshake_msg())

	def start_disconn(self, removeconnfromsock:bool): # runs if we initiated the disconn
		print("we ended the connection")
		self.send(self._sock.get_disconn_msg())
		self._disconn(removeconnfromsock)

	def _handle_disconn(self): # runs if the disconn was initiated by the other side
		print("they ended the connection")
		self._disconn(True)

	def _disconn(self, removeconnfromsock:bool): # removeconnfromsock should usually be true, as after a conn has been disconned, it should no longer be in the list of conns on the sock obj, but for example if conns in the sock are being iterated through to be disconned, we shouldn't remove an item from the list that's being iterated through
		try:
			self._conn.shutdown(socket.SHUT_RDWR)
		except:
			print("Failed to shutdown the connection")
		self._connected = False
		self._conn.close()
		if removeconnfromsock:
			self._sock.remove_conn(self)