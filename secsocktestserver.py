import securesocket as ss

server = ss.Server(42067, "utf-8", "!DISCONN", "!HANDSHAKE")
server.set_socket_status(True)
print(server)
input()
server.set_socket_status(False)