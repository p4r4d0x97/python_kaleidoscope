import multiprocessing
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil
import fnmatch
import threading
import time
import queue
from multiprocessing import Pool, cpu_count
import sys

def copy_func(task):
    src, dest = task
    shutil.copy2(src, dest)

class AdvancedCopyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Copy Tool")
        self.root.geometry("600x600")

        # Copy mode
        tk.Label(root, text="Copy Mode:").pack()
        self.mode_var = tk.StringVar(value="cross")
        tk.Radiobutton(root, text="All sources to all destinations (cross)", variable=self.mode_var, value="cross").pack(anchor=tk.W)
        tk.Radiobutton(root, text="Pair sources with destinations (pairwise)", variable=self.mode_var, value="pairwise").pack(anchor=tk.W)

        # Sources
        tk.Label(root, text="Sources (files or folders):").pack()
        self.sources_list = tk.Listbox(root, height=5, selectmode=tk.MULTIPLE)
        self.sources_list.pack(fill=tk.X)
        frame_sources = tk.Frame(root)
        frame_sources.pack()
        tk.Button(frame_sources, text="Add File(s)", command=self.add_files).pack(side=tk.LEFT)
        tk.Button(frame_sources, text="Add Folder", command=self.add_folder).pack(side=tk.LEFT)
        tk.Button(frame_sources, text="Remove Selected", command=self.remove_sources).pack(side=tk.LEFT)

        # Destinations
        tk.Label(root, text="Destinations (parent folders):").pack()
        self.dests_list = tk.Listbox(root, height=5, selectmode=tk.MULTIPLE)
        self.dests_list.pack(fill=tk.X)
        frame_dests = tk.Frame(root)
        frame_dests.pack()
        tk.Button(frame_dests, text="Add Destination Folder", command=self.add_dest).pack(side=tk.LEFT)
        tk.Button(frame_dests, text="Remove Selected", command=self.remove_dests).pack(side=tk.LEFT)

        # Excludes
        tk.Label(root, text="Excludes (comma-separated patterns, e.g., *.tmp,temp_folder):").pack()
        self.excludes_entry = tk.Entry(root)
        self.excludes_entry.pack(fill=tk.X)

        # Overwrite
        self.overwrite_var = tk.IntVar(value=1)
        tk.Checkbutton(root, text="Overwrite existing files", variable=self.overwrite_var).pack()

        # Status
        self.status_label = tk.Label(root, text="")
        self.status_label.pack()
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack()

        # Buttons
        frame_buttons = tk.Frame(root)
        frame_buttons.pack()
        tk.Button(frame_buttons, text="Start Copy", command=self.start_copy).pack(side=tk.LEFT)
        tk.Button(frame_buttons, text="Cancel", command=self.cancel_copy).pack(side=tk.LEFT)

        # Queue for progress updates
        self.q = queue.Queue()
        self.copied = 0
        self.start_time = None
        self.running = False

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select Files", filetypes=[("All", "*.*")])
        for path in paths:
            self.sources_list.insert(tk.END, path)

    def add_folder(self):
        path = filedialog.askdirectory(title="Select Folder")
        if path:
            self.sources_list.insert(tk.END, path)

    def add_dest(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.dests_list.insert(tk.END, path)

    def remove_sources(self):
        selected = self.sources_list.curselection()
        for idx in reversed(selected):
            self.sources_list.delete(idx)

    def remove_dests(self):
        selected = self.dests_list.curselection()
        for idx in reversed(selected):
            self.dests_list.delete(idx)

    def start_copy(self):
        sources = list(self.sources_list.get(0, tk.END))
        dests = list(self.dests_list.get(0, tk.END))
        mode = self.mode_var.get()
        excludes = [p.strip() for p in self.excludes_entry.get().split(',') if p.strip()]
        overwrite = bool(self.overwrite_var.get())

        if not sources or not dests:
            messagebox.showerror("Error", "Please add at least one source and one destination.")
            return

        if mode == "pairwise" and len(sources) != len(dests):
            messagebox.showerror("Error", "Number of sources and destinations must match for pairwise mode.")
            return

        self.progress['value'] = 0
        self.status_label['text'] = "Preparing..."
        self.copied = 0
        self.running = True
        self.root.after(100, self.update_progress)

        thread = threading.Thread(target=self.do_copy, args=(sources, dests, mode, excludes, overwrite))
        thread.start()

    def cancel_copy(self):
        self.running = False
        self.status_label['text'] = "Cancelling... (may take a moment)"

    def do_copy(self, sources, dests, mode, excludes, overwrite):
        all_tasks = []
        dir_set = set()

        def process_source_dest(source, dest):
            if not os.path.exists(source):
                return  # Skip invalid sources

            base_name = os.path.basename(source)
            target_base = os.path.join(dest, base_name)

            if os.path.isfile(source):
                if any(fnmatch.fnmatch(base_name, exc) for exc in excludes):
                    return
                target = target_base
                if not overwrite and os.path.exists(target):
                    return
                dir_set.add(os.path.dirname(target))
                all_tasks.append((source, target))
            else:  # Directory
                for root, dirs, files in os.walk(source):
                    # Filter dirs
                    dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, exc) for exc in excludes)]

                    rel_root = os.path.relpath(root, source)
                    target_root = os.path.join(target_base, rel_root)

                    for f in files:
                        if any(fnmatch.fnmatch(f, exc) for exc in excludes):
                            continue
                        src_f = os.path.join(root, f)
                        dest_f = os.path.join(target_root, f)
                        if not overwrite and os.path.exists(dest_f):
                            continue
                        dir_set.add(os.path.dirname(dest_f))
                        all_tasks.append((src_f, dest_f))

        if mode == "cross":
            for dest in dests:
                for source in sources:
                    process_source_dest(source, dest)
        elif mode == "pairwise":
            for i in range(len(sources)):
                process_source_dest(sources[i], dests[i])

        if not all_tasks:
            self.q.put("done")
            return

        # Create all directories first to avoid race conditions
        for d in dir_set:
            os.makedirs(d, exist_ok=True)

        total = len(all_tasks)
        self.q.put(("max", total))  # Set max progress

        self.start_time = time.time()

        try:
            with Pool(processes=cpu_count()) as pool:
                for _ in pool.imap_unordered(copy_func, all_tasks):
                    if not self.running:
                        break
                    self.q.put(1)  # Increment progress
        except Exception as e:
            self.q.put(("error", str(e)))
        finally:
            self.q.put("done")

    def update_progress(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if isinstance(msg, tuple):
                    if msg[0] == "max":
                        self.progress['maximum'] = msg[1]
                    elif msg[0] == "error":
                        messagebox.showerror("Error", msg[1])
                        self.running = False
                elif msg == 1:
                    self.copied += 1
                    self.progress['value'] = self.copied
                    elapsed = time.time() - self.start_time
                    if elapsed > 0 and self.copied > 0:
                        speed = self.copied / elapsed
                        eta = (self.progress['maximum'] - self.copied) / speed if speed > 0 else 0
                        self.status_label['text'] = f"Copied {self.copied}/{self.progress['maximum']} | Speed: {speed:.2f} files/sec | ETA: {eta:.0f}s"
                elif msg == "done":
                    self.status_label['text'] = "Copy completed!" if self.running else "Copy cancelled."
                    messagebox.showinfo("Done", "Copy operation completed." if self.running else "Copy cancelled.")
                    self.running = False
                    return
        except queue.Empty:
            pass

        if self.running or not self.q.empty():
            self.root.after(100, self.update_progress)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):  # For pyinstaller or similar
        multiprocessing.freeze_support()
    root = tk.Tk()
    app = AdvancedCopyApp(root)
    root.mainloop()
