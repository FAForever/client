import signal
from PyQt4.QtCore import QCoreApplication, QTimer

from connectivity import QTurnClient

if __name__ == '__main__':
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    def sigint_handler(*args):
        QCoreApplication.quit()
    print("Testing turnclient")
    app = QCoreApplication([])
    timer = QTimer()
    signal.signal(signal.SIGINT, sigint_handler)
    timer.start(500)
    timer.timeout.connect(lambda: None)
    c = QTurnClient()
    c.run()
    app.exec_()
