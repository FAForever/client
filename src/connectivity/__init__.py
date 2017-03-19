import logging

from PyQt5.QtCore import QObject

import util

from .qturnsocket import QTurnSocket
from .helper import ConnectivityHelper

logger = logging.getLogger(__name__)

class ConnectivityDialog(QObject):
    def __init__(self, connectivity):
        QObject.__init__(self)
        self.connectivity = connectivity
        self.dialog = util.loadUi('connectivity/connectivity.ui')
        self.dialog.runTestButton.clicked.connect(self.run_relay_test)

    def update_relay_info(self):
        if self.connectivity.relay_address:
            self.dialog.relay_test_label.setText("{}:{}".format(*self.connectivity.relay_address))

    def run_relay_test(self):
        self.dialog.runTestButton.setEnabled(False)

        self.connectivity.start_relay_test()
        self.connectivity.relay_bound.connect(self.update_relay_info)
        self.connectivity.relay_test_finished.connect(self.end)
        self.connectivity.relay_test_progress.connect(self.report_relay_test)

    def report_relay_test(self, text):
        self.dialog.relay_test_label.setText(text)

    def end(self):
        self.dialog.runTestButton.setEnabled(True)

    def exec_(self):
        self.dialog.test_result_label.setText(
                "State: {}. Resolved address: {}:{}".
                    format(self.connectivity.state, *self.connectivity.mapped_address)
        )
        self.dialog.exec_()
