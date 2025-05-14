DARK_MODE = """
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    color: #ffffff;
}

/* ComboBox Styling */
QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
    color: #ffffff;
}

QComboBox:hover {
    background-color: #444444;
    border-color: #666666;
}

QComboBox:focus {
    border-color: #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: url("CLASSIC Data/graphics/arrow-down.svg");
    width: 12px;
    height: 12px;
}

QComboBox:disabled {
    background-color: #2b2b2b;
    color: #666666;
}

/* ScrollBar Styling */
QScrollBar:vertical {
    background-color: #202020;
    width: 14px;
    border: none;
    border-radius: 7px;
    margin: 0;
}

QScrollBar::groove:vertical {
    background-color: #202020;
    border: none;
    border-radius: 7px;
}

QScrollBar::handle:vertical {
    background-color: #686868;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7f7f7f;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: #202020;
    border: none;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #202020;
    height: 14px;
    border: none;
    border-radius: 7px;
    margin: 0;
}

QScrollBar::groove:horizontal {
    background-color: #202020;
    border: none;
    border-radius: 7px;
}

QScrollBar::handle:horizontal {
    background-color: #686868;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #7f7f7f;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: #202020;
    border: none;
    width: 0px;
}

QScrollBar::corner {
    background: #202020;
}

/* Tab Widget Styling */
QTabWidget::pane {
    border: 1px solid #444444;
}

QTabBar::tab {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    color: #ffffff;
    padding: 5px;
}

QTabBar::tab:selected {
    background-color: #2b2b2b;
    color: #ffffff;
}

/* Button Styling */
QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    color: #ffffff;
    padding: 5px;
}

QPushButton:hover {
    background-color: #444444;
}

QPushButton:pressed {
    background-color: #222222;
}

/* Label Styling */
QLabel {
    color: #ffffff;
}
    """
