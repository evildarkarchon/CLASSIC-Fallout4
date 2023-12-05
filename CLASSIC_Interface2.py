# CLASSIC GUI WITH PySide6 (NOW WORKS WITH 3.11!)
import os
import sys
import time
import platform
import subprocess
import multiprocessing
import soundfile as sfile
import sounddevice as sdev
# sfile and sdev need Numpy
import CLASSIC_Main as CMain
import CLASSIC_ScanGame as CGame
import CLASSIC_ScanLogs as CLogs
from pathlib import Path
from functools import partial
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QUrl, QTimer, Slot
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon
from PySide6.QtWidgets import QDialog, QFileDialog, QSizePolicy, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QMainWindow

CMain.configure_logging()

# FONTS CONFIG
bold_11 = QtGui.QFont()
bold_11.setPointSize(11)
bold_11.setBold(True)
normal_11 = QtGui.QFont()
normal_11.setPointSize(11)
bold_09 = QtGui.QFont()
bold_09.setPointSize(9)
bold_09.setBold(True)



def create_hbox_layout(widgets):
    hbox = QHBoxLayout()
    for widget in widgets:
        hbox.addWidget(widget)
    return hbox
def create_vbox_layout(widgets):
    vbox = QVBoxLayout()
    for widget in widgets:
        vbox.addWidget(widget)
    return vbox
def create_grid_layout(widgets, cols):
    grid = QtWidgets.QGridLayout()
    for i, widget in enumerate(widgets):
        grid.addWidget(widget, i // cols, i % cols)
    return grid

# ================================================
# DEFINE WINDOW ELEMENT TEMPLATES HERE
# ================================================
def custom_line_box(parent, geometry, object_name, text):
    line_edit = QtWidgets.QLineEdit(parent)
    line_edit.setGeometry(geometry)
    line_edit.setObjectName(object_name)
    line_edit.setText(text)
    return line_edit


def custom_push_button(parent, geometry, object_name, text, font, tooltip="", callback=None):
    button = QtWidgets.QPushButton(parent)
    button.setObjectName(object_name)
    button.setGeometry(geometry)
    button.setToolTip(tooltip)
    button.setText(text)
    button.setFont(font)
    button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    button.setStyleSheet("color: white; background: rgba(10, 10, 10, 0.75); border-radius: 10px; border : 1px solid white; font-family: Yu Gothic")
    if callback:
        button.clicked.connect(callback)
    return button


def custom_frame(parent, geometry, frame_shape, frame_shadow, object_name):
    frame = QtWidgets.QFrame(parent)
    frame.setGeometry(geometry)
    frame.setFrameShape(frame_shape)
    frame.setFrameShadow(frame_shadow)
    frame.setObjectName(object_name)
    return frame


def custom_label(parent, geometry, text, font, object_name):
    label = QtWidgets.QLabel(parent)
    label.setGeometry(geometry)
    label.setText(text)
    label.setFont(font)
    label.setObjectName(object_name)
    label.setStyleSheet("color: white; font-family: Yu Gothic")
    return label


def custom_popup_window(parent, title, text, height=250, callback=""):
    popup_window = QDialog(parent)
    popup_window.setWindowTitle(title)
    popup_window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    popup_window.setStyleSheet("color: white; background: rgba(10, 10, 10, 1); border : 1px solid black; font-size: 15px")
    popup_window.setGeometry(15, 300, 620, height)

    layout = QVBoxLayout()
    label = QLabel(text, popup_window)
    # label.setAlignment(Qt.AlignTop)
    label.setWordWrap(True)

    # Create a horizontal layout for buttons
    button_layout = QHBoxLayout()
    ok_button = QPushButton("OK")
    ok_button.setMinimumSize(100, 50)
    ok_button.setStyleSheet("color: black; background: rgb(45, 237, 138); font-size: 20px; font-weight: bold")

    close_button = QPushButton("Close")
    close_button.setMinimumSize(100, 50)
    close_button.setStyleSheet("color: black; background: rgb(240, 63, 40); font-size: 20px; font-weight: bold")

    # Connect button signals to actions
    if callback:
        ok_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(callback)))
    else:
        ok_button.clicked.connect(popup_window.accept)
    close_button.clicked.connect(popup_window.reject)

    # Add buttons to the horizontal layout
    button_layout.addWidget(ok_button)
    button_layout.addWidget(close_button)

    # Add widgets to the main layout
    layout.addWidget(label)
    layout.addLayout(button_layout)
    popup_window.setLayout(layout)
    return popup_window


def custom_text_box(parent, geometry, text):
    text_browser = QtWidgets.QTextBrowser(parent)
    text_browser.setGeometry(geometry)
    text_browser.setObjectName("text_browser")
    text_browser.setText(text)
    text_browser.setStyleSheet("color: white; background: rgba(10, 10, 10, 0.75); border-radius: 10px; border : 1px solid white; font-size: 15px")
    return text_browser


def custom_checkbox_widget(parent, pos_x=250, pos_y=250, size=25, check="", label_text="TEST LABEL"):
    checkbox_widget = QWidget(parent)
    checkbox_widget.setGeometry(pos_x, pos_y, 200, 50)
    layout = QHBoxLayout(checkbox_widget)

    # Create QLabel for image & text.
    image_label = QLabel()
    pixmap0 = QPixmap("CLASSIC Data/graphics/unchecked.png")
    pixmap1 = QPixmap("CLASSIC Data/graphics/checked.png")

    image_label.setPixmap(pixmap0)
    image_label.setFixedSize(size, size)
    text_label = QLabel(label_text)
    text_label.setStyleSheet("color: white; font-family: Yu Gothic")

    # Add image & text labels to layout.
    layout.addWidget(image_label)
    layout.addWidget(text_label)
    checkbox_widget.setLayout(layout)

    # Check assigned YAML setting.
    status = CMain.classic_settings(check)
    if status:
        image_label.setPixmap(pixmap1)
    else:
        image_label.setPixmap(pixmap0)

    # Toggle assigned YAML setting.
    def toggle_setting(_):
        nonlocal check
        # Toggle between images when label is clicked.
        if CMain.classic_settings(check):
            CMain.yaml_settings("CLASSIC Settings.yaml", f"CLASSIC_Settings.{check}", False)
            image_label.setPixmap(pixmap0)
        else:
            CMain.yaml_settings("CLASSIC Settings.yaml", f"CLASSIC_Settings.{check}", True)
            image_label.setPixmap(pixmap1)

    image_label.mousePressEvent = toggle_setting
    return checkbox_widget


def custom_hover_button(parent, geometry, object_name, text, font, tooltip="", callback=None):
    hover_button = QtWidgets.QPushButton(parent)
    hover_button.setObjectName(object_name)
    hover_button.setGeometry(geometry)
    hover_button.setToolTip(tooltip)
    hover_button.setText(text)
    hover_button.setFont(font)
    hover_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    hover_button.setStyleSheet("color: white; background: rgba(10, 10, 10, 0.75); border-radius: 10px; border : 1px solid white; font-family: Yu Gothic")
    if callback:
        hover_button.clicked.connect(callback)

    def enter_event(_):
        hover_button.setText("CHANGE GAME")

    def leave_event(_):
        hover_button.setText(text)

    hover_button.enterEvent = enter_event
    hover_button.leaveEvent = leave_event
    hover_button.setMouseTracking(True)
    return hover_button


def papyrus_worker(q, stop_event):
    while not stop_event.is_set():
        papyrus_result = CGame.papyrus_logging()
        q.put(papyrus_result)
        time.sleep(3)


def play_sound(sound_file):
    sound, samplerate = sfile.read(f"CLASSIC Data/sounds/{sound_file}")
    sdev.play(sound, samplerate)
    sdev.wait()

# ================================================
# CLASSIC MAIN WINDOW
# ================================================
class UiCLASSICMainWin(QMainWindow):
    super.__init__()
    def __init__(self):
        self.main_layout = QtWidgets.QVBoxLayout()