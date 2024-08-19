
import sys
import os
import platform
import sys
import subprocess
import asyncio
import logging
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QUrl, QTimer, QCoreApplication, QSize
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon, QPainter, QColor, QFontMetrics, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                               QScrollArea, QSizePolicy, QStackedWidget, QDialog, QPushButton, QLabel,
                               QGraphicsView, QGraphicsScene, QGraphicsProxyWidget, QLineEdit, QTextEdit,
                               QStackedLayout, QGridLayout, QTabBar, QStyleOptionTab, QStyle, QSizePolicy)

import CLASSIC_Main as CMain
import CLASSIC_ScanGame as CGame
import CLASSIC_ScanLogs as CLogs

logging.basicConfig(level=logging.DEBUG)

class StaticTextButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.full_text = text
        self.setStyleSheet("""
            QPushButton {
                color: white;
                background: rgba(10, 10, 10, 0.90);
                border-radius: 0px;
                border: 2px dashed white;
            }
            QPushButton:checked {
                background: rgba(25, 25, 25, 0.90);
                border: 2px solid white;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumWidth(100)  # Adjust as needed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the button background
        palette = self.palette()
        if self.isChecked():
            painter.fillRect(self.rect(), palette.color(QPalette.Button))
        else:
            painter.fillRect(self.rect(), palette.color(QPalette.Window))

        # Draw the text
        painter.setPen(palette.color(QPalette.ButtonText))
        font = self.font()
        font.setPointSize(self.calculate_font_size())
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.full_text)

    def calculate_font_size(self):
        width = self.width()
        height = self.height()
        return min(width // 10, height // 2, 15)  # Adjust these values as needed

    def sizeHint(self):
        return QSize(120, 40)  # Adjust as needed

class ResponsiveTabButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.full_text = text
        self.setStyleSheet("""
            QPushButton {
                text-align: center;
                padding: 5px;
                color: white;
                background: rgba(10, 10, 10, 0.90);
                border-radius: 0px;
                border: 2px dashed white;
                font-size: 15px;
            }
            QPushButton:checked {
                background: rgba(25, 25, 25, 0.90);
                border: 2px solid white;
            }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustText()

    def adjustText(self):
        metrics = QFontMetrics(self.font())
        available_width = self.width() - 10  # Subtract some padding
        text = metrics.elidedText(self.full_text, Qt.ElideRight, available_width)
        self.setText(text)

class CustomPopupWindow(QDialog):
    def __init__(self, parent, title, text, height=250, callback=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet("color: white; background: rgba(10, 10, 10, 1); border: 1px solid black; font-size: 15px")
        self.setGeometry(15, 300, 620, height)

        layout = QVBoxLayout(self)

        label = QLabel(text, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setMinimumSize(100, 50)
        ok_button.setStyleSheet("color: black; background: rgb(45, 237, 138); font-size: 20px; font-weight: bold")

        close_button = QPushButton("Close")
        close_button.setMinimumSize(100, 50)
        close_button.setStyleSheet("color: black; background: rgb(240, 63, 40); font-size: 20px; font-weight: bold")

        if callback:
            ok_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(callback)))
        else:
            ok_button.clicked.connect(self.accept)
        close_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

class ResizableMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Get the CLASSIC version using yaml_settings
        self.classic_version = CMain.yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Info.version")

        self.setWindowTitle(f"Crash Log Auto Scanner & Setup Integrity Checker | {self.classic_version}")
        self.setWindowIcon(QIcon("CLASSIC Data/graphics/CLASSIC.ico"))
        self.setStyleSheet("font-family: Yu Gothic; font-size: 13px")

        # Flag to track if update check has been performed
        self.update_check_performed = False
        self.is_uptodate = None

        # Create a central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create a stacked widget for tab content
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create tabs
        self.create_main_tab()
        self.create_backup_tab()

        # Add tab buttons
        self.tab_layout = QHBoxLayout()
        self.tab_main = self.create_tab_button("MAIN OPTIONS", True, self.switch_to_main_tab)
        self.tab_backups = self.create_tab_button("FILE BACKUP", False, self.switch_to_backup_tab)
        self.tab_game = self.create_tab_button("FALLOUT 4", False)
        self.tab_layout.addWidget(self.tab_main)
        self.tab_layout.addWidget(self.tab_backups)
        self.tab_layout.addWidget(self.tab_game)

        main_layout.insertLayout(0, self.tab_layout)

        self.setMinimumSize(550, 650)  # Set a minimum window size
        self.text_window.setMinimumHeight(200)  # Set a minimum height for the text window

        self.text_window.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                # Set the application-wide style
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: white;
                font-family: Yu Gothic;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                padding: 3px;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
            }
            QTabBar::tab {
                font-size: 14px;
            }
            @media (min-width: 800px) {
                QTabBar::tab {
                font-size: 16px;
            }
            @media (min-width: 1200px) {
                QTabBar::tab {
                font-size: 18px;
            }
        }
    }
        """)

        if CMain.classic_settings("Update Check"):
            QTimer.singleShot(0, lambda: self.perform_update_check())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_widgets()
        self.update()  # This will trigger a repaint of the buttons

    def adjust_widgets(self):
        # Adjust widget sizes based on window size
        window_width = self.width()
        window_height = self.height()

        # Adjust text window height
        text_window_height = int(window_height * 0.3)  # 30% of window height
        self.text_window.setFixedHeight(text_window_height)

        # Adjust button sizes
        button_width = int(window_width * 0.4)  # 40% of window width
        for button in self.findChildren(QPushButton):
            button.setFixedWidth(button_width)

    def create_tab_button(self, text, is_active, callback=None):
        button = StaticTextButton(text)
        button.setCheckable(True)
        button.setChecked(is_active)
        if callback:
            button.clicked.connect(callback)
        return button

    def perform_update_check(self):
        if not self.update_check_performed:
            QCoreApplication.instance().asyncio_event_loop.create_task(self.async_update_check())

    async def async_update_check(self):
        self.is_uptodate = await CMain.classic_update_check(quiet=True)
        self.update_check_performed = True
        if not self.is_uptodate:
            QTimer.singleShot(0, self.update_popup)

    def switch_to_main_tab(self):
        self.stacked_widget.setCurrentIndex(0)
        self.tab_main.setChecked(True)
        self.tab_backups.setChecked(False)
        self.tab_game.setChecked(False)

    def switch_to_backup_tab(self):
        self.stacked_widget.setCurrentIndex(1)
        self.tab_main.setChecked(False)
        self.tab_backups.setChecked(True)
        self.tab_game.setChecked(False)

    def create_main_tab(self):
        # Create a main widget for this tab
        main_widget = QWidget()
        main_layout = QGridLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create and add background image
        background_label = QLabel()
        background_pixmap = QPixmap("CLASSIC Data/graphics/background.png")
        background_label.setPixmap(background_pixmap)
        background_label.setScaledContents(True)
        main_layout.addWidget(background_label, 0, 0)

        # Create a widget to hold all the content
        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_TranslucentBackground)
        content_layout = QVBoxLayout(content_widget)
        content_widget.setStyleSheet("background-color: rgba(0, 0, 0, 128);")  # Semi-transparent black background
        main_layout.addWidget(content_widget, 0, 0)

        # Add other widgets to content_layout
        self.add_section(content_layout, "STAGING MODS FOLDER", self.create_browse_section)
        self.add_section(content_layout, "CUSTOM SCAN FOLDER", self.create_browse_section)

        # Main buttons
        button_layout = QHBoxLayout()
        self.add_main_button(button_layout, "SCAN CRASH LOGS", CLogs.crashlogs_scan)
        self.add_main_button(button_layout, "SCAN GAME FILES", self.game_files_scan)
        content_layout.addLayout(button_layout)

        # Settings checkboxes
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(QLabel("CLASSIC SETTINGS"))
        settings_layout.addLayout(self.create_checkbox_grid())
        content_layout.addLayout(settings_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        self.add_bottom_button(bottom_layout, "HELP", self.help_popup_main)
        self.add_bottom_button(bottom_layout, "EXIT", QtWidgets.QApplication.quit)
        content_layout.addLayout(bottom_layout)

        # Text window
        self.text_window = QTextEdit()
        self.text_window.setReadOnly(True)
        self.text_window.setStyleSheet("""
            background-color: rgba(45, 45, 45, 0.75);
            color: white;
            border: 1px solid #3d3d3d;
            border-radius: 5px;
            font-size: 15px;
        """)
        content_layout.addWidget(self.text_window)

        # Add stretch to push content to the top
        content_layout.addStretch(1)

        self.stacked_widget.addWidget(main_widget)

    def on_resize(self, event, view, scene, background_item):
        # Resize the view and scene to fit the new window size
        view.setFixedSize(event.size())
        scene.setSceneRect(0, 0, event.size().width(), event.size().height())

        # Scale the background to fit the new size
        scaled_background = self.background.scaled(event.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        background_item.setPixmap(scaled_background)

    def add_section(self, layout, title, content_func):
        layout.addWidget(QtWidgets.QLabel(title))
        layout.addLayout(content_func())

    def create_browse_section(self):
        layout = QHBoxLayout()
        line_edit = QtWidgets.QLineEdit()
        line_edit.setStyleSheet("color: black; background: white;")
        layout.addWidget(line_edit, 3)
        button = QtWidgets.QPushButton("Browse Folder")
        button.setStyleSheet("color: white; background: rgba(10, 10, 10, 0.75); border-radius: 10px; border: 1px solid white")
        layout.addWidget(button, 1)
        return layout

    def create_backup_tab(self):
        # Create a main widget for this tab
        backup_widget = QWidget()
        backup_layout = QGridLayout(backup_widget)
        backup_layout.setContentsMargins(0, 0, 0, 0)
        backup_layout.setSpacing(0)

        # Create and add background image
        background_label = QLabel()
        background_pixmap = QPixmap("CLASSIC Data/graphics/background.png")
        background_label.setPixmap(background_pixmap)
        background_label.setScaledContents(True)
        backup_layout.addWidget(background_label, 0, 0)

        # Create a widget to hold all the content
        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_TranslucentBackground)
        content_layout = QVBoxLayout(content_widget)
        backup_layout.addWidget(content_widget, 0, 0)

        # Add backup options
        self.add_backup_section(content_layout, "SCRIPT EXTENDER", "XSE")
        self.add_backup_section(content_layout, "RESHADE", "RESHADE")
        self.add_backup_section(content_layout, "VULKAN RENDERER", "VULKAN")
        self.add_backup_section(content_layout, "ENHANCED NATURAL BEAUTY ( ENB )", "ENB")

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        self.add_bottom_button(bottom_layout, "HELP", self.help_popup_backup)
        self.add_bottom_button(bottom_layout, "OPEN CLASSIC BACKUPS", self.open_backup_folder)
        self.add_bottom_button(bottom_layout, "EXIT", QtWidgets.QApplication.quit)
        content_layout.addLayout(bottom_layout)

        # Text window
        self.backup_text_window = QTextEdit()
        self.backup_text_window.setReadOnly(True)
        self.backup_text_window.setStyleSheet("""
            background-color: rgba(45, 45, 45, 0.75);
            color: white;
            border: 1px solid #3d3d3d;
            border-radius: 5px;
            font-size: 15px;
        """)
        content_layout.addWidget(self.backup_text_window)

        # Add stretch to push content to the top
        content_layout.addStretch(1)

        self.stacked_widget.addWidget(backup_widget)

    def add_backup_section(self, layout, title, identifier):
        section_layout = QVBoxLayout()

        label = QtWidgets.QLabel(title)
        label.setStyleSheet("color: white; font-weight: bold;")
        section_layout.addWidget(label)

        button_layout = QHBoxLayout()
        self.add_backup_button(button_layout, f"BACKUP {identifier}", lambda: self.manage_files(identifier, "BACKUP"))
        self.add_backup_button(button_layout, f"RESTORE {identifier}", lambda: self.manage_files(identifier, "RESTORE"))
        self.add_backup_button(button_layout, f"REMOVE {identifier}", lambda: self.manage_files(identifier, "REMOVE"))
        section_layout.addLayout(button_layout)

        layout.addLayout(section_layout)

    def add_backup_button(self, layout, text, callback):
        button = QtWidgets.QPushButton(text)
        button.setStyleSheet("""
            background-color: #4d4d4d;
            color: white;
            border: 1px solid #5d5d5d;
            padding: 5px;
            font-size: 13px;
        """)
        button.clicked.connect(callback)
        layout.addWidget(button)

    def manage_files(self, identifier, action):
        CGame.game_files_manage(f"Backup {identifier}", action)
        self.backup_text_window.append(f"{action} {identifier} operation completed.")

    def add_main_button(self, layout, text, callback):
        button = QtWidgets.QPushButton(text)
        button.setStyleSheet("color: black; background: rgba(250, 250, 250, 0.90); border-radius: 10px; border: 1px solid white; font-size: 17px")
        button.clicked.connect(callback)
        layout.addWidget(button)

    def create_checkbox_grid(self):
        grid = QtWidgets.QGridLayout()
        checkboxes = ["FCX MODE", "VR MODE", "SIMPLIFY LOGS", "SHOW FID VALUES", "UPDATE CHECK", "MOVE INVALID LOGS"]
        for i, text in enumerate(checkboxes):
            checkbox = QtWidgets.QCheckBox(text)
            checkbox.setStyleSheet("color: white")
            grid.addWidget(checkbox, i // 3, i % 3)
        return grid

    def add_bottom_button(self, layout, text, callback):
        button = QtWidgets.QPushButton(text)
        button.setStyleSheet("color: white; background: rgba(10, 10, 10, 0.75); border-radius: 10px; border: 1px solid white")
        button.clicked.connect(callback)
        layout.addWidget(button)

    def game_files_scan(self):
        print(CGame.game_combined_result())
        print(CGame.mods_combined_result())
        CGame.write_combined_results()

    def help_popup_main(self):
        help_popup_text = CMain.yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Interface.help_popup_main")
        popup = CustomPopupWindow(self, title="NEED HELP?", text=help_popup_text, height=450, callback="https://discord.com/invite/7ZZbrsGQh4")
        popup.exec()

    def help_popup_backup(self):
        help_popup_text = CMain.yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Interface.help_popup_backup")
        popup = CustomPopupWindow(self, title="NEED HELP?", text=help_popup_text, height=450, callback="https://discord.com/invite/7ZZbrsGQh4")
        popup.exec()

    def update_popup(self):
        update_popup_text = CMain.yaml_settings("CLASSIC Data/databases/CLASSIC Main.yaml", "CLASSIC_Interface.update_popup_text")
        if self.is_uptodate is None:
            popup = CustomPopupWindow(self, title="CLASSIC UPDATE", text="Update check has not been performed yet.")
        elif self.is_uptodate:
            popup = CustomPopupWindow(self, title="CLASSIC UPDATE", text="You have the latest version of CLASSIC!")
        else:
            popup = CustomPopupWindow(self, title="CLASSIC UPDATE", text=update_popup_text, callback="https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest")
        popup.exec()

    def open_backup_folder(self):
        backup_path = Path("CLASSIC Backup/Game Files").resolve()

        if not backup_path.exists():
            QtWidgets.QMessageBox.warning(self, "Folder Not Found", f"The backup folder does not exist: {backup_path}")
            return

        if platform.system() == "Windows":
            os.startfile(backup_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", backup_path])
        else:  # Linux and other Unix-like
            subprocess.run(["xdg-open", backup_path])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResizableMainWindow()
    window.show()
    sys.exit(app.exec())