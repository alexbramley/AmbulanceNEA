import entities as en
import securesocket as ss
import time
import sqlite3




server = ss.Server(42072, "utf-8", "!DISCONN", "!HANDSHAKE")
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

input()

my_database_manager.execute("INSERT OR IGNORE INTO Ambulance(AmbulanceCallSign) VALUES (?)", ("AMB001",))

input()

my_database_manager.stop()
my_server_manager.end_master()
my_server_manager.shutdown_server()