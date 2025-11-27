import vectors
import securesocket as ss
import threading
import time
import socket



class EntityManager:
    
    _entities = []
    _secure_connection = None
    _newest_conn_msg = ""

    @classmethod
    def _master(cls):
        while True:
            if cls._secure_connection != None:
                new_conn_msg = cls._secure_connection.get_most_recent_message()
                if cls._newest_conn_msg != new_conn_msg:
                    cls._newest_conn_msg = new_conn_msg

    _master_thread = threading.Thread(target=_master)
    _master_thread.start()

    @classmethod
    def _handle_conn_msg(cls, message):
        """Gets triggered when we get a new message"""
        if message[0] != "<":
            print(Exception("No command recognised!!"))
            return
        
        command_data, argument_data = cls._parse_message(message, "<", ">", "|")

        print(f"received command: {command_data[0]}")

    @classmethod
    def _parse_message(cls, message, start_char, end_char, sep_char):
        letters = list(message)
        if letters.pop(0) != start_char:
            raise Exception("Message has invalid format")
        
        current_data = ""
        command_data = []
        argument_data = []

        reading_command_data = True

        for letter in letters:
            if letter == end_char:
                reading_command_data = False
            elif letter == sep_char:
                if reading_command_data:
                    command_data.append(current_data)
                else:
                    argument_data.append(current_data)
                current_data = ""
            else:
                current_data += letter
        
        return command_data, argument_data

    @classmethod
    def send_socket_message(cls, message):
        if cls._secure_connection == None:
            return Exception("No secure_connection object to send with")
        cls._secure_connection.send(message)

    @classmethod
    def disconnect(cls):
        if cls._secure_connection != None:
            cls._secure_connection._sock.set_socket_status(False)

    @classmethod
    def add_entity(cls, new_entity):
        cls._entities.append(new_entity)
    
    @classmethod
    def remove_entity(cls, entity_to_remove):
        cls._entities.remove(entity_to_remove)

    @classmethod
    def set_secure_connection(cls, new_secure_connection):
        cls._secure_connection = new_secure_connection

    





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
            print(Exception("No command recognised!!"))
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


#my_entity = Entity(vectors.Vector2(0,0), {})
EntityManager.set_secure_connection(client.get_conn())

msg = ""
while msg != "stop":
    if msg != "":
        EntityManager.send_socket_message(msg)
    msg = input()

EntityManager.disconnect()