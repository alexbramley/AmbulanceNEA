import securesocket as ss

server = ss.Server(42049, 64, "utf-8", "!DISCONN")
server.set_socket_status(True)
print(server)
input()
server.set_socket_status(False)