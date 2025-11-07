import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk
import xml.etree.ElementTree as ET
from threading import Timer, Thread
import os, json, subprocess, concurrent.futures, socket, math, platform, queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ----------------------------------------------------------------------
#  Data classes
# ----------------------------------------------------------------------
class Device:
    def __init__(self, ip, name, mac, switch, port, vlan, url):
        self.ip = ip
        self.name = name
        self.mac = mac
        self.switch = switch
        self.port = port
        self.vlan = vlan
        self.url = url
        self.groups = set()
        self.original_position = None  # (x, y) in ORIGINAL image coordinates
        self.canvas_id = None
        self.color = 'blue'

class Group:
    def __init__(self, name): self.name = name

# ----------------------------------------------------------------------
#  Main application
# ----------------------------------------------------------------------
class NetworkMapper:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Floorplan Mapper")
        self.devices = {}          # key to Device
        self.groups  = {}          # name to Group
        self.xml_file = "network.xml"
        self.map_image_path = "drawing.jpg"
        self.state_file = "mapper_state.json"

        self.zoom_level = 1.0
        self.base_radius = 10
        self.original_img = None
        self.current_img = None
        self.map_tk = None
        self.image_id = None

        self.dragging = None
        self.selected_key = None
        self.click_x = self.click_y = None
        self.drag_threshold = 5

        self.current_dev = None    # device shown in side-panel

        self.load_xml()
        self.load_state()
        self.setup_gui()
        self.load_map_image()      # after canvas exists
        self.draw_devices()
        self.setup_file_watcher()
        self.auto_save_timer = None

        # Ping queue for non-blocking UI
        self.ping_queue = queue.Queue()
        self.ping_thread = None
        self.online = 0
        self.total_devs = 0

    # ------------------------------------------------------------------
    #  GUI construction
    # ------------------------------------------------------------------
    def setup_gui(self):
        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # ---------- LEFT SIDE PANEL ----------
        side = tk.Frame(main, width=320, bg='#f0f0f0')
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.pack_propagate(False)

        # Search
        tk.Label(side, text="Search (IP/Name):", bg='#f0f0f0').pack(pady=5)
        self.search_entry = tk.Entry(side)
        self.search_entry.pack(fill=tk.X, padx=10)
        self.search_entry.bind("<KeyRelease>", self.update_search_results)

        self.search_lb = tk.Listbox(side, height=10)
        self.search_lb.pack(fill=tk.X, padx=10, pady=5)
        self.search_lb.bind("<<ListboxSelect>>", self.on_select_for_deploy)

        # Groups
        tk.Label(side, text="Groups:", bg='#f0f0f0').pack(pady=(15,5))
        self.groups_lb = tk.Listbox(side, height=5)
        self.groups_lb.pack(fill=tk.X, padx=10)

        btns = tk.Frame(side, bg='#f0f0f0')
        btns.pack(pady=5)
        tk.Button(btns, text="Create", width=10, command=self.create_group).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Delete", width=10, command=self.delete_group).pack(side=tk.LEFT, padx=5)

        # Filters
        tk.Label(side, text="Filters:", bg='#f0f0f0').pack(pady=(15,5))
        self.filter_entry = tk.Entry(side)
        self.filter_entry.pack(fill=tk.X, padx=10)
        tk.Label(side,
                 text="e.g. include shopfloor, exclude plc, name:printer, ips:192.168.1.11,192.168.1.12",
                 bg='#f0f0f0', font=('Arial',8)).pack(padx=10)

        fbtns = tk.Frame(side, bg='#f0f0f0')
        fbtns.pack(pady=5)
        tk.Button(fbtns, text="Apply", width=8, command=self.apply_filter).pack(side=tk.LEFT, padx=2)
        tk.Button(fbtns, text="Clear", width=8, command=self.clear_filter).pack(side=tk.LEFT, padx=2)
        tk.Button(fbtns, text="Ping",   width=8, command=self.ping_filtered).pack(side=tk.LEFT, padx=2)
        tk.Button(fbtns, text="Export", width=8, command=self.export_filtered).pack(side=tk.LEFT, padx=2)
        tk.Button(fbtns, text="List",   width=8, command=self.show_online_offline).pack(side=tk.LEFT, padx=2)

        # ---------- DEVICE INFO PANEL ----------
        info = tk.LabelFrame(side, text="Device Info", bg='#f0f0f0')
        info.pack(fill=tk.X, padx=10, pady=15)

        labels = [
            ("IP:",       "ip_label"),
            ("Name:",     "name_label"),
            ("MAC:",      "mac_label"),
            ("Switch:",   "switch_label"),
            ("Port:",     "port_label"),
            ("VLAN:",     "vlan_label"),
            ("URL:",      "url_label"),
        ]
        for txt, attr in labels:
            lbl = tk.Label(info, text=txt, bg='#f0f0f0', anchor='w')
            lbl.pack(fill=tk.X, padx=5)
            setattr(self, attr, lbl)

        tk.Label(info, text="Groups:", bg='#f0f0f0').pack(anchor='w', padx=5)
        self.groups_entry = tk.Entry(info)
        self.groups_entry.pack(fill=tk.X, padx=5, pady=2)

        ibtns = tk.Frame(info, bg='#f0f0f0')
        ibtns.pack(pady=5)
        self.save_btn = tk.Button(ibtns, text="Save Groups", state=tk.DISABLED, command=self.save_groups)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        self.del_btn  = tk.Button(ibtns, text="Delete", state=tk.DISABLED, command=self.delete_device)
        self.del_btn.pack(side=tk.LEFT, padx=5)

        self.clear_device_info()

        # ---------- CANVAS ----------
        canvas_frame = tk.Frame(main)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg='white')
        hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL,   command=self.canvas.yview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack(side=tk.RIGHT,  fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        # bindings
        self.canvas.bind("<MouseWheel>", self.zoom)          # Windows / macOS
        self.canvas.bind("<Button-4>",   lambda e: self.zoom(e, 1.1))
        self.canvas.bind("<Button-5>",   lambda e: self.zoom(e, 0.9))
        self.canvas.bind("<Button-1>",   self.on_click)
        self.canvas.bind("<B1-Motion>",  self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_drop)
        self.canvas.bind("<Motion>",     self.on_hover)

        self.update_groups_list()

    # ------------------------------------------------------------------
    #  Image handling
    # ------------------------------------------------------------------
    def load_map_image(self):
        if not os.path.exists(self.map_image_path):
            return
        self.original_img = Image.open(self.map_image_path)
        self.current_img  = self.original_img.copy()
        self.map_tk = ImageTk.PhotoImage(self.current_img)
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.map_tk)
        w, h = self.original_img.size
        self.canvas.config(scrollregion=(0, 0, w, h))

    # ------------------------------------------------------------------
    #  Zoom (mouse-wheel centred on cursor)
    # ------------------------------------------------------------------
    def zoom(self, event, factor=None):
        if not self.original_img:
            return
        if factor is None:
            factor = 1.1 if event.delta > 0 else 0.9

        # mouse position in canvas coordinates (current scaled)
        mx = self.canvas.canvasx(event.x)
        my = self.canvas.canvasy(event.y)

        old_zoom = self.zoom_level
        self.zoom_level *= factor

        # resize image
        nw = int(self.original_img.width  * self.zoom_level)
        nh = int(self.original_img.height * self.zoom_level)
        self.current_img = self.original_img.resize((nw, nh), Image.LANCZOS)
        self.map_tk = ImageTk.PhotoImage(self.current_img)
        self.canvas.itemconfig(self.image_id, image=self.map_tk)
        self.canvas.config(scrollregion=(0, 0, nw, nh))

        # redraw devices at scaled positions
        self.draw_devices()

        # keep mouse point fixed
        new_mx = mx * factor
        new_my = my * factor
        self.canvas.xview_moveto((new_mx - event.x) / nw)
        self.canvas.yview_moveto((new_my - event.y) / nh)

    # ------------------------------------------------------------------
    #  XML / State
    # ------------------------------------------------------------------
    def get_text(self, parent, tag, default=''):
        el = parent.find(tag)
        return el.text.strip() if el is not None and el.text else default

    def load_xml(self):
        if not os.path.exists(self.xml_file):
            return
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
            for dev_el in root.findall('device'):
                ip   = self.get_text(dev_el, 'ip')
                name = self.get_text(dev_el, 'name')
                mac  = self.get_text(dev_el, 'mac')
                sw   = self.get_text(dev_el, 'switch')
                port = self.get_text(dev_el, 'port')
                vlan = self.get_text(dev_el, 'vlan')
                url  = self.get_text(dev_el, 'url')

                key = name if name else ip
                if not key:
                    key = mac if mac else f"unk_{len(self.devices)}"
                while key in self.devices:
                    key += "_dup"

                if key not in self.devices:
                    self.devices[key] = Device(ip, name, mac, sw, port, vlan, url)
                else:
                    d = self.devices[key]
                    d.ip, d.name, d.mac, d.switch, d.port, d.vlan, d.url = ip, name, mac, sw, port, vlan, url
        except ET.ParseError as e:
            messagebox.showerror("XML Error", str(e))

    def load_state(self):
        if not os.path.exists(self.state_file):
            return
        with open(self.state_file) as f:
            st = json.load(f)
        for g in st.get('groups', []):
            self.groups[g] = Group(g)
        for key, data in st.get('devices', {}).items():
            if key in self.devices:
                dev = self.devices[key]
                dev.groups = set(data.get('groups', []))
                pos = data.get('position')
                if pos:
                    dev.original_position = tuple(pos)

    def save_state(self):
        st = {
            "groups": list(self.groups.keys()),
            "devices": {}
        }
        for k, d in self.devices.items():
            st["devices"][k] = {
        "groups": list(d.groups),
        "position": list(d.original_position) if d.original_position else None
            }
        with open(self.state_file, 'w') as f:
            json.dump(st, f)

    def schedule_save(self):
        if self.auto_save_timer:
            self.auto_save_timer.cancel()
        self.auto_save_timer = Timer(5.0, self.save_state)
        self.auto_save_timer.start()

    # ------------------------------------------------------------------
    #  File watcher (XML changes)
    # ------------------------------------------------------------------
    def setup_file_watcher(self):
        class Handler(FileSystemEventHandler):
            def __init__(self, app):
                self.app = app
            def on_modified(self, ev):
                if ev.src_path == os.path.abspath(self.app.xml_file):
                    self.app.load_xml()
                    self.app.draw_devices()
                    messagebox.showinfo("Update", "network.xml changed – reloaded")
        obs = Observer()
        obs.schedule(Handler(self), path=os.path.dirname(os.path.abspath(self.xml_file)))
        obs.start()

    # ------------------------------------------------------------------
    #  Search / Deploy
    # ------------------------------------------------------------------
    def update_search_results(self, _=None):
        q = self.search_entry.get().lower()
        self.search_lb.delete(0, tk.END)
        for key, dev in self.devices.items():
            if dev.original_position:               # already placed to skip
                continue
            s = f"{key} {dev.ip or ''} {dev.name or ''}".lower()
            if q in s:
                self.search_lb.insert(tk.END, key)

    def on_select_for_deploy(self, _=None):
        sel = self.search_lb.curselection()
        if not sel: return
        key = self.search_lb.get(sel[0])
        dev = self.devices[key]

        # ----- ask for groups -----
        gs = simpledialog.askstring("Groups", "Comma-separated groups:", initialvalue=', '.join(dev.groups))
        if gs:
            for g in [x.strip() for x in gs.split(',') if x.strip()]:
                if g not in self.groups:
                    self.groups[g] = Group(g)
                dev.groups.add(g)
            self.update_groups_list()

        # start dragging to place
        self.dragging = dev
        messagebox.showinfo("Deploy", "Click & drag on the map to place the device.")

    # ------------------------------------------------------------------
    #  Mouse handling (click / drag / drop) – FIXED CLICK AFTER ZOOM
    # ------------------------------------------------------------------
    def on_click(self, ev):
        self.click_x, self.click_y = ev.x, ev.y
        self.selected_key = None
        if self.dragging:
            return

        # Use canvas (scaled + scrolled) coordinates for hit detection
        cx = self.canvas.canvasx(ev.x)
        cy = self.canvas.canvasy(ev.y)

        # halo=5 gives tolerance for small circles at low zoom
        item = self.canvas.find_closest(cx, cy, halo=5)[0]
        tags = self.canvas.gettags(item)
        if tags and tags[0].startswith('dev:'):
            self.selected_key = tags[0][4:]          # strip "dev:"

    def on_drag(self, ev):
        cx = self.canvas.canvasx(ev.x)
        cy = self.canvas.canvasy(ev.y)
        r  = self.base_radius * self.zoom_level

        if self.dragging:
            # erase temporary circle
            if self.dragging.canvas_id:
                self.canvas.delete(self.dragging.canvas_id)
            self.dragging.canvas_id = self.canvas.create_oval(
                cx-r, cy-r, cx+r, cy+r, fill=self.dragging.color, tags='temp')
            return

        # start moving an existing device?
        if self.selected_key and not self.dragging:
            dx = ev.x - self.click_x
            dy = ev.y - self.click_y
            if math.hypot(dx, dy) > self.drag_threshold:
                dev = self.devices[self.selected_key]
                self.dragging = dev
                if dev.canvas_id:
                    self.canvas.delete(dev.canvas_id)
                dev.canvas_id = None

        if self.dragging:
            if self.dragging.canvas_id:
                self.canvas.delete(self.dragging.canvas_id)
            self.dragging.canvas_id = self.canvas.create_oval(
                cx-r, cy-r, cx+r, cy+r, fill=self.dragging.color, tags='temp')

    def on_drop(self, ev):
        if self.dragging:
            # Store position in ORIGINAL image coordinates
            cx = self.canvas.canvasx(ev.x) / self.zoom_level
            cy = self.canvas.canvasy(ev.y) / self.zoom_level

            # Prevent duplicate placement
            if self.dragging.original_position and self.dragging.color != 'orange':
                pass  # already placed, just moving
            elif self.dragging.original_position:
                messagebox.showerror("Error", "Device already placed!")
                self.dragging.color = 'orange'

            # Clean temporary circle
            if self.dragging.canvas_id:
                self.canvas.delete(self.dragging.canvas_id)

            self.dragging.original_position = (cx, cy)
            self.draw_device(self.dragging, self.key_of(self.dragging))
            self.dragging = None
            self.schedule_save()
        else:
            # Just a click to show info
            if self.selected_key:
                dev = self.devices[self.selected_key]
                self.show_device_info(dev)

        self.click_x = self.click_y = None
        self.selected_key = None

    def on_hover(self, ev):
        item = self.canvas.find_closest(ev.x, ev.y)[0]
        tags = self.canvas.gettags(item)
        if tags and tags[0].startswith('dev:'):
            key = tags[0][4:]
            dev = self.devices.get(key)
            if dev:
                self.root.title(f"Mapper – {dev.name or dev.ip}")
            else:
                self.root.title("Mapper")
        else:
            self.root.title("Mapper")

    # ------------------------------------------------------------------
    #  Drawing
    # ------------------------------------------------------------------
    def key_of(self, dev):
        for k, d in self.devices.items():
            if d is dev: return k
        return None

    def draw_devices(self):
        for key, dev in self.devices.items():
            self.draw_device(dev, key)

    def draw_device(self, dev, key):
        if dev.canvas_id:
            self.canvas.delete(dev.canvas_id)
        if not dev.original_position:
            return
        ox, oy = dev.original_position
        x = ox * self.zoom_level
        y = oy * self.zoom_level
        r = self.base_radius * self.zoom_level
        dev.canvas_id = self.canvas.create_oval(
            x-r, y-r, x+r, y+r,
            fill=dev.color,
            tags=f'dev:{key}'
        )

    # ------------------------------------------------------------------
    #  Side-panel device info
    # ------------------------------------------------------------------
    def show_device_info(self, dev):
        self.current_dev = dev
        self.ip_label.config(text=f"IP: {dev.ip}")
        self.name_label.config(text=f"Name: {dev.name}")
        self.mac_label.config(text=f"MAC: {dev.mac}")
        self.switch_label.config(text=f"Switch: {dev.switch}")
        self.port_label.config(text=f"Port: {dev.port}")
        self.vlan_label.config(text=f"VLAN: {dev.vlan}")
        self.url_label.config(text=f"URL: {dev.url}")
        self.groups_entry.delete(0, tk.END)
        self.groups_entry.insert(0, ', '.join(sorted(dev.groups)))
        self.save_btn.config(state=tk.NORMAL)
        self.del_btn.config(state=tk.NORMAL)

    def clear_device_info(self):
        self.current_dev = None
        for lbl in (self.ip_label, self.name_label, self.mac_label,
                    self.switch_label, self.port_label, self.vlan_label,
                    self.url_label):
            lbl.config(text=lbl.cget('text').split(':')[0] + ": ")
        self.groups_entry.delete(0, tk.END)
        self.save_btn.config(state=tk.DISABLED)
        self.del_btn.config(state=tk.DISABLED)

    def save_groups(self):
        if not self.current_dev: return
        txt = self.groups_entry.get()
        self.current_dev.groups = {g.strip() for g in txt.split(',') if g.strip()}
        self.schedule_save()
        messagebox.showinfo("Saved", "Groups updated")

    def delete_device(self):
        if not self.current_dev: return
        if not messagebox.askyesno("Delete", "Remove this device from the map?"):
            return
        self.canvas.delete(self.current_dev.canvas_id)
        self.current_dev.original_position = None
        self.current_dev.canvas_id = None
        self.current_dev.color = 'blue'
        self.schedule_save()
        self.clear_device_info()

    # ------------------------------------------------------------------
    #  Groups management
    # ------------------------------------------------------------------
    def create_group(self):
        name = simpledialog.askstring("New Group", "Group name:")
        if name and name not in self.groups:
            self.groups[name] = Group(name)
            self.update_groups_list()
            self.schedule_save()

    def delete_group(self):
        sel = self.groups_lb.curselection()
        if not sel: return
        name = self.groups_lb.get(sel[0])
        del self.groups[name]
        for dev in self.devices.values():
            dev.groups.discard(name)
        self.update_groups_list()
        self.schedule_save()

    def update_groups_list(self):
        self.groups_lb.delete(0, tk.END)
        for g in sorted(self.groups.keys()):
            self.groups_lb.insert(tk.END, g)

    # ------------------------------------------------------------------
    #  Filters
    # ------------------------------------------------------------------
    def parse_filters(self, txt):
        parts = [p.strip() for p in txt.split(',')]
        f = {'inc':[], 'exc':[], 'name':[], 'switch':[], 'ips':[]}
        for p in parts:
            if p.startswith('include '):  f['inc'].append(p[8:].strip())
            elif p.startswith('exclude '): f['exc'].append(p[8:].strip())
            elif p.startswith('name:'):    f['name'].append(p[5:].strip())
            elif p.startswith('switch:'): f['switch'].append(p[7:].strip())
            elif p.startswith('ips:'):     f['ips'].extend([i.strip() for i in p[4:].split(';')])
        return f

    def matches_filter(self, dev, f):
        if f['inc'] and not any(g in dev.groups for g in f['inc']): return False
        if any(g in dev.groups for g in f['exc']): return False
        if f['name'] and (dev.name or '').lower() not in [n.lower() for n in f['name']]: return False
        if f['switch'] and (dev.switch or '').lower() not in [s.lower() for s in f['switch']]: return False
        if f['ips'] and (dev.ip or '').lower() not in [i.lower() for i in f['ips']]: return False
        return True

    def apply_filter(self):
        txt = self.filter_entry.get()
        filt = self.parse_filters(txt)
        self.clear_colors(exclude=['green','red'])
        for key, dev in self.devices.items():
            if self.matches_filter(dev, filt):
                dev.color = 'dark violet'
                self.draw_device(dev, key)

    def clear_filter(self):
        self.clear_colors()
        for key, dev in self.devices.items():
            if dev.original_position:
                dev.color = 'blue'
                self.draw_device(dev, key)

    def clear_colors(self, exclude=None):
        if exclude is None: exclude = []
        for dev in self.devices.values():
            if dev.color not in exclude:
                dev.color = 'blue'
                if dev.original_position:
                    self.draw_device(dev, self.key_of(dev))

    def get_filtered(self):
        filt = self.parse_filters(self.filter_entry.get())
        return [dev for dev in self.devices.values() if self.matches_filter(dev, filt) and dev.original_position]

    # ------------------------------------------------------------------
    #  Ping – FIXED (non-blocking UI)
    # ------------------------------------------------------------------
    def is_online(self, target):
        """Return True if target (IP or hostname) is reachable."""
        if not target:
            return False

        system = platform.system()
        if system == "Windows":
            cmd = ['ping', '-n', '1', '-w', '1000', target]
        else:
            cmd = ['ping', '-c', '1', '-W', '1', target]

        try:
            result = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result == 0:
                return True
        except Exception:
            pass

        # Fallback: try TCP connect on common ports
        for port in (80, 443, 22, 23, 9100):
            try:
                with socket.create_connection((target, port), timeout=1):
                    return True
            except (OSError, socket.gaierror):
                continue
        return False

    def ping_filtered(self):
        devs = self.get_filtered()
        if not devs:
            messagebox.showinfo("Ping", "No devices match the filter.")
            return

        self.online = 0
        self.total_devs = len(devs)

        def worker():
            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
                futures = {}
                for dev in devs:
                    target = dev.name if dev.vlan == '1088' else dev.ip
                    futures[pool.submit(self.is_online, target)] = dev
                for f in concurrent.futures.as_completed(futures):
                    dev = futures[f]
                    color = 'green' if f.result() else 'red'
                    self.ping_queue.put((dev, color))
            self.ping_queue.put(None)  # end signal

        self.ping_thread = Thread(target=worker, daemon=True)
        self.ping_thread.start()
        self.root.after(100, self.process_ping_queue)

    def process_ping_queue(self):
        try:
            while True:
                item = self.ping_queue.get_nowait()
                if item is None:
                    messagebox.showinfo("Ping", f"{self.online}/{self.total_devs} online")
                    return
                dev, color = item
                dev.color = color
                self.draw_device(dev, self.key_of(dev))
                if color == 'green':
                    self.online += 1
        except queue.Empty:
            pass
        self.root.after(100, self.process_ping_queue)

    # ------------------------------------------------------------------
    #  Export / List
    # ------------------------------------------------------------------
    def export_filtered(self):
        devs = self.get_filtered()
        if not devs:
            messagebox.showinfo("Export", "Nothing to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, 'w') as f:
                for d in devs:
                    f.write(f"{d.name or d.ip}: {d.ip}  groups: {', '.join(d.groups)}\n")
            messagebox.showinfo("Export", "Done")

    def show_online_offline(self):
        devs = self.get_filtered()
        if not devs:
            messagebox.showinfo("List", "No filtered devices.")
            return
        on  = [d.name or d.ip for d in devs if d.color == 'green']
        off = [d.name or d.ip for d in devs if d.color == 'red']
        msg = f"Online: {', '.join(on)}\nOffline: {', '.join(off)}"
        messagebox.showinfo("Online / Offline", msg)

# ----------------------------------------------------------------------
#  Run
# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkMapper(root)
    root.mainloop()
