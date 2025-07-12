from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QFormLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.config import Settings


class IceAdapterVersionSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Tool Versions")
        self.setFixedSize(300, 150)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        notice = (
            "Leave blank to use latest. <b>HEED:</b> be careful with leading 'v' "
            "-- it may or may not be present in release tag. Add it if needed."
        )
        notice_label = QLabel(notice)
        notice_label.setWordWrap(True)
        layout.addWidget(notice_label)
        self.javaAdapterEdit = QLineEdit()
        self.javaAdapterEdit.setPlaceholderText("e.g., 3.3.12")
        self.javaAdapterEdit.setText(Settings.get("iceadapter/java_version", ""))
        self.goAdapterEdit = QLineEdit()
        self.goAdapterEdit.setPlaceholderText("e.g., 0.1.6")
        self.goAdapterEdit.setText(Settings.get("iceadapter/go_version", ""))

        form_layout.addRow("<b>Java ICE Adapter Version:</b>", self.javaAdapterEdit)
        form_layout.addRow("<b>Go (pioneer) ICE Adapter Version:</b>", self.goAdapterEdit)

        button_layout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.cancelButton = QPushButton("Cancel")

        self.okButton.clicked.connect(self.save_and_accept)
        self.cancelButton.clicked.connect(self.reject)

        button_layout.addWidget(self.okButton)
        button_layout.addWidget(self.cancelButton)

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_and_accept(self) -> None:
        Settings.set("iceadapter/java_version", self.javaAdapterEdit.text())
        Settings.set("iceadapter/go_version", self.goAdapterEdit.text())
        self.accept()
