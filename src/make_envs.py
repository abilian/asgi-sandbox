import sys
from pathlib import Path

import shelmet as sh

stdout = sys.stdout
stderr = sys.stderr

# Cinder
sh.mkdir("git", exist_ok=True)
with sh.cd("git"):
    if not Path("cinder").exists():
        sh.cmd("git", "clone", "https://github.com/facebookincubator/cinder.git").run()
    with sh.cd("cinder"):
        sh.cmd("./configure").run()
        sh.cmd("make", stdout=stdout, stderr=stderr).run()


# Pystone
