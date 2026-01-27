import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QLineEdit, QVBoxLayout, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from pygrabber.dshow_graph import FilterGraph


# ===================== CONFIG =====================

SAVE_DIR = r"C:\temp"

# ⚠️ PUT YOUR CAMERA NAMES HERE (order = layout order)
CAMERA_NAMES = [
    "USB Camera SN1234",
    "USB Camera SN5678",
]

EXIT_KEY = (Qt.Key_Q, Qt.ControlModifier | Qt.ShiftModifier)

# =================================================


class CameraThread(QThread):
    frame_ready = Signal(object)

    def __init__(self, device_name):
        super().__init__()
        self.device_name = device_name
        self.running = True
        self.last_frame = None

    def run(self):
        cap = cv2.VideoCapture(
            f"video={self.device_name}",
            cv2.CAP_DSHOW
        )

        if not cap.isOpened():
            print(f"[ERROR] Cannot open {self.device_name}")
            return

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.last_frame = frame
                self.frame_ready.emit(frame)
            time.sleep(0.01)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class CameraView(QLabel):
    def __init__(self):
        super().__init__()
        self.setScaledContents(True)
        self.setStyleSheet("background-color: black;")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        self.camera_threads = []
        self.camera_views = []

        cam_layout = QHBoxLayout()
        cam_layout.setSpacing(0)
        cam_layout.setContentsMargins(0, 0, 0, 0)

        for name in CAMERA_NAMES:
            view = CameraView()
            cam_layout.addWidget(view)
            self.camera_views.append(view)

            thread = CameraThread(name)
            thread.frame_ready.connect(
                lambda frame, v=view: self.update_view(v, frame)
            )
            self.camera_threads.append(thread)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Scan code here")
        self.input.setFixedHeight(40)

        self.scan_btn = QPushButton("SCAN")
        self.scan_btn.setFixedHeight(40)
        self.scan_btn.clicked.connect(self.scan)

        bottom = QHBoxLayout()
        bottom.addWidget(self.input)
        bottom.addWidget(self.scan_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(cam_layout)
        layout.addLayout(bottom)

        for t in self.camera_threads:
            t.start()

    def update_view(self, view, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        view.setPixmap(QPixmap.fromImage(img))

    def scan(self):
        name = self.input.text().strip()
        if not name:
            self.popup("Error", "No scan text entered", QMessageBox.Warning)
            return

        try:
            os.makedirs(SAVE_DIR, exist_ok=True)

            frames = []
            for t in self.camera_threads:
                if t.last_frame is not None:
                    frames.append(t.last_frame.copy())

            if not frames:
                raise RuntimeError("No camera frames available")

            stitched = np.hstack(frames)

            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            cv2.putText(
                stitched,
                timestamp,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            filename = self.unique_filename(name)
            path = os.path.join(SAVE_DIR, filename)

            if not cv2.imwrite(path, stitched):
                raise IOError("Failed to save image")

            self.popup("Success", f"Saved:\n{path}", QMessageBox.Information)
            self.input.clear()

        except PermissionError:
            self.popup("Error", "No access to save location", QMessageBox.Critical)
        except OSError as e:
            self.popup("Error", f"OS Error:\n{e}", QMessageBox.Critical)
        except Exception as e:
            self.popup("Error", str(e), QMessageBox.Critical)

    def unique_filename(self, base):
        i = 0
        while True:
            suffix = f"_{i}" if i else ""
            name = f"{base}{suffix}.jpg"
            if not os.path.exists(os.path.join(SAVE_DIR, name)):
                return name
            i += 1

    def popup(self, title, text, icon):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.exec()

    def keyPressEvent(self, event):
        if (
            event.key() == EXIT_KEY[0]
            and event.modifiers() == EXIT_KEY[1]
        ):
            self.close()

    def closeEvent(self, event):
        for t in self.camera_threads:
            t.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    sys.exit(app.exec())
