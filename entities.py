import vectors
import securesocket

class Entity(object):
    def __init__(self, position:vectors.Vector2, socket_instruction_set:dict):
        self.position = position
        self.secure_connection = None
        self.socket_instruction_set = socket_instruction_set

    def set_secure_connection(self, new_secure_connection:securesocket.SecureConnection):
        self.secure_connection = new_secure_connection

    def handle_socket_message(self, message):
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
