import securesocket as ss
import socket
import time

client = ss.Client(42067, "utf-8", "!DISCONN", "!HANDSHAKE", socket.gethostbyname(socket.gethostname()))
client.set_socket_status(True)
print(client)

time.sleep(0.1)

msg = ""
while msg != "stop":
    if msg != "":
        client.get_conn().send(msg, "utf-8")
    msg = input()

client.set_socket_status(False)