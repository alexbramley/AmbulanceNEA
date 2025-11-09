import securesocket as ss
import socket
import time

client = ss.Client(42069, 64, "utf-8", "!DISCONN", "!HANDSHAK", socket.gethostbyname(socket.gethostname()))
client.set_socket_status(True)
print(client)

time.sleep(0.1)

msg = ""
while msg != "stop":
    client.get_conn().send(msg)
    msg = input()

client.set_socket_status(False)