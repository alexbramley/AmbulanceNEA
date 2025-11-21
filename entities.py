import vectors
import securesocket as ss
import threading
import time
import socket

class Entity(object):
    def __init__(self, position:vectors.Vector2, socket_instruction_set:dict):
        self.position = position
        self.secure_connection = None
        self.socket_instruction_set = socket_instruction_set
        self._most_recent_socket_message = ""

        self._master_thread = threading.Thread(target=self._master)
        self._master_thread.start()

    def _master(self):
        while True:
            if self.secure_connection != None:
                new_socket_message = self.secure_connection.get_most_recent_message()
                if new_socket_message != self._most_recent_socket_message:
                    
                    self._most_recent_socket_message = new_socket_message

                    self._handle_socket_message(self._most_recent_socket_message)

    def set_secure_connection(self, new_secure_connection:ss.SecureConnection):
        self.secure_connection = new_secure_connection

    def _handle_socket_message(self, message):
        """Gets triggered when a the secure_socket object receives a new connection"""
        if message[0] != "<":
            Exception("No command recognised!!")
            return
        
        command = ""
        reading_command = True
        for letter in message:
            if reading_command:
                if letter == ">":
                    reading_command = False
                    continue
                if letter == "<":
                    continue
                command += letter

        print(f"received command: {command}")


    def send_socket_message(self, message):
        if self.secure_connection == None:
            return Exception("No secure_connection object to send with")
        self.secure_connection.send(message)



client = ss.Client(42067, "utf-8", "!DISCONN", "!HANDSHAKE", socket.gethostbyname(socket.gethostname()))
client.set_socket_status(True)
print(client)

time.sleep(0.1)


my_entity = Entity(vectors.Vector2(0,0), {})
my_entity.set_secure_connection(client.get_conn())

msg = ""
while msg != "stop":
    if msg != "":
        my_entity.send_socket_message(msg)
    msg = input()

if my_entity.secure_connection != None:
    my_entity.secure_connection._sock.set_socket_status(False)