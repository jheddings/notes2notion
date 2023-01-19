"""Main interface to notes2notion."""


import logging
import sys

import notional

# setup logging before importing our modules
from config import AppConfig

conf = AppConfig.load(sys.argv[1])

from . import apple
from .builder import PageBuilder

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
