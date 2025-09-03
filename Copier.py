import tkinter as tk
from tkinter import filedialog, messagebox
import shutil
import os
import threading
import queue
from datetime import datetime
import time

class FileCopierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File/Folder Copier")
        self.root.geometry("800x600")
        
        # State variables
        self.copy_thread = None
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.queue = queue.Queue()
        self.is_paused = False
        
        # GUI Elements
        self.create_widgets()
        
        # Update progress periodically
        self.root.after(100, self.update_progress)

    def create_widgets(self):
        # Source Selection
        tk.Label(self.root, text="Source(s):").pack(pady=5)
        self.source_listbox = tk.Listbox(self.root, height=5, selectmode=tk.MULTIPLE)
        self.source_listbox.pack(fill=tk.X, padx=10)
        tk.Button(self.root, text="Add Source", command=self.add_source).pack()
        
        # Destination Selection
        tk.Label(self.root, text="Destination(s):").pack(pady=5)
        self.dest_listbox = tk.Listbox(self.root, height=5, selectmode=tk.MULTIPLE)
        self.dest_listbox.pack(fill=tk.X, padx=10)
        tk.Button(self.root, text="Add Destination", command=self.add_destination).pack()
        
        # Exclusions
        tk.Label(self.root, text="Exclude (comma-separated names):").pack(pady=5)
        self.exclude_entry = tk.Entry(self.root)
        self.exclude_entry.pack(fill=tk.X, padx=10)
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # Log Window
        tk.Label(self.root, text="Log:").pack(pady=5)
        self.log_text = tk.Text(self.root, height=10, state='disabled')
        self.log_text.pack(fill=tk.BOTH, padx=10, expand=True)
        
        # Control Buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=10)
        tk.Button(self.button_frame, text="Start Copy", command=self.start_copy).pack(side=tk.LEFT, padx=5)
        self.pause_button = tk.Button(self.button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Stop", command=self.stop_copy).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)

    def add_source(self):
        paths = filedialog.askopenfilenames() or filedialog.askdirectory()
        if isinstance(paths, str):
            if paths and paths not in self.source_listbox.get(0, tk.END):
                self.source_listbox.insert(tk.END, paths)
        else:
            for path in paths:
                if path and path not in self.source_listbox.get(0, tk.END):
                    self.source_listbox.insert(tk.END, path)

    def add_destination(self):
        path = filedialog.askdirectory()
        if path and path not in self.dest_listbox.get(0, tk.END):
            self.dest_listbox.insert(tk.END, path)

    def log_message(self, message):
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def toggle_pause(self):
        if self.is_paused:
            self.pause_event.set()
            self.pause_button.config(text="Pause")
            self.log_message("Resumed copying")
        else:
            self.pause_event.clear()
            self.pause_button.config(text="Resume")
            self.log_message("Paused copying")
        self.is_paused = not self.is_paused

    def stop_copy(self):
        self.stop_event.set()
        self.pause_event.set()  # Resume if paused to allow thread to exit
        self.log_message("Stopping copy operation")

    def update_progress(self):
        try:
            while True:
                progress, message = self.queue.get_nowait()
                self.progress_var.set(progress)
                if message:
                    self.log_message(message)
        except queue.Empty:
            pass
        self.root.after(100, self.update_progress)

    def copy_files(self):
        sources = self.source_listbox.get(0, tk.END)
        destinations = self.dest_listbox.get(0, tk.END)
        excludes = [x.strip() for x in self.exclude_entry.get().split(",") if x.strip()]
        
        if not sources or not destinations:
            self.log_message("Error: Please select at least one source and destination")
            return
        
        total_items = len(sources) * len(destinations)
        items_processed = 0
        
        self.stop_event.clear()
        self.pause_event.set()
        
        for src in sources:
            for dest in destinations:
                if self.stop_event.is_set():
                    self.log_message("Copy operation stopped")
                    break
                
                try:
                    src_name = os.path.basename(src)
                    if src_name in excludes:
                        self.log_message(f"Skipping excluded item: {src_name}")
                        items_processed += 1
                        self.queue.put((items_processed / total_items * 100, None))
                        continue
                    
                    dest_path = os.path.join(dest, src_name)
                    
                    self.pause_event.wait()  # Pause if event is unset
                    
                    if os.path.isfile(src):
                        shutil.copy2(src, dest_path)
                        self.log_message(f"Copied file: {src} to {dest_path}")
                    else:
                        shutil.copytree(src, dest_path, ignore=shutil.ignore_patterns(*excludes), dirs_exist_ok=True)
                        self.log_message(f"Copied folder: {src} to {dest_path}")
                    
                    items_processed += 1
                    self.queue.put((items_processed / total_items * 100, None))
                
                except Exception as e:
                    self.log_message(f"Error copying {src} to {dest}: {str(e)}")
                    items_processed += 1
                    self.queue.put((items_processed / total_items * 100, None))
            
            if self.stop_event.is_set():
                break
        
        self.queue.put((100, "Copy operation completed"))

    def start_copy(self):
        if self.copy_thread and self.copy_thread.is_alive():
            messagebox.showwarning("Warning", "A copy operation is already running!")
            return
        
        self.copy_thread = threading.Thread(target=self.copy_files)
        self.copy_thread.daemon = True
        self.copy_thread.start()
        self.log_message("Started copy operation")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileCopierApp(root)
    root.mainloop()
