import entities as en
import socket
import securesocket as ss
import time
import tkinter as tk
from tkintermapview import TkinterMapView
import threading
import geocoder

# =========================
# GLOBALS
# =========================

markers = {}
paths = {}
map_widget = None
entry = None

my_conn_manager = en.ConnectionManager()
my_entity_manager = en.EntityManager()
my_database_manager = en.DatabaseManager()

my_ambulance_callsign = ""
my_ambulance_id = 0
my_crew_login = ""
my_crew_id = 0


try:
    with open("lastidempotencykey.key", "r") as f:
        previous_idempotency_key = int(f.read(1))
except:
    previous_idempotency_key = 0


# =========================
# NETWORK SETUP (RUN FIRST)
# =========================

def connect_to_server():
    client = ss.Client(
        42075,
        "utf-8",
        "!DISCONN",
        "!HANDSHAKE",
        socket.gethostbyname(socket.gethostname())
    )
    client.set_socket_status(True)

    time.sleep(0.1)

    en.SuperManager.setup(
        False,
        my_conn_manager,
        my_entity_manager,
        my_database_manager
    )

    my_conn_manager.set_secure_connection(client.get_conn())
    my_conn_manager.start_master()



def update_map_entities():
    while True:
        updated_markers = {}
        time.sleep(1)
        try:
            main.update_current_status()
        except Exception as e:
            print(f"THERE WAS AN EXCEPTION\n{e}")
        for entity in my_entity_manager.get_entites():
            if entity.get_id() not in markers and map_widget:
                # making a new marker
                marker_text = ""
                if type(entity) == en.Ambulance:
                    marker_text = entity.get_status().get_name() + " Ambulance"
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
    # while True:
    #     time.sleep(1)
    #     updated = {}

    #     for entity in my_entity_manager.get_entites():
    #         if entity.get_id() not in markers and map_widget:
    #             text = ""

    #             if type(entity) == en.Ambulance:
    #                 text = entity.get_status().get_name() + " Ambulance"
    #                 paths[entity.get_id()] = map_widget.set_path([
    #                     (entity.get_position().x, entity.get_position().y),
    #                     (entity.get_destination().get_position().x,
    #                      entity.get_destination().get_position().y)
    #                 ])

    #             elif type(entity) == en.Emergency:
    #                 text = f"Emergency severity {entity.get_severity()}"

    #             markers[entity.get_id()] = map_widget.set_marker(
    #                 entity.get_position().x,
    #                 entity.get_position().y,
    #                 text
    #             )
    #         else:
    #             markers[entity.get_id()].set_position(
    #                 entity.get_position().x,
    #                 entity.get_position().y
    #             )

    #         updated[entity.get_id()] = markers[entity.get_id()]

    #     for eid in list(markers):
    #         if eid not in updated:
    #             markers[eid].delete()
    #             markers.pop(eid)
    #             if eid in paths:
    #                 paths[eid].delete()
    #                 paths.pop(eid)



class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ambulance Control")
        self.geometry("900x600")
        self.frames = {}

    def show_frame(self, name):
        self.frames[name].tkraise()


class LoginFrame(tk.Frame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        tk.Label(self, text="Server Login", font=("Arial", 22)).pack(pady=40)

        self.username = tk.Entry(self)
        self.callsign = tk.Entry(self)
        self.password = tk.Entry(self, show="*")

        self.username.pack(pady=5)
        self.callsign.pack(pady=5)
        self.password.pack(pady=5)

        self.status = tk.Label(self, text="")
        self.status.pack(pady=5)

        tk.Button(self, text="Login", command=self.login).pack(pady=20)

    def login(self):
        user = self.username.get()
        clsgn = self.callsign.get()
        pwd = self.password.get()

        if not user or not pwd or not clsgn:
            self.status.config(text="Missing fields", fg="red")
            return

        # SEND LOGIN REQUEST TO SERVER
        my_conn_manager.send_socket_message(
            f"<LOGIN>{user}|{pwd}|{clsgn}",
            True
        )

        
        threading.Thread(
            target=self.wait_for_auth,
            daemon=True,
            args=(clsgn, user)
        ).start()

    def wait_for_auth(self, ambulance_callsign, crew_login):
        time.sleep(1.0)


        if my_conn_manager.logged_in:

            global my_ambulance_callsign
            global my_ambulance_id
            global my_crew_login
            global my_crew_id
            my_ambulance_callsign = ambulance_callsign
            my_ambulance_id = int(ambulance_callsign[-3:])
            my_crew_login = crew_login
            my_crew_id = int(crew_login[-3:])
            
            self.master.after(0, self.success)
        else:
            self.master.after(0, self.fail)

    def success(self):
        self.controller.show_frame("main")

        threading.Thread(
            target=update_map_entities,
            daemon=True
        ).start()

    def fail(self):
        self.status.config(text="Invalid login", fg="red")


class MainFrame(tk.Frame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        global entry, map_widget

        self._previous_status = None
        self._next_statuses = []

        # =========================
        # TOP COMMAND BAR
        # =========================

        def submit():
            if entry and entry.get():
                my_conn_manager.send_socket_message(entry.get(), False)

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        entry = tk.Entry(top, width=40)
        entry.pack(side="left", padx=(0, 10))

        tk.Button(top, text="Send", command=submit).pack(side="left")

        # =========================
        # MAIN CONTENT AREA
        # =========================

        content = tk.Frame(self)
        content.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------- LEFT: MAP ----------
        map_frame = tk.Frame(content)
        map_frame.pack(side="left", fill="both", expand=True)

        map_widget = TkinterMapView(map_frame, corner_radius=20)
        map_widget.pack(fill="both", expand=True)

        map_widget.set_position(51.5074, -0.1278)
        map_widget.set_zoom(10)

        # ---------- RIGHT: CONTROL PANEL ----------
        panel = tk.Frame(content, width=300)
        panel.pack(side="right", fill="y", padx=(10, 0))
        panel.pack_propagate(False)

        # =========================
        # DESCRIPTION BOX
        # =========================

        tk.Label(panel, text="Description", font=("Arial", 12, "bold")).pack(anchor="w")

        self.description = tk.Text(panel, height=6, wrap="word", state="disabled")
        self.description.pack(fill="x", pady=(5, 15))

        # =========================
        # UPDATE POSITION
        # =========================

        tk.Label(panel, text="Update Position", font=("Arial", 12, "bold")).pack(anchor="w")

        pos_frame = tk.Frame(panel)
        pos_frame.pack(fill="x", pady=5)

        tk.Button(
            pos_frame,
            text="Autofill",
            command=self.autofill_position
        ).pack(side="left")

        self.lat_entry = tk.Entry(pos_frame, width=10)
        self.lon_entry = tk.Entry(pos_frame, width=10)

        self.lat_entry.pack(side="left", padx=(0, 5))
        self.lon_entry.pack(side="left", padx=(0, 5))

        tk.Button(
            pos_frame,
            text="Update",
            command=self.update_position
        ).pack(side="left")

        # =========================
        # UPDATE STATUS
        # =========================

        tk.Label(panel, text="Update Status", font=("Arial", 12, "bold")).pack(anchor="w", pady=(15, 0))

        self.current_status_var = tk.StringVar()
        self.current_status_var.set("Current status: —")

        tk.Label(
            panel,
            textvariable=self.current_status_var,
            font=("Arial", 12)
        ).pack(anchor="w", pady=(10, 5))


        status_frame = tk.Frame(panel)
        status_frame.pack(fill="x", pady=5)

        self.status_var = tk.StringVar(value="Available")

        self.status_menu = tk.OptionMenu(
            status_frame,
            self.status_var,
            "Available",
        )
        self.status_menu.pack(side="left", fill="x", expand=True)

        tk.Button(
            status_frame,
            text="Update",
            command=self.update_status
        ).pack(side="left", padx=(5, 0))
    
    def set_description(self, text):
        self.description.config(state="normal")
        self.description.delete("1.0", tk.END)
        self.description.insert(tk.END, text)
        self.description.config(state="disabled")

    def update_current_status(self):
        try:
            current_status = my_entity_manager.get_entity_by_id(my_ambulance_id).get_status()
        except:
            return
        current_status_name = current_status.get_name()
        self.current_status_var.set(f"Current Status: {current_status_name}")

        if current_status == self._previous_status:
            return
        
        self._next_statuses = current_status.get_next_states()

        menu = self.status_menu["menu"]
        menu.delete(0, "end")

        next_status_names = []
        for status in self._next_statuses:
            next_status_names.append(status.get_name())

            menu.add_command(label=status.get_name(), command=lambda s=status.get_name(): self.status_var.set(s))
            
        
        self.status_var.set(current_status_name)

        self._previous_status = current_status

    def autofill_position(self):
        print("autofilling pos")
        
        g=geocoder.ip("me")
        if not g.ok:
            print("location fetch failed")
            return

        print(g.latlng)

        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, str(g.latlng[0]))

        self.lon_entry.delete(0, tk.END)
        self.lon_entry.insert(0, str(g.latlng[1]))

    def update_position(self):
        global previous_idempotency_key
        global my_ambulance_id

        lat = self.lat_entry.get()
        lon = self.lon_entry.get()

        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            print("Invalid coordinates")
            return

        my_conn_manager.send_socket_message(
            f"<UPDATE_ENTITY_POSITION|{my_crew_login+my_ambulance_callsign+str(previous_idempotency_key)}>{my_ambulance_id}|{lat}|{lon}",
            False
        )
        previous_idempotency_key += 1

    def update_status(self):
        global previous_idempotency_key
        global my_ambulance_id

        status = None
        status_name = self.status_var.get()
        state_keys = list(en.vehicle_states.keys())
        i=0
        for state in list(en.vehicle_states.values()):
            if state.get_name() == status_name:
                status = state
                break
            i+=1
        status_key = state_keys[i]

        my_conn_manager.send_socket_message(
            f"<SET_STATUS|{my_crew_login+my_ambulance_callsign+str(previous_idempotency_key)}>{my_ambulance_id}|{status_key}",
            False
        )
        previous_idempotency_key += 1



# =========================
# STARTUP
# =========================

connect_to_server()

app = App()

login = LoginFrame(app, app)
main = MainFrame(app, app)

app.frames["login"] = login
app.frames["main"] = main

login.place(relwidth=1, relheight=1)
main.place(relwidth=1, relheight=1)

app.show_frame("login")
app.mainloop()


my_conn_manager.send_socket_message("<LOGOUT>", False)

time.sleep(1.0)
my_conn_manager.disconnect()
my_conn_manager.end_master()

with open("lastidempotencykey.key", "w") as f:
    f.write(str(previous_idempotency_key))