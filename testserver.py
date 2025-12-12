import entities as en
import securesocket as ss
import time

server = ss.Server(42067, "utf-8", "!DISCONN", "!HANDSHAKE")
server.set_socket_status(True)
print(server)

time.sleep(0.1)


my_server_manager = en.ServerManager()
my_server_manager.set_server(server)
my_server_manager.start_master()

input()

my_server_manager.end_master()
my_server_manager.shutdown_server()