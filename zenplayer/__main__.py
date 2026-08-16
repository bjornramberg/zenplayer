import argparse
import faulthandler
import os
import time

from zenplayer import __version__, diagnostics, nonblocking_output
from zenplayer.app import ZenPlayer


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminal YouTube Music client")
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.parse_args()

    stack_log = open("/tmp/zenplayer-stack.log", "w")
    faulthandler.dump_traceback_later(10, repeat=True, file=stack_log)
    nonblocking_output.install()
    diagnostics.start()
    t0 = time.monotonic()
    app = ZenPlayer()
    app.run()
    diagnostics.log_line("run returned after %.3fs" % (time.monotonic() - t0))
    stack_log.close()
    diagnostics.log_line("main returned (interpreter shutdown follows)")


if __name__ == "__main__":
    main()
