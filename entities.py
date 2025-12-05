import vectors
import securesocket as ss
import threading
import time
import socket



class EntityManager:
    
    _entities = []
    _secure_connection = None
    _newest_conn_msg = ""
    master_thread = None
    _master_active = False

    @classmethod
    def _master(cls):
        print("Starting master EntityManager thread...")
        while cls._master_active:
            if cls._secure_connection != None:
                new_conn_msg = cls._secure_connection.get_most_recent_message()
                if cls._newest_conn_msg != new_conn_msg:
                    print("we got a brand new message")
                    cls._newest_conn_msg = new_conn_msg
                    cls._handle_conn_msg(cls._newest_conn_msg)

    @staticmethod
    def start_master():
        EntityManager._master_active = True
        EntityManager.master_thread = threading.Thread(target=EntityManager._master)
        EntityManager.master_thread.start()

    @staticmethod
    def end_master():
        EntityManager._master_active = False
        if EntityManager.master_thread != None:
            EntityManager.master_thread.join()

    @classmethod
    def _handle_conn_msg(cls, message):
        """Gets triggered when we get a new message"""
        print(f"We got a message!! {message} is the message.")
        
        try:
            command_data, argument_data = cls._parse_message(message, "<", ">", "|")
            print(f"received command: {command_data[0]}")
            print(f"receiced data {command_data}, {argument_data}")
        except Exception as e:
            print(e)

        

    @classmethod
    def _parse_message(cls, message, start_char, end_char, sep_char):
        print(f"Parsing {message}")
        letters = list(message)
        if letters.pop(0) != start_char:
            raise Exception("Message has invalid format")
        
        current_data = ""
        command_data = []
        argument_data = []

        reading_command_data = True

        for letter in letters:
            if letter == sep_char or letter == end_char:
                if reading_command_data:
                    command_data.append(current_data)
                else:
                    argument_data.append(current_data)
                current_data = ""
                if letter == end_char:
                    reading_command_data = False
            else:
                current_data += letter
        
        if current_data != "":
            argument_data.append(current_data)
        
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
    def __init__(self, position:vectors.Vector2):
        self.position = position



client = ss.Client(42067, "utf-8", "!DISCONN", "!HANDSHAKE", socket.gethostbyname(socket.gethostname()))
client.set_socket_status(True)
print(client)

time.sleep(0.1)


#my_entity = Entity(vectors.Vector2(0,0))
EntityManager.set_secure_connection(client.get_conn())
EntityManager.start_master()

msg = ""
while msg != "stop":
    if msg != "":
        EntityManager.send_socket_message(msg)
    msg = input()

EntityManager.disconnect()
EntityManager.end_master()