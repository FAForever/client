#! /usr/bin/env python3
import sys

print(sys.version)

import sip, pytest
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)
sip.setapi('QDate', 2)
sip.setapi('QDateTime', 2)
sip.setapi('QTextStream', 2)
sip.setapi('QTime', 2)
sip.setapi('QUrl', 2)


if __name__ == '__main__':
    print("pytest:", pytest.__file__)
    sys.exit(pytest.main(sys.argv[1:]))
