#!/usr/bin/env python3

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import os

import yaml
from notion_client import Client

import apple
import builder

try:
    from yaml import CLoader as YamlLoader
except ImportError:
    from yaml import Loader as YamlLoader


def parse_args():
    import argparse

    argp = argparse.ArgumentParser()

    argp.add_argument(
        "--config",
        default="./notes2notion.yaml",
        help="configuration file (default: ./notes2notion.yaml)",
    )

    return argp.parse_args()


def load_config(config_file):
    import logging.config

    if not os.path.exists(config_file):
        print("config file does not exist: %s", config_file)
        return None

    with open(config_file, "r") as fp:
        conf = yaml.load(fp, Loader=YamlLoader)

        # XXX how to update existing loggers?

        if "logging" in conf:
            logging.config.dictConfig(conf["logging"])
        else:
            logging.basicConfig(level=logging.WARN)

    return conf


################################################################################
## MAIN ENTRY

args = parse_args()
conf = load_config(args.config)
log = logging.getLogger(__name__)

# TODO consider switching to Notional ...
# client = notional.connect(auth=conf["auth_token"])

client = Client(auth=conf["auth_token"])
archive = builder.PageArchive(client, conf["import_page_id"])

notes = apple.Notes()
note_ids = notes.get_all_ids()

for note_id in note_ids:
    note = notes[note_id]

    # skip empty notes
    if note is None:
        log.warning("empty note; skipping")
        continue

    note_meta = note["meta"]
    note_name = note_meta["name"]

    # skip locked notes
    if note_meta["locked"]:
        log.warning("LOCKED - %s", note_name)
        continue

    log.info("Processing - %s", note_name)

    page = archive.add(note)

    log.debug("processing complete - %s", note_name)
    log.info(":: %s => %s", note_name, page.get("url"))
