import entities as en
import socket
import securesocket as ss
import time
import tkinter as tk
from tkintermapview import TkinterMapView



my_conn_manager = en.ConnectionManager()
my_entity_manager = en.EntityManager()

def setup():
    client = ss.Client(42076, "utf-8", "!DISCONN", "!HANDSHAKE", socket.gethostbyname(socket.gethostname()))
    client.set_socket_status(True)
    print(client)

    time.sleep(0.1)

    en.SuperManager.setup(False, my_conn_manager, my_entity_manager)

    my_conn_manager.set_secure_connection(client.get_conn())
    my_conn_manager.start_master()



    

### TKINTER

def submit():
    query = entry.get()
    print(f"Submitted:{query}")
    if query != "":
        my_conn_manager.send_socket_message(query)

root = tk.Tk()
root.title("map app")
root.geometry("900x600")

top_frame = tk.Frame(root)
top_frame.pack(fill="x", padx=10, pady=10)

entry = tk.Entry(top_frame, width=40)
entry.pack(side="left", padx=(0,10))

submit_btn = tk.Button(top_frame, text="Submit", command=submit)
submit_btn.pack()

map_widget = TkinterMapView(root, width=900, height=500, corner_radius=0)
map_widget.pack(fill="both", expand=True, padx=10, pady=(0,10))

map_widget.set_position(51.5074, -0.1278)
map_widget.set_zoom(10)

root.after(100, setup)

root.mainloop()

def update_map():
    






# msg = ""
# while msg != "stop":
#     if msg != "":
#         my_conn_manager.send_socket_message(msg)
#     msg = input()


my_conn_manager.disconnect()
my_conn_manager.end_master()