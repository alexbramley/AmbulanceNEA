import entities as en
import socket
import securesocket as ss
import time
import tkinter as tk
from tkintermapview import TkinterMapView
import threading


def update_map_entities():
    while True:
        updated_markers = {}
        time.sleep(1)
        for entity in my_entity_manager.get_entites():
            if entity.get_id() not in markers:
                # making a new marker
                marker_text = ""
                if type(entity) == en.Ambulance:
                    marker_text = entity.get_status().get_name() + "Ambulance"
                    new_path = map_widget.set_path([(entity.get_position().x, entity.get_position().y), (entity.get_destination().get_position().x, entity.get_destination().get_position().y)])
                    paths[entity.get_id()] = new_path
                elif type(entity) == en.Emergency:
                    marker_text = "Emergency, severity:" + str(entity.get_severity()) + " requires " + str(entity.get_qualifications())
                new_marker = map_widget.set_marker(entity.get_position().x, entity.get_position().y, marker_text)
                markers[entity.get_id()] = (new_marker)


            else:
                # updating current marker
                markers[entity.get_id()].set_position(entity.get_position().x, entity.get_position().y)
                if type(entity) == en.Ambulance:
                    paths[entity.get_id()].set_position_list([(entity.get_position().x, entity.get_position().y), (entity.get_destination().get_position().x, entity.get_destination().get_position().y)])

                    markers[entity.get_id()].set_text(entity.get_status().get_name() + " Ambulance going to " + str(entity.get_destination()))
                
                elif type(entity) == en.Emergency:
                    marker_text = "Emergency, severity:" + str(entity.get_severity()) + " requires " + str(entity.get_qualifications())
                    markers[entity.get_id()].set_text(marker_text)

            updated_markers[entity.get_id()] = (markers[entity.get_id()])

        for entity_id in list(markers):
            if entity_id not in updated_markers:
                marker = markers.pop(entity_id)
                marker.delete()
                if entity_id in paths:
                    path = paths.pop(entity_id)
                    path.delete()


my_conn_manager = en.ConnectionManager()
my_entity_manager = en.EntityManager()
my_database_manager = en.DatabaseManager()

def setup():
    client = ss.Client(42067, "utf-8", "!DISCONN", "!HANDSHAKE", socket.gethostbyname(socket.gethostname()))
    client.set_socket_status(True)
    print(client)

    time.sleep(0.1)

    en.SuperManager.setup(False, my_conn_manager, my_entity_manager, my_database_manager)

    my_conn_manager.set_secure_connection(client.get_conn())
    my_conn_manager.start_master()

    update_map_thread = threading.Thread(target=update_map_entities, daemon=True)
    update_map_thread.start()



    

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

markers = {}
paths = {}

map_widget = TkinterMapView(root, width=900, height=500, corner_radius=0)
map_widget.pack(fill="both", expand=True, padx=10, pady=(0,10))

map_widget.set_position(51.5074, -0.1278)
map_widget.set_zoom(10)

root.after(100, setup)

root.mainloop()







# msg = ""
# while msg != "stop":
#     if msg != "":
#         my_conn_manager.send_socket_message(msg)
#     msg = input()


my_conn_manager.disconnect()
my_conn_manager.end_master()