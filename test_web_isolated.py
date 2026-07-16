import sys
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView

class StandaloneNewsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FAF Newsfeed - Web-Only Test Harness")
        self.resize(1024, 768)

        # Main Layout container
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Embedded Chromium browser instance
        self.browser = QWebEngineView(self)
        self.browser.setUrl(QUrl("https://faforever.github.io/FAF-Newsfeed/"))
        
        layout.addWidget(self.browser)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StandaloneNewsWindow()
    window.show()
    sys.exit(app.exec_())