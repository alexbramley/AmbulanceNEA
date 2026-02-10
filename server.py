import entities as en
import securesocket as ss
import time


server = ss.Server(42076, "utf-8", "!DISCONN", "!HANDSHAKE")
server.set_socket_status(True)
print(server)

time.sleep(0.1)

en.init_db()
my_server_manager = en.ServerManager()
my_entity_manager = en.EntityManager()
my_database_manager = en.DatabaseManager()

en.SuperManager.setup(True, my_server_manager, my_entity_manager, my_database_manager)


my_database_manager.start()
my_server_manager.set_server(server)
my_server_manager.start_master()
en.load_qualifications()
en.load_hospitals()
my_entity_manager.setup_severity_updater()

def handle_admin_input(admin_input:str):
    split_input = admin_input.split(" ")
    command = split_input[0]
    data = split_input[1:]
    try:
        if command == "db":
            if data[0] == "insert":
                if data[1] == "sample-data":
                    db_insert_sample_data()
                elif data[1] == "ambulance":
                    if "-h" in data[-1]:
                        print("db insert ambulance <AmbulanceCallSign>")
                    else:
                        my_database_manager.execute("INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)", (data[2],))

                elif data[1] == "crew":
                    if "-h" in data[-1]:
                        print("db insert crew <CrewID> <AmbulanceCallSign> <CrewPassword>")
                    else:
                        my_database_manager.execute("INSERT OR IGNORE INTO AmbulanceCrew(CrewID, AmbulanceCallSign, CrewHashedPassword) VALUES (?, ?, ?)", (data[2],data[3],en.bcrypt.hashpw(data[4].encode("utf-8"), en.bcrypt.gensalt())))
                        
                elif data[1] == "callhandler":
                    if "-h" in data[-1]:
                        print("db insert callhandler <CallHandlerID> <CallHandlerPassword>")
                    else:
                        my_database_manager.execute("INSERT OR IGNORE INTO CallHandler(CallHandlerID, CallHandlerHashedPassword) VALUES (?, ?)", (data[1],en.bcrypt.hashpw(data[2].encode("utf-8"), en.bcrypt.gensalt())))
                        
                elif data[1] == "qualification":
                    if "-h" in data[-1]:
                        print("db insert qualification <QualificationID> <QualificationName>")
                    else:
                        my_database_manager.execute("INSERT OR IGNORE INTO Qualification(QualificationID, QualificationName) VALUES (?, ?)", (data[1],data[2]))

                elif data[1] == "achievedqualification":
                    if "-h" in data[-1]:
                        print("db insert achievedqualification <CrewID> <QualificationID>")
                    else:
                        my_database_manager.execute("INSERT OR IGNORE INTO AchievedQualification(CrewID, QualificationID) VALUES(?, ?)", (data[1],data[2]))
    except Exception as e:
        print(f"Error\n{e}")



def db_insert_sample_data():
    # inserts some test data into the database
    my_database_manager.execute("INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)", ("AMB001",))
    my_database_manager.execute("INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)", ("AMB002",))
    my_database_manager.execute("INSERT OR IGNORE INTO AmbulanceCrew(CrewID, AmbulanceCallSign, CrewHashedPassword) VALUES (?, ?, ?)", ("CRW001","AMB001",en.bcrypt.hashpw("exapmlepassword".encode("utf-8"), en.bcrypt.gensalt())))
    my_database_manager.execute("INSERT OR IGNORE INTO AmbulanceCrew(CrewID, AmbulanceCallSign, CrewHashedPassword) VALUES (?, ?, ?)", ("CRW002","AMB002",en.bcrypt.hashpw("exapmlepassword".encode("utf-8"), en.bcrypt.gensalt())))
    my_database_manager.execute("INSERT OR IGNORE INTO CallHandler(CallHandlerID, CallHandlerHashedPassword) VALUES (?, ?)", ("CLH001",en.bcrypt.hashpw("exapmlepassword".encode("utf-8"), en.bcrypt.gensalt())))
    my_database_manager.execute("INSERT OR IGNORE INTO CallHandler(CallHandlerID, CallHandlerHashedPassword) VALUES (?, ?)", ("CLH002",en.bcrypt.hashpw("exapmlepassword".encode("utf-8"), en.bcrypt.gensalt())))
    my_database_manager.execute("INSERT OR IGNORE INTO Qualification(QualificationID, QualificationName) VALUES (?, ?)", ("QUL001","example_qual1"))
    my_database_manager.execute("INSERT OR IGNORE INTO Qualification(QualificationID, QualificationName) VALUES (?, ?)", ("QUL002","example_qual2"))
    my_database_manager.execute("INSERT OR IGNORE INTO AchievedQualification(CrewID, QualificationID) VALUES (?, ?)", ("CRW001", "QUL001"))
    my_database_manager.execute("INSERT OR IGNORE INTO Hospital(HospitalID, HospitalName, HospitalLat, HospitalLon) VALUES (?, ?, ?, ?)", ("HSP001", "Example Hospital London", 51.52, -0.09))
    my_database_manager.execute("INSERT OR IGNORE INTO Hospital(HospitalID, HospitalName, HospitalLat, HospitalLon) VALUES (?, ?, ?, ?)", ("HSP002", "Example Hospital Birmingham", 52.47, -1.89))
    my_database_manager.execute("INSERT OR IGNORE INTO MapLogin(MapID, MapHashedPassword) VALUES (?, ?)", ("MAP001", en.bcrypt.hashpw("exapmlepassword".encode("utf-8"), en.bcrypt.gensalt())))



admin_input = ""

while admin_input != "close-server":
    admin_input = input("Enter admin command:\n")
    handle_admin_input(admin_input)




my_database_manager.stop()
my_server_manager.end_master()
my_server_manager.shutdown_server()