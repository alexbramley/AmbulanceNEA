import socket
import threading
import time
import rsa
import struct

# these keys are used for data transfer during the initial handshake in a connection, before the two parties have exchanged new randomly generated keys

with open("default-public.pem","rb") as f:
	DEFAULT_PUBLIC_KEY = rsa.PublicKey.load_pkcs1(f.read())

with open("default-private.pem","rb") as f:
	DEFAULT_PRIVATE_KEY = rsa.PrivateKey.load_pkcs1(f.read())

KEYSIZE = 1024
MAXMSGLENGTH = 117

print(rsa.decrypt(rsa.encrypt("test message".encode("utf-8"), DEFAULT_PUBLIC_KEY), DEFAULT_PRIVATE_KEY).decode("utf-8"))

class SecureSocket(object):
	def __repr__(self):
		return f"SecureSocket object    hostadress: {self._HOSTADDRESS}    hostname: {self._HOSTNAME}    port: {self._PORT}"
	
	def __init__(self, PORT, FORMAT, DISCONN_MSG, HANDSHAKE_MSG):
		self._online = False
		self._PORT = PORT
		self._HOSTNAME = socket.gethostname()
		self._HOSTADDRESS = socket.gethostbyname(self._HOSTNAME)
		self._ADDR = (self._HOSTADDRESS, self._PORT)
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

	def get_conns(self):
		if len(self._conns) == 0:
			raise Exception("There are no active connections")
		return self._conns



class Client(SecureSocket):
	def __init__(self, PORT, FORMAT, DISCONN_MSG, HANDSHAKE_MSG, TARGET_HOSTADDRESS):
		super().__init__(PORT, FORMAT, DISCONN_MSG, HANDSHAKE_MSG)
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
		self._conn.settimeout(None)
		self._addr = addr
		self._connected = False
		self._handshaked = False
		self._most_recent_message = ""

		self._send_queue = []

		

		self._public_key = DEFAULT_PUBLIC_KEY
		self._private_key = DEFAULT_PRIVATE_KEY
		self._recipient_public_key = DEFAULT_PUBLIC_KEY

		self._conn_thread = threading.Thread(target=self._handle_conn)
		self._conn_thread.start()

	def _handle_conn(self):
		print(f"[NEW CONNECTION] {self._addr} connected.")
		self._connected = True

		if type(self._sock) == Server:
			if self._start_handshake():
				self._handshaked = True
				print("Handshake completed successfully")
			else:
				self.start_disconn(True)


		while self._connected:
			### HANDLES RECEIVING NEW MESSAGES ###
			new_message_received = False
			msg = ""
			try:
				msg = self._receive(self._sock.get_format())
				new_message_received = True
			except:
				new_message_received = False # if we can't receive anymore then that means this connection has shutdown

			if new_message_received:
				if msg == "":
					break

				print(f"[{self._addr}] {msg}")

				if msg == self._sock.get_disconn_msg():
					self._handle_disconn()
				elif msg == self._sock.get_handshake_msg():
					if self._handle_handshake():
						self._handshaked = True
						print("Handshake completed successfully")
					else:
						self.start_disconn(True)
				else:
					self._most_recent_message = msg

				# no longer need to broadcast message to everyone from here, this is done on a higher level now
				# if type(self._sock) == Server:
				# 	for conn in self._sock.get_conns():
				# 		conn.send(self._most_recent_message)



			### HANDLES SENDING MESSAGES FROM THE SEND QUEUE ###

			try:
				self._send_items_from_queue()
			except Exception as e:
				print(e)


	def get_most_recent_message(self):
		return self._most_recent_message

	def _receive(self, decode_format):
		#print("we are getting a brand new message")
		#encrypted_msg_length_bytes = self._conn.recv(128)
		#print(f"received length of message {encrypted_msg_length_bytes}\n")
		#msg_length_bytes = rsa.decrypt(encrypted_msg_length_bytes, DEFAULT_PRIVATE_KEY)
		#print(f"decrypted length of message {msg_length_bytes}\n")
		#msg_length_text = msg_length_bytes.decode(self._sock.get_format())

		#if not msg_length_text:
		#	return ""
		#print(f"message is {msg_length_text} bits long")
		#msg_length = int(msg_length_text)

		number_of_chunks_bytes = rsa.decrypt(self._conn.recv(KEYSIZE//8), self._private_key)
		number_of_chunks = struct.unpack('>I', number_of_chunks_bytes)[0]
		#print(f"there are {number_of_chunks} chunks")

		message_bytes = b''

		for i in range(number_of_chunks):
			encrypted_chunk = self._conn.recv(KEYSIZE//8)
			#print(f"received message {encrypted_chunk}\n")
			chunk_bytes = rsa.decrypt(encrypted_chunk, self._private_key)
			message_bytes += chunk_bytes
		
		message = self._decode_from_bytes(message_bytes, decode_format)

		return message

	def add_message_to_send_queue(self, msg):
		"""This method allows other objects to add a new message to the queue of messages to be sent by this connection"""
		self._send_queue.append(msg)
		print(f"we added the message {msg} to the send queue")

	def _send_items_from_queue(self):
		"""Recursive function, sends next item from queue of messages to send, then calls itself. Continues until no more items to send."""
		if self._handshaked:
			if self._send_queue == []:
				return # the queue is empty, we've sent everything (base case)
			message_to_send = self._send_queue.pop(0)
			print(f"attempting to send message {message_to_send}")
			self._raw_send(message_to_send, "utf-8")
			self._send_items_from_queue()
		else:
			raise Exception("Cannot send as handshake incomplete")

	def _raw_send(self, msg, encode_format):
		if not self._connected:
			raise Exception("Cannot _raw_send as not connected")
		#print(f"_raw_sending message: {msg}")
		
		message = self._encode_to_bytes(msg, encode_format)

		number_of_chunks = (len(message) // MAXMSGLENGTH) + 1
		#print(f"There are {number_of_chunks} chunks")
		number_of_chunks_bytes = struct.pack('>I', number_of_chunks)
		encrypted_number_of_chunks = rsa.encrypt(number_of_chunks_bytes, self._recipient_public_key)

		self._conn.send(encrypted_number_of_chunks)

		#print("number of chunks sent!")
		
		i = 0
		for chunk in self._byte_chunks(message, MAXMSGLENGTH):
			#print(f"chunk {i}: {chunk}")
			i += 1

			encrypted_chunk = rsa.encrypt(chunk, self._recipient_public_key)
			
			self._conn.send(encrypted_chunk)


		#msg_length = len(encrypted_message)
		#_raw_send_length = str(msg_length).encode(self._sock.get_format())
		#_raw_send_length += b" " * (self._sock.get_header() - len(_raw_send_length))
		
		#encrypted__raw_send_length = rsa.encrypt(_raw_send_length, DEFAULT_PUBLIC_KEY)

		#self._conn._raw_send(encrypted__raw_send_length)
		#print(f"sent length {rsa.decrypt(encrypted__raw_send_length, DEFAULT_PRIVATE_KEY)}\n")
		#time.sleep(0.1)


		
	def _byte_chunks(self, data_bytes, chunk_length):
		return (data_bytes[0+i:chunk_length+i] for i in range(0, len(data_bytes), chunk_length))

	def _encode_to_bytes(self, data, encode_format):
		if encode_format == "pkcs1":
			return data.save_pkcs1("PEM")
		else:
			return data.encode(encode_format)

	def _decode_from_bytes(self, data_bytes, decode_format):
		if decode_format == "pkcs1":
			return rsa.PublicKey.load_pkcs1(data_bytes)
		else:
			return data_bytes.decode(decode_format)


	def _start_handshake(self):
		try:
			self._raw_send(self._sock.get_handshake_msg(), self._sock.get_format())
			print("handshake message sent!")
			
			response = self._receive(self._sock.get_format())
			print(response)
			
			if response != self._sock.get_handshake_msg():
				return False
			
			new_public_key, new_private_key = rsa.newkeys(KEYSIZE) # we create new keys in temporary vars because we need to exchange them before we start using them

			self._raw_send(new_public_key, "pkcs1")

			new_recipient_public_key = self._receive("pkcs1")

			self._public_key, self._private_key, self._recipient_public_key = new_public_key, new_private_key, new_recipient_public_key
			

			# redo handshake message again with new keys to make sure exchange was successful
			self._raw_send(self._sock.get_handshake_msg(), self._sock.get_format())
			print("handshake message sent!")
			
			response = self._receive(self._sock.get_format())
			print(response)
			
			if response != self._sock.get_handshake_msg():
				return False
			
			self._conn.settimeout(0)
			self._conn.setblocking(False)

			return True
		except Exception as e:
			print(f"Handshake failed: {e}")
			return False

	def _handle_handshake(self):
		try:
			self._raw_send(self._sock.get_handshake_msg(), self._sock.get_format())

			new_public_key, new_private_key = rsa.newkeys(KEYSIZE) # we create new keys in temporary vars because we need to exchange them before we start using them

			new_recipient_public_key = self._receive("pkcs1")
			self._raw_send(new_public_key, "pkcs1")

			self._public_key, self._private_key, self._recipient_public_key = new_public_key, new_private_key, new_recipient_public_key

			response = self._receive(self._sock.get_format())
			print(response)
			
			if response != self._sock.get_handshake_msg():
				return False
			self._raw_send(self._sock.get_handshake_msg(), self._sock.get_format())

		except Exception as e:
			print(f"Handshake failed: {e}")
			return False
		
		self._conn.settimeout(0)
		self._conn.setblocking(False)
		return True


	def start_disconn(self, removeconnfromsock:bool): # runs if we initiated the disconn
		print("we ended the connection")
		self._conn.settimeout(None)
		self._conn.setblocking(True)
		self._raw_send(self._sock.get_disconn_msg(), self._sock.get_format())
		self._disconn(removeconnfromsock)

	def _handle_disconn(self): # runs if the disconn was initiated by the other side
		print("they ended the connection")
		self._conn.settimeout(None)
		self._conn.setblocking(True)
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
			