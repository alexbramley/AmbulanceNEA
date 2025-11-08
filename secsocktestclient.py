import securesocket as ss
import socket

client = ss.Client(42049, 64, "utf-8", "!DISCONN", socket.gethostbyname(socket.gethostname()))
client.set_socket_status(True)
print(client)

msg = ""
while msg != "stop":
    msg = input()
    client.send(msg)

client.set_socket_status(False)