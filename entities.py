import vectors
import securesocket as ss
import threading
import time
import socket
import datetime
import sqlite3
import queue

WRONG_QUALIFICATION_PENALTY = 2000
DBPATH = "ambulancedata.db"

def init_db():
    con = sqlite3.connect(DBPATH, timeout=10)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    con.close()

class DatabaseManager:
    def __init__(self):
        self._job_queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = False
        self._con = None
        self._last_result = None
        self._lock = threading.Lock()  # protects _last_result

    

    def start(self):
        """Start the DB thread"""
        self._running = True
        self._thread.start()

    def stop(self):
        """Stop the DB thread"""
        self._running = False
        self._job_queue.put(None)  # sentinel
        time.sleep(0.1)
        self._thread.join()
        

    def execute(self, sql: str, params: tuple = ()):
        """
        Submit an SQL command to run on the DB thread.
        For SELECTs, fetchone() will be stored in _last_result.
        For INSERT/UPDATE/DELETE, commits automatically.
        """
        done_queue = queue.Queue(maxsize=1)
        self._job_queue.put((sql, params, done_queue))
        # wait for job to complete
        done_queue.get()

    def get_last_result(self):
        """Return the last fetchone() result"""
        with self._lock:
            return self._last_result

    

    def _run(self):
        # single connection for this thread
        self._con = sqlite3.connect(DBPATH, timeout=5)
        self._con.execute("PRAGMA journal_mode=WAL;")
        self._con.execute("PRAGMA foreign_keys=ON;")
        self._create_tables()

        while self._running:
            job = self._job_queue.get()
            if job is None:
                if self._con:
                    self._con.close()
                break

            sql, params, done_queue = job
            try:
                cur = self._con.cursor()
                print(f"executing {sql} with params {params}")
                cur.execute(sql, params)
                print("executed!!")

                if sql.strip().upper().startswith("SELECT"):
                    with self._lock:
                        self._last_result = cur.fetchone()
                else:
                    self._con.commit()

            except Exception as e:
                print("DB Error:", e)
                with self._lock:
                    self._last_result = None

            finally:
                done_queue.put(True)

    

    def _create_tables(self):
        if self._con:
            cur = self._con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Ambulance(
                    AmbulanceCallSign TEXT PRIMARY KEY
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS AmbulanceCrew(
                    CrewID TEXT PRIMARY KEY,
                    AmbulanceCallSign TEXT,
                    CrewHashedPassword TEXT,
                    FOREIGN KEY (AmbulanceCallSign)
                        REFERENCES Ambulance(AmbulanceCallSign)
                )
            """)
            self._con.commit()
        else:
            raise Exception("databasemanager._con is set as None")


class SuperManager:
    """Contains references to all managers that there should be one of per client or server"""

    @classmethod
    def setup(cls, is_server, server_or_connection_manager, entity_manager, database_manager):
        """Sets the values for the managers that this holds references to"""
        cls._is_server = is_server
        if is_server:
            cls._server_manager = server_or_connection_manager
        else:
            cls._connection_manager = server_or_connection_manager
        cls._entity_manager = entity_manager
        cls._database_manager = database_manager

    @classmethod
    def get_is_server(cls):
        return cls._is_server

    @classmethod
    def get_entity_manager(cls):
        return cls._entity_manager

    @classmethod
    def get_server_manager(cls):
        return cls._server_manager

    @classmethod
    def get_database_manager(cls) -> DatabaseManager:
        return cls._database_manager

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
        self.master_thread = threading.Thread(target=self._master, daemon=True)
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
        self._previous_combination_idempotency_key = 0
        self._previous_combination = []

    def _master(self):
        """Main loop"""
        while self._master_active:
            time.sleep(0.1)
            self._refresh_conns()
            self._recalculate_ambulance_combinations()

    def _recalculate_ambulance_combinations(self): # right now there's a problem because unused ambulances' destinations need to be set back to themselves
        combination = SuperManager.get_entity_manager().calculate_best_combination()
        if combination == self._previous_combination:
            return
        print("we got a new combination, which is")
        print(combination)
        for matchup in combination:
            ambulance = matchup[0]
            destination = matchup[1]
            ambulance.set_destination(destination)
            self.broadcast(f"<SET_DESTINATION|newdestination{self._previous_combination_idempotency_key}>{ambulance.get_id()}|{destination.get_id()}")
            if ambulance == destination: # the ambulance has been routed to itself, meaning it's no longer needed
                print("trying to set status available")
                ambulance.set_status(vehicle_states["available"])
                self.broadcast(f"<SET_STATUS|newstatus{self._previous_combination_idempotency_key}>{ambulance.get_id()}|available")
            else:
                print("trying to set status en route")
                ambulance.set_status(vehicle_states["en_route"])
                self.broadcast(f"<SET_STATUS|newstatus{self._previous_combination_idempotency_key}>{ambulance.get_id()}|en_route")

            self._previous_combination_idempotency_key += 1
        self._previous_combination = combination


    def handle_connection_message(self, connection_manager, new_message, new_command_data, new_argument_data):
        """Broadcasts messages to all clients when a message is received"""

        self.broadcast(new_message)
        # for recipient_conn_manager in self._conn_managers:
        #     recipient_conn_manager.send_socket_message(new_message)

    def broadcast(self, message):
        self._previous_messages.append(message)
        for recipient_conn_manager in self._conn_managers:
            recipient_conn_manager.send_socket_message(message)



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
        self.master_thread = threading.Thread(target=self._master, daemon=True)
        self.master_thread.start()

    def end_master(self):
        """Ends the master loop"""
        self._master_active = False
        if self.master_thread != None:
            self.master_thread.join()

    def shutdown_server(self):
        """Shuts down the server and all its connections"""
        self._server.set_socket_status(False)

class AmbulanceCrew(object):
    def __init__(self, crew_id):
        self._crew_id = crew_id
        self._ambulance = None
        self._qualifications = []
        self._hashed_password = ""

    def add_qualification(self, new_qualification):
        self._qualifications.append(new_qualification)

    def get_qualifications(self):
        return self._qualifications

    def get_id(self):
        return self._crew_id

    def set_ambulance(self, new_ambulance):
        self._ambulance = new_ambulance

    def get_ambulance(self):
        return self._ambulance

class Qualification(object):
    def __repr__(self):
        return "Qualifcation "+self._name
    def __init__(self, qualification_id, qualification_name):
        self._id = qualification_id
        self._name = qualification_name

    def get_name(self):
        return self._name

    def get_id(self):
        return self._id

class VehicleState(object):
    def __init__(self, name):
        self._name = name
        self._next_states = []

    def get_name(self):
        return self._name

    def set_next_states(self, new_states):
        self._next_states = new_states

    def get_next_states(self):
        return self._next_states


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
        try:
            qualification_string = " with qualifications "+str(SuperManager.get_entity_manager().get_crew_by_ambulance(self).get_qualifications())
        except:
            qualification_string = " with no qualifications"
        return "Ambulance "+super().__repr__()+" going to "+str(type(self._destination))+qualification_string

    def __init__(self, entity_id, position: vectors.Vector2, status, callsign):
        super().__init__(entity_id, position)
        self._status = status
        self._destination = self
        self._speed = 35
        self._crew = None
        self._callsign = callsign

    def set_callsign(self, new_call_sign):
        self._callsign = new_call_sign

    def get_callsign(self):
        return self._callsign

    def set_crew(self, new_crew):
        self._crew = new_crew

    def get_crew(self):
        return self._crew

    def set_status(self, new_status):
        print(f"setting status {new_status.get_name()}")
        self._status = new_status

    def get_speed(self):
        return self._speed

    def get_status(self):
        return self._status

    def set_destination(self, new_destination:Entity):
        self._destination = new_destination
        print("setting destination to",new_destination)

    def get_destination(self):
        return self._destination

class Emergency(Entity):
    """Emergency entity"""
    def __repr__(self):
        return "Emergency "+super().__repr__()

    def __init__(self, entity_id, position: vectors.Vector2, severity:int):
        super().__init__(entity_id, position)
        self._severity = severity
        self._qualifications = []
        self._response_time = None # the time when the emergency received a response
        self._start_time = None
        self._end_time = None
        self._ambulance_required = True



    def set_response_time(self, new_response_time):
        self._response_time = new_response_time

    def set_start_time(self, new_start_time):
        self._start_time = new_start_time

    def set_end_time(self, new_end_time):
        self._end_time = new_end_time

    def get_response_time(self):
        return self._response_time

    def get_start_time(self):
        return self._start_time

    def get_end_time(self):
        return self._end_time

    def add_qualification(self, new_qualification):
        print("adding a new qualification "+str(new_qualification.get_name()))
        self._qualifications.append(new_qualification)

    def get_qualifications(self):
        return self._qualifications

    def set_severity(self, new_severity):
        self._severity = new_severity

    def get_severity(self):
        return self._severity



class EntityManager(object):
    """Contains references to all entites, creates and does operations on them using commands that have been sent"""
    def __init__(self):
        self._entites = []
        self._crews = []

    def add_new_entity(self, **kwargs):
        """Creates new entity of given type"""
        if not self.check_entity_exists_by_id(kwargs["entity_id"]):
            if kwargs["entity_type"] == "entity":
                new_entity = Entity(kwargs["entity_id"], kwargs["position"])
            elif kwargs["entity_type"] == "ambulance":


                # when we get the create ambulance command, we should check if an ambulance with that id exists in the db.
                # if so, we then create the ambulance
                # if no ambulance exists with that id, we should make a new ambulance with that id # TODO THIS MUST BE AUTHED BY AN ADMIN SOMEHOW

                if SuperManager.get_is_server():
                    try:
                        dbm = SuperManager.get_database_manager()

                        dbm.execute("SELECT 1 FROM Ambulance WHERE AmbulanceCallSign = ? LIMIT 1",
                                           (kwargs["callsign"],))
                        ambulance_exists = dbm.get_last_result() is not None

                        if ambulance_exists:
                            print("That ambulance exists in the database")
                        else:
                            dbm.execute(
                                "INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)",
                                (kwargs["callsign"],)
                            )
                            print("we made a new ambulance")

                    except Exception as e:
                        print(e)




                new_entity = Ambulance(kwargs["entity_id"], kwargs["position"], vehicle_states[kwargs["status"]], kwargs["callsign"])
            elif kwargs["entity_type"] == "emergency":
                new_entity = Emergency(kwargs["entity_id"], kwargs["position"], kwargs["severity"])
                new_entity.set_start_time(datetime.datetime.now())
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

    def get_ambulances(self):
        ambulances = []
        for entity in self._entites:
            if type(entity) == Ambulance:
                ambulances.append(entity)
        return ambulances

    def get_ambulances_by_state(self, state:VehicleState):
        ambulances = []
        for entity in self._entites:
            if type(entity) == Ambulance:
                if entity.get_status() == state:
                    ambulances.append(entity)
        return ambulances


    def get_emergencies(self):
        emergencies = []
        for entity in self._entites:
            if type(entity) == Emergency:
                emergencies.append(entity)
        return emergencies

    def calculate_best_combination(self):
        import math

        available_ambulances = self.get_ambulances_by_state(vehicle_states["available"]) + self.get_ambulances_by_state(vehicle_states["en_route"])
        emergencies = self.get_emergencies()

        if not available_ambulances:
            return []

        if not emergencies:
            assignments = []
            for ambulance in available_ambulances:
                assignments.append((ambulance, ambulance))
            return assignments

        # haversine distance
        def haversine_distance(pos1, pos2):
            r = 6371000
            lat1 = math.radians(pos1.x)
            lon1 = math.radians(pos1.y)
            lat2 = math.radians(pos2.x)
            lon2 = math.radians(pos2.y)

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            )
            return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # build cost matrix (ambulances x emergencies)
        cost_matrix = []
        for ambulance in available_ambulances:
            row = []
            for emergency in emergencies:
                try:
                    ambulance_quals = set(ambulance.get_crew().get_qualifications())
                except:
                    ambulance_quals = set()
                required_quals = set(emergency.get_qualifications())

                missing_count = len(required_quals - ambulance_quals)
                qualification_penalty = missing_count * WRONG_QUALIFICATION_PENALTY

                distance = haversine_distance(
                    ambulance.get_position(),
                    emergency.get_position()
                )
                travel_time = distance / ambulance.get_speed()

                severity = emergency.get_severity()
                severity_multiplier = 1.0 / (1.0 + severity)

                weighted_cost = (travel_time + qualification_penalty) * severity_multiplier

                row.append(weighted_cost)

            cost_matrix.append(row)


        def hungarian(matrix):
            n = len(matrix)
            m = len(matrix[0])
            size = max(n, m)

            # pad to square matrix
            padded = [row + [0] * (size - m) for row in matrix]
            for _ in range(size - n):
                padded.append([0] * size)

            u = [0.0] * (size + 1)
            v = [0.0] * (size + 1)
            p = [0] * (size + 1)
            way = [0] * (size + 1)

            for i in range(1, size + 1):
                p[0] = i
                j0 = 0
                minv = [float("inf")] * (size + 1)
                used = [False] * (size + 1)

                while True:
                    used[j0] = True
                    i0 = p[j0]
                    delta = float("inf")
                    j1 = 0

                    for j in range(1, size + 1):
                        if not used[j]:
                            cur = padded[i0 - 1][j - 1] - u[i0] - v[j]
                            if cur < minv[j]:
                                minv[j] = cur
                                way[j] = j0
                            if minv[j] < delta:
                                delta = minv[j]
                                j1 = j

                    for j in range(size + 1):
                        if used[j]:
                            u[p[j]] += delta
                            v[j] -= delta
                        else:
                            minv[j] -= delta

                    j0 = j1
                    if p[j0] == 0:
                        break

                while True:
                    j1 = way[j0]
                    p[j0] = p[j1]
                    j0 = j1
                    if j0 == 0:
                        break

            result = []
            for j in range(1, size + 1):
                if p[j] <= n and j <= m:
                    result.append((p[j] - 1, j - 1))

            return result

        hungarian_matches = hungarian(cost_matrix)

        assignments = []

        assigned_ambulance_indices = set()

        # assigned ambulances → emergencies
        for amb_idx, em_idx in hungarian_matches:
            ambulance = available_ambulances[amb_idx]
            emergency = emergencies[em_idx]

            assignments.append((ambulance, emergency))
            assigned_ambulance_indices.add(amb_idx)

        # unassigned ambulances → (ambulance, ambulance)
        for idx, ambulance in enumerate(available_ambulances):
            if idx not in assigned_ambulance_indices:
                assignments.append((ambulance, ambulance))

        return assignments

    def create_crew(self, crew_id):
        if SuperManager.get_is_server():
            dbm = SuperManager.get_database_manager()
            try:
                dbm.execute(
                    "SELECT 1 FROM AmbulanceCrew WHERE CrewID = ? LIMIT 1",
                    ("CRW" + str(crew_id).rjust(3, "0"),)
                )

                crew_exists = dbm.get_last_result() is not None

                if crew_exists:
                    dbm.execute(
                        "SELECT CrewHashedPassword FROM AmbulanceCrew WHERE CrewID = ? LIMIT 1",
                        ("CRW" + str(crew_id).rjust(3, "0"),)
                    )
                    password_data = dbm.get_last_result()
                    if password_data != None:
                        password = password_data[0]
                        print(password)
                else:
                    dbm.execute(
                        "INSERT OR IGNORE INTO AmbulanceCrew(CrewID, AmbulanceCallSign, CrewHashedPassword) VALUES (?, ?, ?)",
                        ("CRW" + str(crew_id).rjust(3, "0"),"AMB001","exapmlepassword",)
                    )
                    
                    print("we made a record")
            except Exception as e:
                print("there was an error in the crew db operation")
                print(type(e),e)

        self._crews.append(AmbulanceCrew(crew_id))
        # when we get the create crew command, we should check if a crew with that id exists in the db.
        # if so, we should check if the password given matches that crew's password
            # if yes, then create the crew
            # if no, then we should refuse to create the crew
        # if no crew exists with that id, we should make a new crew with that id and password # TODO THIS MUST BE AUTHED BY AN ADMIN SOMEHOW
        

    def get_crew_by_id(self, crew_id:int):
        for crew in self._crews:
            if crew.get_id() == crew_id:
                return crew

        raise Exception("No crew exists with that id")

    def get_crew_by_ambulance(self, ambulance):
        for crew in self._crews:
            if crew.get_ambulance() == ambulance:
                return crew

        raise Exception("No crew exists with that ambulance")

    def display_entites(self):
        for entity in self.get_entites():
            print(entity)

    def assign_crew(self, ambulance:Ambulance, crew:AmbulanceCrew):
        ambulance.set_crew(crew)
        crew.set_ambulance(ambulance)

    def handle_command(self, command_data, argument_data):
        """Executed correct method based on incoming command"""
        try:
            if command_data[0] == "CREATE_ENTITY":
                if command_data[1] == "ambulance":
                    self.add_new_entity(entity_id=int(argument_data[0]), entity_type=command_data[1], position=vectors.Vector2(float(argument_data[1]), float(argument_data[2])), status=argument_data[3], callsign=argument_data[4]) # command_data: [1]=entitytype argument_data: [0]=id, [1]=xpos, [2]=ypos
                elif command_data[1] == "emergency":
                    self.add_new_entity(entity_id=int(argument_data[0]), entity_type=command_data[1], position=vectors.Vector2(float(argument_data[1]), float(argument_data[2])), severity=int(argument_data[3])) # argument_data[3]=severity
                else:
                    self.add_new_entity(entity_id=int(argument_data[0]), entity_type=command_data[1], position=vectors.Vector2(float(argument_data[1]), float(argument_data[2])))
                print("we added a new entity")
            elif command_data[0] == "DISPLAY_ENTITIES":
                self.display_entites()
            elif command_data[0] == "UPDATE_ENTITY_POSITION":
                self.get_entity_by_id(int(argument_data[0])).update_position(vectors.Vector2(float(argument_data[1]), float(argument_data[2]))) # argument_data: [0]=id, [1]=xpos, [2]=ypos
            elif command_data[0] == "REMOVE_ENTITY":
                self.remove_entity(self.get_entity_by_id(int(argument_data[0]))) # argument_data: [0]=id
            elif command_data[0] == "SET_DESTINATION":
                self.get_entity_by_id(int(argument_data[0])).set_destination(self.get_entity_by_id(int(argument_data[1])))
            elif command_data[0] == "SET_STATUS":
                self.get_entity_by_id(int(argument_data[0])).set_status(vehicle_states[argument_data[1]]) # argument_data: [0]=id, [1]=status_name
            elif command_data[0] == "CREATE_CREW":
                self.create_crew(int(argument_data[0])) # argument_data: [0] = crew_id
            elif command_data[0] == "ASSIGN_CREW":
                self.assign_crew(self.get_entity_by_id(int(argument_data[0])), self.get_crew_by_id(int(argument_data[1]))) # argument_data: [0]=ambulance_entity_id, [1]=crew_id
            elif command_data[0] == "ADD_QUALIFICATION": # can be done on emergencies or crews, specify in the command
                if command_data[1] == "crew":
                    self.get_crew_by_id(int(argument_data[0])).add_qualification(qualifications[int(argument_data[1])]) # argument_data: [0]=crew_id, [1]=qualification_id
                elif command_data[1] == "emergency":
                    print("attempting to add new qualification")
                    self.get_entity_by_id(int(argument_data[0])).add_qualification(qualifications[int(argument_data[1])]) # argument_data: [0]=entity_id, [1]=qualification_id
                else:
                    raise Exception("You can only add a qualification to an emergency (as a requirement) or to a crew (as an achieved qualification).")
            else:
                print(f"That command keyword, {command_data[0]}, is invalid")
        except Exception as e:
            print(e)





qualifications = {0:Qualification(0,"Example Qualification 1"),
                  1:Qualification(1,"Exapmle Qualification 2")}

vehicle_states = {"available":VehicleState("Available"),
                  "en_route":VehicleState("En route"),
                  "on_scene":VehicleState("On scene"),
                  "returning_to_hospital":VehicleState("Returning to hospital"),
                  "unloading":VehicleState("Unloading patient"),
                  "returning_to_base":VehicleState("Returning to base"),
                  "handover":VehicleState("Shift handover")}

vehicle_states["available"].set_next_states([vehicle_states["en_route"], vehicle_states["handover"]])
vehicle_states["en_route"].set_next_states([vehicle_states["en_route"], vehicle_states["on_scene"]])
vehicle_states["on_scene"].set_next_states([vehicle_states["returning_to_base"], vehicle_states["returning_to_hospital"]])
vehicle_states["returning_to_hospital"].set_next_states([vehicle_states["unloading"]])
vehicle_states["unloading"].set_next_states(["returning_to_base"])
vehicle_states["returning_to_base"].set_next_states([vehicle_states["available"]])
vehicle_states["handover"].set_next_states([vehicle_states["available"]])