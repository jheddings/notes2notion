#!/usr/bin/env python3

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import sys

import notional

# setup logging before importing our modules
from config import AppConfig

conf = AppConfig.load(sys.argv[1])

import apple
from builder import PageBuilder

log = logging.getLogger(__name__)

session = notional.connect(auth=conf.auth_token)
archive = session.pages.retrieve(conf.import_page_id)
builder = PageBuilder(session, archive)

for note in apple.Notes():

    # skip empty notes
    if note is None:
        log.warning("empty note; skipping")
        continue

    note_meta = note["meta"]
    note_name = note_meta["name"]

    # skip locked notes - they are just empty
    if note_meta["locked"]:
        log.warning("LOCKED - %s", note_name)
        continue

    log.info("Processing - %s", note_name)

    log.debug("creating page - %s", note_name)

    # build the note in-place on the archive page
    try:
        page = builder.build(note)
    except Exception:
        log.exception("An exception occurred while processing '%s'", note_name)
        continue

    log.debug("processing complete - %s", note_name)
    log.info(":: %s => %s", page.Title, page.url)
