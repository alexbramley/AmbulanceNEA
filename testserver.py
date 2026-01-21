import entities as en
import securesocket as ss
import time
import sqlite3




server = ss.Server(42078, "utf-8", "!DISCONN", "!HANDSHAKE")
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
input()

my_database_manager.execute("INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)", ("AMB001",))
my_database_manager.execute("INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)", ("AMB002",))
my_database_manager.execute("INSERT OR IGNORE INTO AmbulanceCrew(CrewID, AmbulanceCallSign, CrewHashedPassword) VALUES (?, ?, ?)", ("CRW001","AMB001","exapmlepassword"))
my_database_manager.execute("INSERT OR IGNORE INTO AmbulanceCrew(CrewID, AmbulanceCallSign, CrewHashedPassword) VALUES (?, ?, ?)", ("CRW002","AMB002","exapmlepassword"))
my_database_manager.execute("INSERT OR IGNORE INTO CallHandler(CallHandlerID, CallHandlerHashedPassword) VALUES (?, ?)", ("CLH001","exapmlepassword"))
my_database_manager.execute("INSERT OR IGNORE INTO CallHandler(CallHandlerID, CallHandlerHashedPassword) VALUES (?, ?)", ("CLH002","exapmlepassword"))
my_database_manager.execute("INSERT OR IGNORE INTO Qualification(QualificationID, QualificationName) VALUES (?, ?)", ("QUL001","example_qual1"))
my_database_manager.execute("INSERT OR IGNORE INTO Qualification(QualificationID, QualificationName) VALUES (?, ?)", ("QUL002","example_qual2"))
my_database_manager.execute("INSERT OR IGNORE INTO AchievedQualification(CrewID, QualificationID) VALUES(?, ?)", ("CRW001", "QUL001"))


input()

my_database_manager.stop()
my_server_manager.end_master()
my_server_manager.shutdown_server()