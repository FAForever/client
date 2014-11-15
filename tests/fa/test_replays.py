import urllib
import py

from os.path import join

REPLAY_v0 = "2712924.scfareplay"
REPLAY_v1 = "2712924.fafreplay_old"
REPLAY_v2 = "2712924.fafreplay_new"
REPLAY_v2_OUT = "2712924.scfareplay_new"

tmpdir = str(py.test.ensuretemp(__name__))

urllib.urlretrieve ("http://content.faforever.com/faf/vault/replay_vault/replay.php?id=2712924",
                    join(tmpdir, REPLAY_v1))

from PyQt4.QtCore import *

import zlib, base64

from fa.FAFReplayReader import FAFReplayReader
from fa.FAFReplayWriter import FAFReplayWriter

# Prepare Old .scfareplay reference
with open(join(tmpdir, REPLAY_v1), "rb") as fv1:
    fv1.readline()

    replay_data = zlib.decompress( base64.b64decode( fv1.read() )[4:] )

    with open(join(tmpdir, REPLAY_v0), "wb") as fv0:
        fv0.write(replay_data)

def fcmp(fileA, fileB):
    with open(fileA, "rb") as fa:
        with open(fileB, "rb") as fb:
            da = fa.read(512)
            db = fb.read(512)
            while da:
                assert db
                assert da == db
                da = fa.read(512)
                db = fb.read(512)

def test_FAFReplay(qtbot):

    # Write a v2 replay
    f = QFile(join(tmpdir, REPLAY_v2))
    f.open(QFile.WriteOnly)

    writer = FAFReplayWriter(f)

    writer.writeHeader({'name':'banana'})

    writer.write(replay_data[:1024])
    writer.write(replay_data[1024:2048])
    writer.write(replay_data[2048:])

    writer.close()
    f.close()

    f = QFile(join(tmpdir, REPLAY_v2))
    f.open(QFile.ReadOnly)

    reader = FAFReplayReader(f)

    fout = QFile(join(tmpdir, REPLAY_v2_OUT))
    fout.open(QFile.WriteOnly)

    data = reader.read(512)

    assert reader.header == {'name':'banana'}

    while data:
        fout.write(data)
        data = reader.read(512)

    reader.close()
    fout.close()

    fcmp(join(tmpdir, REPLAY_v0), join(tmpdir, REPLAY_v2_OUT))

