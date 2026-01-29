import entities as en
import socket
import securesocket as ss
import time
import tkinter as tk
from tkintermapview import TkinterMapView
import threading
import geocoder


# GLOBALS


markers = {}
paths = {}
ambulance_map_widget = None
map_map_widget = None
entry = None

my_conn_manager = en.ConnectionManager()
my_entity_manager = en.EntityManager()
my_database_manager = en.DatabaseManager()

my_ambulance_callsign = ""
my_ambulance_id = 0
my_crew_login = ""
my_crew_id = 0
my_callhandler_login = ""
my_callhandler_id = 0
my_maplogin = ""
my_maplogin_id = 0

my_destination = None


try:
    with open("lastidempotencykey.key", "r") as f:
        previous_idempotency_key = int(f.read())
except Exception as e:
    previous_idempotency_key = 0



# NETWORK SETUP (RUN FIRST)

server_ipaddress = input()
if server_ipaddress == "":
    server_ipaddress = socket.gethostbyname(socket.gethostname())

def connect_to_server():
    client = ss.Client(
        42076,
        "utf-8",
        "!DISCONN",
        "!HANDSHAKE",
        server_ipaddress
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

previous_quals = []

def update_quals():
    while True:
        global previous_quals
        time.sleep(1)
        if previous_quals != en.qualifications:
            call_handler.rebuild_qual_checkboxes(en.qualifications)
            previous_quals = en.qualifications

def get_colour_by_severity(severity:int) -> str:
    if 0 <= severity and severity < 20:
        return "green"
    elif 20 <= severity and severity < 40:
        return "yellow"
    elif 40 <= severity and severity < 60:
        return "orange"
    elif 60 <= severity and severity < 80:
        return "red"
    elif 80 <= severity and severity < 100:
        return "magenta"
    return "white"

def update_map_entities(map_widget):
    while True:
        updated_markers = {}
        time.sleep(1)
        if my_ambulance_id != 0:
            try:
                main.update_current_status()
                main.set_eta(my_entity_manager.get_entity_by_id(my_ambulance_id).get_eta())
                global my_destination
                my_destination = my_entity_manager.get_entity_by_id(my_ambulance_id).get_destination()
                if type(my_destination) == en.Emergency:
                    main.set_description(my_destination.description)
                elif type(my_destination) == en.Ambulance:
                    main.set_description("")

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
                    new_marker = map_widget.set_marker(entity.get_position().x, entity.get_position().y, marker_text, marker_color_outside="blue", marker_color_circle="red")
                elif type(entity) == en.Emergency:
                    marker_text = "Emergency, severity:" + str(entity.get_severity()) + " requires " + str(entity.get_qualifications())
                    new_marker = map_widget.set_marker(entity.get_position().x, entity.get_position().y, marker_text, marker_color_outside=get_colour_by_severity(entity.get_severity()), marker_color_circle=get_colour_by_severity(entity.get_severity()))
                else:
                    new_marker = map_widget.set_marker(entity.get_position().x, entity.get_position().y, marker_text)
                markers[entity.get_id()] = (new_marker)


            else:
                # updating current marker
                markers[entity.get_id()].set_position(entity.get_position().x, entity.get_position().y)
                if type(entity) == en.Ambulance:
                    paths[entity.get_id()].set_position_list([(entity.get_position().x, entity.get_position().y), (entity.get_destination().get_position().x, entity.get_destination().get_position().y)])


                    markers[entity.get_id()].set_text(entity.get_status().get_name() + " " + str(entity) + str(entity.get_crew().get_qualifications())) # type: ignore
                
                elif type(entity) == en.Emergency:
                    marker_text = "Emergency, " + entity.injury + ", severity: " + str(entity.get_severity()) + " requires " + str(entity.get_qualifications())
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
    def __init__(self, master, controller, **kw):
        super().__init__(master, kw)
        self.controller = controller

        tk.Label(self, text="Login", font=("Arial", 22), bg="gray21", fg="white").pack(pady=40)

        self.username = tk.Entry(self)
        self.callsign = tk.Entry(self)
        self.password = tk.Entry(self, show="*")

        tk.Label(self, text="Crew ID or Call Handler ID", font=("Arial", 12, "bold"), bg="gray21", fg="white").pack(pady=5)
        self.username.pack(pady=5)
        tk.Label(self, text="Ambulance Callsign (if applicable)", font=("Arial", 12, "bold"), bg="gray21", fg="white").pack(pady=5)
        self.callsign.pack(pady=5)
        tk.Label(self, text="Password", font=("Arial", 12, "bold"), bg="gray21", fg="white").pack(pady=5)
        self.password.pack(pady=5)

        self.status = tk.Label(self, text="", bg="gray21")
        self.status.pack(pady=5)

        tk.Button(self, text="Login", command=self.login).pack(pady=20)

    def login(self):
        user = self.username.get()
        clsgn = self.callsign.get()
        pwd = self.password.get()

        if not user or not pwd:
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

    def wait_for_auth(self, ambulance_callsign, user_login):
        time.sleep(1.0)


        if my_conn_manager.logged_in:
            if user_login[:3] == "CRW":
                global my_ambulance_callsign
                global my_ambulance_id
                global my_crew_login
                global my_crew_id
                my_ambulance_callsign = ambulance_callsign
                my_ambulance_id = int(ambulance_callsign[-3:])
                my_crew_login = user_login
                my_crew_id = int(user_login[-3:])
                
                self.master.after(0, self.success_main_page)
            elif user_login[:3] == "CLH":
                global my_callhandler_login
                global my_callhandler_id
                my_callhandler_login = user_login
                my_callhandler_id = int(user_login[-3:])

                self.master.after(0, self.success_callhandler_page)
            elif user_login[:3] == "MAP":
                print("\n\n\nMAP LOGIN SUCCESS")
                global my_maplogin
                global my_maplogin_id
                my_maplogin = user_login
                my_maplogin_id = int(user_login[-3:])

                self.master.after(0, self.success_map_page)
            else:
                self.master.after(0, self.fail)

        else:
            self.master.after(0, self.fail)

    def success_main_page(self):
        self.controller.show_frame("main")
        global ambulance_map_widget
        if ambulance_map_widget != None:
            threading.Thread(
                target=update_map_entities,
                daemon=True,
                args=(ambulance_map_widget,)
            ).start()

    def success_callhandler_page(self):
        self.controller.show_frame("call_handler")

        threading.Thread(
            target=update_quals,
            daemon=True
        ).start()
    
    def success_map_page(self):
        print("map loading thread!")
        global map_map_widget
        self.controller.show_frame("map_view")
        if map_map_widget != None:
            threading.Thread(
                target=update_map_entities,
                daemon=True,
                args=(map_map_widget,)
            ).start()

    def fail(self):
        self.status.config(text="Invalid login", fg="red")


class MainFrame(tk.Frame):
    def __init__(self, master, controller, **kw):
        super().__init__(master, **kw)
        self.controller = controller

        global entry, ambulance_map_widget

        self._previous_status = None
        self._next_statuses = []

        
        # TOP COMMAND BAR
        

        def submit():
            if entry and entry.get():
                my_conn_manager.send_socket_message(entry.get(), False)

        top = tk.Frame(self, bg="gray21")
        top.pack(fill="x", padx=10, pady=10)

        entry = tk.Entry(top, width=40)
        entry.pack(side="left", padx=(0, 10))

        tk.Button(top, text="Send", command=submit).pack(side="left")

        
        # MAIN CONTENT AREA
        

        content = tk.Frame(self, bg="gray21")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        #  LEFT: MAP 
        map_frame = tk.Frame(content, bg="gray21")
        map_frame.pack(side="left", fill="both", expand=True)

        ambulance_map_widget = TkinterMapView(map_frame, corner_radius=20)
        ambulance_map_widget.pack(fill="both", expand=True)

        ambulance_map_widget.set_position(51.5074, -0.1278)
        ambulance_map_widget.set_zoom(10)

        #  RIGHT: CONTROL PANEL 
        panel = tk.Frame(content, width=300, bg="gray21")
        panel.pack(side="right", fill="y", padx=(10, 0))
        panel.pack_propagate(False)

        eta_panel = tk.Frame(panel, width=50, bg="gray10")
        eta_panel.pack(side="top", padx=10)

        self.eta_text = tk.StringVar()
        self.eta_text.set("00min")

        tk.Label(
            panel,
            textvariable=self.eta_text,
            font=("Arial", 12), bg="gray10", fg="white"
        ).pack(anchor="center", pady=(10, 10))
        
        # DESCRIPTION BOX
        

        tk.Label(panel, text="Description", font=("Arial", 12, "bold"), bg="gray21", fg="white").pack(anchor="w")

        self.description = tk.Text(panel, height=6, wrap="word", state="disabled")
        self.description.pack(fill="x", pady=(5, 15))

        
        # UPDATE POSITION
        

        tk.Label(panel, text="Update Position", font=("Arial", 12, "bold"), bg="gray21", fg="white").pack(anchor="w")

        pos_frame = tk.Frame(panel, bg="gray21")
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

        
        # UPDATE STATUS
        

        tk.Label(panel, text="Update Status", font=("Arial", 12, "bold"), bg="gray21", fg="white").pack(anchor="w", pady=(15, 0))

        self.current_status_var = tk.StringVar()
        self.current_status_var.set("Current status:")

        tk.Label(
            panel,
            textvariable=self.current_status_var,
            font=("Arial", 12), bg="gray21", fg="white"
        ).pack(anchor="w", pady=(10, 5))


        status_frame = tk.Frame(panel, bg="gray21")
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

    def set_eta(self, new_time_seconds:float):
        self.eta_text.set(str(int(new_time_seconds//60)).rjust(2, "0")+"min")
    
    def set_description(self, new_text):
        self.description.config(state="normal")
        self.description.delete("1.0", tk.END)
        self.description.insert(tk.END, new_text)
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

class CallHandlerFrame(tk.Frame):
    def __init__(self, master, controller, **kw):
        super().__init__(master, kw)
        self.controller = controller

        tk.Label(self, text="Call Handler", font=("Arial", 22), bg="gray21", fg="white").pack(pady=20)

        form = tk.Frame(self, bg="gray21")
        form.pack(pady=10)

        #  INJURY 
        tk.Label(form, text="Injury Type", bg="gray21", fg="white").grid(row=0, column=0, sticky="w")
        self.injury_entry = tk.Entry(form, width=30)
        self.injury_entry.grid(row=0, column=1, pady=5)

        #  SEVERITY 
        tk.Label(form, text="Category", bg="gray21", fg="white").grid(row=1, column=0, sticky="w")
        self.category_var = tk.IntVar(value=1)
        tk.Spinbox(
            form,
            from_=1,
            to=5,
            textvariable=self.category_var,
            width=5
        ).grid(row=1, column=1, sticky="w", pady=5)

        #  COORDINATES 
        tk.Label(form, text="Latitude", bg="gray21", fg="white").grid(row=2, column=0, sticky="w")
        self.lat_entry = tk.Entry(form)
        self.lat_entry.grid(row=2, column=1, pady=5)

        tk.Label(form, text="Longitude", bg="gray21", fg="white").grid(row=3, column=0, sticky="w")
        self.lon_entry = tk.Entry(form)
        self.lon_entry.grid(row=3, column=1, pady=5)

        #  DESCRIPTION 
        tk.Label(self, text="Description", bg="gray21", fg="white").pack(anchor="w", padx=40, pady=(15, 0))
        self.desc_box = tk.Text(self, height=5, wrap="word")
        self.desc_box.pack(fill="x", padx=40, pady=5)

        # QUALIFICATIONS CHECKBOXES

        self.qual_frame = tk.Frame(self, bg="gray21")
        self.qual_frame.pack(anchor="w", padx=40, pady=10)


        options = []
        for qual in en.qualifications:
            options.append(qual.get_name())        

        print(f"options: {options}")
        
        self.bool_vars = {}
        for opt in options:
            v = tk.BooleanVar()
            tk.Checkbutton(self.qual_frame, text=opt, variable=v, bg="gray21", fg="white").pack(anchor="w")
            self.bool_vars[opt] = v

        #  BUTTONS 
        btns = tk.Frame(self, bg="gray21")
        btns.pack(pady=20)

        tk.Button(
            btns,
            text="Submit Emergency",
            command=self.submit_emergency,
        ).pack(side="left", padx=10)

        

    def rebuild_qual_checkboxes(self, qualifications):
        print("updating qualifications...")
        for w in self.qual_frame.winfo_children():
            w.destroy()
        
        self.bool_vars = {}
        self.checks = {}

        options = []
        for qual in qualifications:
            options.append(qual.get_name())

        print(options)


        for opt in options:
            v = tk.BooleanVar()
            cb = tk.Checkbutton(
                self.qual_frame,
                text=opt,
                variable=v,
                bg="gray21",
                fg="white",
                activebackground="gray30",
                activeforeground="white",
                selectcolor="gray30"
            )
            cb.pack(anchor="w")
            self.bool_vars[opt] = v
            self.checks[opt] = cb

    def reset_qual_checkboxes(self):
        for opt in list(self.bool_vars.keys()):
            self.bool_vars[opt].set(False)


    def submit_emergency(self):
        injury = self.injury_entry.get()
        severity = int(100-(20 * self.category_var.get()))
        lat = self.lat_entry.get()
        lon = self.lon_entry.get()
        desc = self.desc_box.get("1.0", tk.END).strip()

        selected_qual_names = [opt for opt, v in self.bool_vars.items() if v.get()]
        

        if not injury or not lat or not lon or not desc:
            print("Missing fields")
            return

        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            print("Invalid coordinates")
            return

        global previous_idempotency_key

        message = (
            f"<CREATE_ENTITY|emergency|newemergency{previous_idempotency_key}>{int('001'+str(my_callhandler_id).rjust(3,'0')+str(previous_idempotency_key).rjust(3,'0'))}|{lat}|{lon}|{severity}|{injury}|{desc}"
        )
        
        my_conn_manager.send_socket_message(message, False)

        counter = 1
        for name in selected_qual_names:
            for qual in en.qualifications:
                if qual.get_name() == name:
                    my_conn_manager.send_socket_message(f"<ADD_QUALIFICATION|emergency|addnewemergency{previous_idempotency_key+counter}>{int('001'+str(my_callhandler_id).rjust(3,'0')+str(previous_idempotency_key).rjust(3,'0'))}|{qual.get_id()}",False)
                    break
            counter += 1

        previous_idempotency_key += 1+counter

        print("Emergency sent")

        # clear form
        self.injury_entry.delete(0, tk.END)
        self.lat_entry.delete(0, tk.END)
        self.lon_entry.delete(0, tk.END)
        self.desc_box.delete("1.0", tk.END)
        self.reset_qual_checkboxes()

class MapViewFrame(tk.Frame):
    def __init__(self, master, controller, **kw):
        super().__init__(master, **kw)
        self.controller = controller

        global entry, map_map_widget

        
        # TOP COMMAND BAR
        

        # def submit():
        #     if entry and entry.get():
        #         my_conn_manager.send_socket_message(entry.get(), False)

        # top = tk.Frame(self, bg="gray21")
        # top.pack(fill="x", padx=10, pady=10)

        # entry = tk.Entry(top, width=40)
        # entry.pack(side="left", padx=(0, 10))

        # tk.Button(top, text="Send", command=submit).pack(side="left")

        
        # MAIN CONTENT AREA
        

        content = tk.Frame(self, bg="gray21")
        content.pack(fill="both", expand=True, padx=10, pady=10)

        #  LEFT: MAP 
        map_frame = tk.Frame(content, bg="gray21")
        map_frame.pack(side="left", fill="both", expand=True)

        map_map_widget = TkinterMapView(map_frame, corner_radius=20)
        map_map_widget.pack(fill="both", expand=True)

        map_map_widget.set_position(51.5074, -0.1278)
        map_map_widget.set_zoom(10)


# STARTUP


connect_to_server()

app = App()





login = LoginFrame(app, app, bg="gray21")
main = MainFrame(app, app, bg="gray21")
call_handler = CallHandlerFrame(app, app, bg="gray21")
map_view = MapViewFrame(app, app, bg="gray21")

app.frames["login"] = login
app.frames["main"] = main
app.frames["call_handler"] = call_handler
app.frames["map_view"] = map_view

login.place(relwidth=1, relheight=1)
main.place(relwidth=1, relheight=1)
call_handler.place(relwidth=1, relheight=1)
map_view.place(relwidth=1, relheight=1)

app.show_frame("login")
app.mainloop()


my_conn_manager.send_socket_message("<LOGOUT>", False)

time.sleep(1.0)
my_conn_manager.disconnect()
my_conn_manager.end_master()

with open("lastidempotencykey.key", "w") as f:
    f.write(str(previous_idempotency_key))