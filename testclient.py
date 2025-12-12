import entities as en
import socket
import securesocket as ss
import time

client = ss.Client(42067, "utf-8", "!DISCONN", "!HANDSHAKE", socket.gethostbyname(socket.gethostname()))
client.set_socket_status(True)
print(client)

time.sleep(0.1)


#my_entity = Entity(vectors.Vector2(0,0))
my_conn_manager = en.ConnectionManager()
my_conn_manager.set_secure_connection(client.get_conn())
my_conn_manager.start_master()

msg = ""
while msg != "stop":
    if msg != "":
        my_conn_manager.send_socket_message(msg)
    msg = input()

my_conn_manager.disconnect()
my_conn_manager.end_master()