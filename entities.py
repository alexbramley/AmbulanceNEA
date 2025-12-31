import vectors
import securesocket as ss
import threading
import time
import socket

class SuperManager:
    """Contains references to all managers that there should be one of per client or server"""

    @classmethod
    def setup(cls, is_server, server_or_connection_manager, entity_manager):
        """Sets the values for the managers that this holds references to"""
        cls._is_server = is_server
        if is_server:
            cls._server_manager = server_or_connection_manager
        else:
            cls._connection_manager = server_or_connection_manager
        cls._entity_manager = entity_manager

    @classmethod
    def get_is_server(cls):
        return cls._is_server

    @classmethod
    def get_entity_manager(cls):
        return cls._entity_manager
    
    @classmethod
    def get_server_manager(cls):
        return cls._server_manager


class ConnectionManager(object):
    """Handles a connection on a higher level than securesocket.SecureConnection"""
    def __init__(self):
        self._secure_connection = None
        self._newest_conn_msg = ""
        self.master_thread = None
        self._master_active = False
        self._newest_conn_command_data = []
        self._newest_conn_argument_data = []
        self._previous_idempotency_keys = []

    
    def _master(self):
        """The main loop of handling new messages from the connection"""
        print("Starting master ConnectionManager thread...")
        while self._master_active:
            time.sleep(0.1)
            if self._secure_connection != None:
                new_conn_msg = self._secure_connection.get_most_recent_message()
                if self._newest_conn_msg != new_conn_msg:
                    print("we got a brand new message")
                    self._newest_conn_msg = new_conn_msg
                    self._newest_conn_command_data, self._newest_conn_argument_data = self._handle_conn_msg(self._newest_conn_msg)
                    if SuperManager.get_is_server() == True:
                        SuperManager.get_server_manager().handle_connection_message(self, self._newest_conn_msg, self._newest_conn_command_data, self._newest_conn_argument_data)
                    
                    
    
    def start_master(self):
        """Starts the master loop"""
        self._master_active = True
        self.master_thread = threading.Thread(target=self._master)
        self.master_thread.start()

    def end_master(self):
        """Ends the master loop"""
        self._master_active = False
        if self.master_thread != None:
            self.master_thread.join()

    def _handle_conn_msg(self, message):
        """Gets triggered when we get a new message, decodes and executes the message command"""
        print(f"We got a message!! {message} is the message.")
        
        try:
            command_data, argument_data = self._parse_message(message, "<", ">", "|")
            print(f"received command: {command_data[0]}")
            print(f"receiced data {command_data}, {argument_data}")

            if command_data[-1] in self._previous_idempotency_keys:
                raise Exception("Repeat idempotency key")
            
            self._previous_idempotency_keys.append(command_data[-1])
            
            SuperManager.get_entity_manager().handle_command(command_data, argument_data)
            
            return (command_data, argument_data)
        except Exception as e:
            print(e)
            return [],[]


    def _parse_message(self, message, start_char, end_char, sep_char):
        """Decodes the message's command"""
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
        """Sends a message throught the SecureConnection object"""
        if self._secure_connection == None:
            return Exception("No secure_connection object to send with")
        try:
            print("adding message to send queue")
            self._secure_connection.add_message_to_send_queue(message)
        except Exception as e:
            print(f"Failed to send message, there was en exception:\n{e}")
    
    def disconnect(self):
        """Starts a disconnect on the SecureConnection object"""
        if self._secure_connection != None:
            self._secure_connection._sock.set_socket_status(False)


    def set_secure_connection(self, new_secure_connection):
        self._secure_connection = new_secure_connection

    def get_secure_connection(self):
        return self._secure_connection
    
    def get_newest_message(self):
        return self._newest_conn_msg

    def get_newest_message_data(self):
        return self._newest_conn_command_data, self._newest_conn_argument_data
    
class ServerManager(object):
    """Handles creating ConnectionManager objects and also broadcasting messages where relevant"""
    def __init__(self):
        self._server:ss.Server
        self._conn_managers = []
        self._master_active = False
        self.master_thread = None
        self._master_active = False
        self._previous_messages = [] # a list of all previous broadcasted messages

    def _master(self):
        """Main loop"""
        while self._master_active:
            time.sleep(0.1)
            self._refresh_conns()

    def handle_connection_message(self, connection_manager, new_message, new_command_data, new_argument_data):
        """Broadcasts messages to all clients when a message is received"""
        self._previous_messages.append(new_message)
        
        
        for recipient_conn_manager in self._conn_managers:
            recipient_conn_manager.send_socket_message(new_message)


    def _refresh_conns(self):
        """Makes sure self._conn_managers is up to date with the latest conns on the SecureSocket.Server"""
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
                for message in self._previous_messages:
                    new_conn_manager.send_socket_message(message)


    def set_server(self, new_server):
        self._server = new_server



    def start_master(self):
        """Starts the master loop"""
        self._master_active = True
        self.master_thread = threading.Thread(target=self._master)
        self.master_thread.start()

    def end_master(self):
        """Ends the master loop"""
        self._master_active = False
        if self.master_thread != None:
            self.master_thread.join()

    def shutdown_server(self):
        """Shuts down the server and all its connections"""
        self._server.set_socket_status(False)


class EntityManager(object):
    """Contains references to all entites, creates and does operations on them using commands that have been sent"""
    def __init__(self):
        self._entites = []

    def add_new_entity(self, entity_id, entity_type, position):
        """Creates new entity of given type"""
        if not self.check_entity_exists_by_id(entity_id):
            if entity_type == "entity":
                new_entity = Entity(entity_id, position)
            elif entity_type == "ambulance":
                new_entity = Ambulance(entity_id, position)
            else:
                raise Exception("Entity type invalid!")

            self._entites.append(new_entity)
        else:
            raise Exception("Cannot add entity as there is already an entity with that id.")

    def get_entity_by_id(self, entity_id:int):
        for entity in self._entites:
            if entity.get_id() == entity_id:
                return entity
        raise Exception(f"No entity found with id: {entity_id}")
    
    def check_entity_exists_by_id(self, entity_id):
        try:
            self.get_entity_by_id(entity_id)
            entity_already_exists = True
        except:
            entity_already_exists = False

        return entity_already_exists

    def remove_entity(self, entity_to_remove):
        """Removes specified entity"""
        for entity in self._entites:
            if entity == entity_to_remove:
                self._entites.remove(entity)
                return
        raise Exception(f"No such entity found")
    
    def get_entites(self):
        return self._entites
    
    def display_entites(self):
        for entity in self.get_entites():
            print(entity)
    
    def handle_command(self, command_data, argument_data):
        """Executed correct method based on incoming command"""
        try:
            if command_data[0] == "CREATE_ENTITY":
                self.add_new_entity(int(argument_data[0]), command_data[1], vectors.Vector2(float(argument_data[1]), float(argument_data[2]))) # command_data: [1]=entitytype argument_data: [0]=id, [1]=xpos, [2]=ypos
                print("we added a new entity")
            elif command_data[0] == "DISPLAY_ENTITIES":
                self.display_entites()
            elif command_data[0] == "UPDATE_ENTITY_POSITION":
                self.get_entity_by_id(int(argument_data[0])).update_position(float(argument_data[1]), float(argument_data[2])) # argument_data: [0]=id, [1]=xpos, [2]=ypos
            elif command_data[0] == "REMOVE_ENTITY":
                self.remove_entity(self.get_entity_by_id(int(argument_data[0]))) # argument_data: [0]=id
            else:
                print(f"That command keyword, {command_data[0]}, is invalid")
        except Exception as e:
            print(e)

class Entity(object):
    """Base class for all entity objects"""
    def __repr__(self):
        return f"entity object with id {self._id} at position {self.position}"
    
    def __init__(self, entity_id, position:vectors.Vector2):
        self._id = entity_id
        self.position = position

    def get_id(self):
        return self._id
    
    def update_position(self, new_position:vectors.Vector2):
        self.position = new_position

    def get_position(self):
        return self.position

class Ambulance(Entity):
    """Ambulance vehicle entity"""
    def __repr__(self):
        return "Ambulance "+super().__repr__()