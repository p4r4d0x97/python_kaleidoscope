import tkinter as tk
from tkinter import filedialog, messagebox, ttk  # Added ttk for progress bar
from pynput import keyboard, mouse
import keyboard as kb  # For Esc and F9 key detection
import time
import threading
import pickle
import os

# Global variables
recorded_actions = []
recording = False
replaying = False
start_time = 0
keyboard_listener = None
mouse_listener = None
current_pressed = set()
speed_factor = 1.0  # Default speed
loop_count = 1  # Default loop once
action_log = []  # Store log messages for GUI

# Hotkeys
STOP_HOTKEY = 'esc'  # Esc key to stop recording
PAUSE_HOTKEY = 'f9'  # F9 key to pause (stop) replay


def on_press(key):
    global recording
    current_pressed.add(key)
    if not recording:
        return
    timestamp = time.time() - start_time
    recorded_actions.append(('key_press', key, timestamp))
    # Log action
    action_log.append(f"Pressed key '{key}' at {timestamp:.2f}s")
    update_action_log_display()


def on_release(key):
    global recording
    if key in current_pressed:
        current_pressed.remove(key)
    if not recording:
        return
    timestamp = time.time() - start_time
    recorded_actions.append(('key_release', key, timestamp))
    # Log action
    action_log.append(f"Released key '{key}' at {timestamp:.2f}s")
    update_action_log_display()


def on_move(x, y):
    global recording
    if recording:
        timestamp = time.time() - start_time
        recorded_actions.append(('mouse_move', (x, y), timestamp))
        # Log action
        action_log.append(f"Moved mouse to ({x}, {y}) at {timestamp:.2f}s")
        update_action_log_display()


def on_click(x, y, button, pressed):
    global recording
    if recording:
        timestamp = time.time() - start_time
        action = 'mouse_press' if pressed else 'mouse_release'
        recorded_actions.append((action, (button, x, y), timestamp))
        # Log action
        action_log.append(f"{'Pressed' if pressed else 'Released'} mouse {button} at ({x}, {y}) at {timestamp:.2f}s")
        update_action_log_display()


def on_scroll(x, y, dx, dy):
    global recording
    if recording:
        timestamp = time.time() - start_time
        recorded_actions.append(('mouse_scroll', (dx, dy), timestamp))
        # Log action
        action_log.append(f"Scrolled mouse ({dx}, {dy}) at ({x}, {y}) at {timestamp:.2f}s")
        update_action_log_display()


def update_action_log_display():
    # Display last 5 actions to avoid clutter
    log_text = "\n".join(action_log[-5:])  # Show last 5 actions
    action_log_text.delete(1.0, tk.END)
    action_log_text.insert(tk.END, log_text)


def start_recording():
    global recording, start_time, recorded_actions, keyboard_listener, mouse_listener, action_log
    if recording:
        messagebox.showinfo("Info", "Already recording!")
        return
    if replaying:
        messagebox.showinfo("Info", "Cannot record while replaying!")
        return
    recorded_actions = []
    action_log = []  # Clear action log
    action_log_text.delete(1.0, tk.END)  # Clear text area
    current_pressed.clear()
    recording = True
    start_time = time.time()
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    keyboard_listener.start()
    mouse_listener.start()
    status_label.config(text="Recording... Press Esc to stop.")
    print("Recording started. Press Esc to stop.")  # Debug
    # Register Esc key for stopping
    kb.add_hotkey(STOP_HOTKEY, stop_recording)


def stop_recording():
    global recording, keyboard_listener, mouse_listener
    if not recording:
        return
    recording = False
    if keyboard_listener:
        keyboard_listener.stop()
    if mouse_listener:
        mouse_listener.stop()
    kb.remove_hotkey(STOP_HOTKEY)
    status_label.config(text="Recording stopped. Actions recorded: {}".format(len(recorded_actions)))
    print("Recording stopped.")  # Debug


def pause_replay():
    global replaying
    if replaying:
        replaying = False  # Stop the replay
        status_label.config(text="Replay paused. Click Replay to restart.")
        progress_bar["value"] = 0  # Reset progress bar
        print("Replay paused by F9.")  # Debug


def replay():
    global replaying
    if recording:
        messagebox.showinfo("Info", "Cannot replay while recording.")
        return
    if not recorded_actions:
        messagebox.showinfo("Info", "No actions recorded to replay.")
        return
    replaying = True
    # Register F9 key for pausing replay
    try:
        kb.add_hotkey(PAUSE_HOTKEY, pause_replay)
        print("F9 hotkey registered for pause.")  # Debug
    except Exception as e:
        print(f"Error registering F9 hotkey: {e}")  # Debug

    keyboard_controller = keyboard.Controller()
    mouse_controller = mouse.Controller()
    status_label.config(text="Replaying... Press F9 to pause.")
    progress_bar["value"] = 0  # Reset progress bar
    root.update()  # Ensure GUI updates

    total_actions = len(recorded_actions) * loop_count
    current_action = 0

    for i in range(loop_count):
        prev_time = 0
        for action, data, timestamp in recorded_actions:
            if not replaying:  # Exit if paused
                break
            sleep_time = (timestamp - prev_time) * speed_factor
            if sleep_time > 0:
                time.sleep(sleep_time)
            prev_time = timestamp
            if action == 'key_press':
                keyboard_controller.press(data)
            elif action == 'key_release':
                keyboard_controller.release(data)
            elif action == 'mouse_move':
                x, y = data
                mouse_controller.position = (x, y)
            elif action == 'mouse_press':
                button, x, y = data
                mouse_controller.position = (x, y)
                mouse_controller.press(button)
            elif action == 'mouse_release':
                button, x, y = data
                mouse_controller.position = (x, y)
                mouse_controller.release(button)
            elif action == 'mouse_scroll':
                dx, dy = data
                mouse_controller.scroll(dx, dy)
            current_action += 1
            # Update progress bar
            progress = (current_action / total_actions) * 100
            progress_bar["value"] = progress
            root.update()  # Update GUI for progress bar
        if not replaying:  # Exit loop if paused
            break

    replaying = False
    try:
        kb.remove_hotkey(PAUSE_HOTKEY)
        print("F9 hotkey unregistered.")  # Debug
    except Exception as e:
        print(f"Error unregistering F9 hotkey: {e}")  # Debug
    status_label.config(text="Replay finished. Click Replay to restart.")
    progress_bar["value"] = 0  # Reset progress bar
    print("Replay finished.")  # Debug


def save_macro():
    if not recorded_actions:
        messagebox.showinfo("Info", "No actions to save.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".pkl", filetypes=[("Pickle files", "*.pkl")])
    if file_path:
        with open(file_path, 'wb') as f:
            pickle.dump(recorded_actions, f)
        messagebox.showinfo("Info", "Macro saved successfully.")


def load_macro():
    global recorded_actions
    file_path = filedialog.askopenfilename(filetypes=[("Pickle files", "*.pkl")])
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            recorded_actions = pickle.load(f)
        status_label.config(text="Macro loaded. Actions: {}".format(len(recorded_actions)))


def update_speed():
    global speed_factor
    try:
        speed_factor = float(speed_entry.get())
        if speed_factor <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Invalid speed factor. Must be positive number.")
        speed_entry.delete(0, tk.END)
        speed_entry.insert(0, "1.0")


def update_loops():
    global loop_count
    try:
        loop_count = int(loop_entry.get())
        if loop_count < 1:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Invalid loop count. Must be positive integer.")
        loop_entry.delete(0, tk.END)
        loop_entry.insert(0, "1")


# GUI setup
root = tk.Tk()
root.title("Keyboard and Mouse Macro Recorder")
root.geometry("400x480")  # Increased height for progress bar

status_label = tk.Label(root, text="Ready", padx=10, pady=10)
status_label.pack()

btn_record = tk.Button(root, text="Start Recording", command=start_recording)
btn_record.pack(pady=5)

btn_replay = tk.Button(root, text="Replay", command=lambda: threading.Thread(target=replay, daemon=True).start())
btn_replay.pack(pady=5)

btn_save = tk.Button(root, text="Save Macro", command=save_macro)
btn_save.pack(pady=5)

btn_load = tk.Button(root, text="Load Macro", command=load_macro)
btn_load.pack(pady=5)

# Speed and loop controls
tk.Label(root, text="Speed Factor (1.0 default, <1 faster, >1 slower):").pack()
speed_entry = tk.Entry(root)
speed_entry.insert(0, "1.0")
speed_entry.pack()
btn_update_speed = tk.Button(root, text="Update Speed", command=update_speed)
btn_update_speed.pack(pady=5)

tk.Label(root, text="Loop Count (1 default):").pack()
loop_entry = tk.Entry(root)
loop_entry.insert(0, "1")
loop_entry.pack()
btn_update_loops = tk.Button(root, text="Update Loops", command=update_loops)
btn_update_loops.pack(pady=5)

# Progress bar
tk.Label(root, text="Replay Progress:").pack()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=5)

# Action log display
tk.Label(root, text="Recorded Actions (Last 5):").pack()
action_log_text = tk.Text(root, height=5, width=50, wrap=tk.WORD)
action_log_text.pack(pady=5)

# Run GUI
root.mainloop()
