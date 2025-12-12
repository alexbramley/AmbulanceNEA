import vectors
import securesocket as ss
import threading
import time
import socket



class ConnectionManager(object):
    def __init__(self):
        self._secure_connection = None
        self._newest_conn_msg = ""
        self.master_thread = None
        self._master_active = False
        self._newest_conn_command_data = []
        self._newest_conn_argument_data = []
        self.new_message_flag = False

    
    def _master(self):
        print("Starting master ConnectionManager thread...")
        while self._master_active:
            if self._secure_connection != None:
                new_conn_msg = self._secure_connection.get_most_recent_message()
                if self._newest_conn_msg != new_conn_msg:
                    print("we got a brand new message")
                    self._newest_conn_msg = new_conn_msg
                    self._newest_conn_command_data, self._newest_conn_argument_data = self._handle_conn_msg(self._newest_conn_msg)
                    self.new_message_flag = True

    
    def start_master(self):
        self._master_active = True
        self.master_thread = threading.Thread(target=self._master)
        self.master_thread.start()

    def end_master(self):
        self._master_active = False
        if self.master_thread != None:
            self.master_thread.join()

    def _handle_conn_msg(self, message):
        """Gets triggered when we get a new message"""
        print(f"We got a message!! {message} is the message.")
        
        try:
            command_data, argument_data = self._parse_message(message, "<", ">", "|")
            print(f"received command: {command_data[0]}")
            print(f"receiced data {command_data}, {argument_data}")
            return (command_data, argument_data)
        except Exception as e:
            print("The message wasn't in a valid format")
            return [],[]


    def _parse_message(self, message, start_char, end_char, sep_char):
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


    def send_socket_message(self, message):
        if self._secure_connection == None:
            return Exception("No secure_connection object to send with")
        self._secure_connection.send(message)

    
    def disconnect(self):
        if self._secure_connection != None:
            self._secure_connection._sock.set_socket_status(False)


    def set_secure_connection(self, new_secure_connection):
        self._secure_connection = new_secure_connection

    def get_secure_connection(self):
        return self._secure_connection
    
    def get_newest_message(self):
        self.new_message_flag = False
        return self._newest_conn_msg


    def get_newest_message_data(self):
        self.new_message_flag = False
        return self._newest_conn_command_data, self._newest_conn_argument_data
    
class ServerManager(object):
    def __init__(self):
        self._server:ss.Server
        self._conn_managers = []
        self._master_active = False
        self.master_thread = None
        self._master_active = False

    def _master(self):
        while self._master_active:
            self._refresh_conns()
            for conn_manager in self._conn_managers:
                if conn_manager.new_message_flag == True:
                    message_to_broadcast = conn_manager.get_newest_message()
                    for recipient_conn_manager in self._conn_managers:
                        recipient_conn_manager.send_socket_message(message_to_broadcast)

    
    def _refresh_conns(self):
        """makes sure self._conn_managers is up to date with the latest conns on the server"""
        try:
            server_conns = self._server.get_conns()
        except:
            return

        # checks for outdated conns and removes them
        for conn_manager in self._conn_managers:
            conn_found = False
            for conn in server_conns:
                if conn_manager.get_secure_connection() == conn:
                    conn_found = True
            
            if not conn_found:
                print("Removing an old connection that no longer exists on the server...")
                conn_manager.end_master()
                self._conn_managers.remove(conn_manager)


        # checks for new conns and adds them
        for conn in server_conns:
            conn_found = False
            for conn_manager in self._conn_managers:
                if conn_manager.get_secure_connection() == conn:
                    conn_found = True
            
            if not conn_found:
                print("The server got a new connection!!")
                new_conn_manager = ConnectionManager()
                new_conn_manager.set_secure_connection(conn)
                new_conn_manager.start_master()
                self._conn_managers.append(new_conn_manager)


    def set_server(self, new_server):
        self._server = new_server



    def start_master(self):
        self._master_active = True
        self.master_thread = threading.Thread(target=self._master)
        self.master_thread.start()

    def end_master(self):
        self._master_active = False
        if self.master_thread != None:
            self.master_thread.join()

    def shutdown_server(self):
        self._server.set_socket_status(False)


class Entity(object):
    def __init__(self, position:vectors.Vector2):
        self.position = position

