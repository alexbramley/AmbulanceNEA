import socket
import threading
import time


class SecureSocket(object):
	def __repr__(self):
		return f"SecureSocket object    hostadress: {self._HOSTADDRESS}    hostname: {self._HOSTNAME}    port: {self._PORT}"
	
	def __init__(self, PORT, HEADER, FORMAT, DISCONN_MSG):
		self._PORT = PORT
		self._HOSTNAME = socket.gethostname()
		self._HOSTADDRESS = socket.gethostbyname(self._HOSTNAME)
		self._ADDR = (self._HOSTADDRESS, self._PORT)
		self._HEADER = HEADER
		self._FORMAT = FORMAT
		self._DISCONN_MSG = DISCONN_MSG
		self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._server.bind(self._ADDR)
		self._conns = []

		self._server_thread = threading.Thread(target=self._start)
		self._server_thread.start()



	def _start(self):
		print(f"[STARTING] server is starting...")
		self._server.listen()
		print(f"[LISTENING] server is listening on {self._ADDR}")
		while True:
			conn, addr = self._server.accept()
			self._conns.append(SecureConnection(self, conn, addr))
			print(f"[ACTIVE CONNECTIONS] {len(self._conns)}")
	
	def remove_conn(self, conn_to_remove):
		self._conns.remove(conn_to_remove)

	def get_header(self):
		return self._HEADER
	
	def get_format(self):
		return self._FORMAT
	
	def get_disconn_msg(self):
		return self._DISCONN_MSG



class SecureConnection(object):
	def __init__(self, sock:SecureSocket, conn:socket, addr):
		self._sock = sock
		self._conn = conn
		self._addr = addr

		self._conn_thread = threading.Thread(target=self._handle_conn)
		self.start()

	def _handle_conn(self):
		print(f"[NEW CONNECTION] {self._addr} connected.")

		connected = True
		while connected:
			msg_length = int(self._conn.recv(self._sock.get_header()).decode(self._sock.get_format()))

			msg = self._conn.recv(msg_length).decode(self._sock.get_format())

			if msg == self._sock.get_disconn_msg():
				connected = False

			print(f"[{self._addr}] f{msg}")

		self._handle_disconn()

	def _handle_disconn(self):
		self._conn.close()
		self._sock.remove_conn(self)


print(SecureSocket(42067, 64, "utf-8", "!DISCONN"))