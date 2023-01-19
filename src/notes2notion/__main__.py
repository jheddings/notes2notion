"""Main interface to notes2notion."""


import logging

import click
import notional

from . import apple
from .builder import PageBuilder
from .config import AppConfig

logger = logging.getLogger(__name__)


class MainApp:
    """Context used during main execution."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logger.getChild("MainApp")

        self._initialize_session(config)

    def _initialize_session(self, config: AppConfig):
        self.session = notional.connect(auth=config.auth_token)
        self.archive = self.session.pages.retrieve(config.import_page_id)

    def __call__(self):
        builder = PageBuilder(self.session, self.archive)

        for note in apple.Notes():

            # skip empty notes
            if note is None:
                self.logger.warning("empty note; skipping")
                continue

            note_meta = note["meta"]
            note_name = note_meta["name"]

            # skip locked notes - they are just empty
            if note_meta["locked"]:
                self.logger.warning("LOCKED - %s", note_name)
                continue

            self.logger.info("Processing - %s", note_name)

            self.logger.debug("creating page - %s", note_name)

            # build the note in-place on the archive page
            try:
                page = builder.build(note)
            except Exception:
                self.logger.exception(
                    "An exception occurred while processing '%s'", note_name
                )
                continue

            self.logger.debug("processing complete - %s", note_name)
            self.logger.info(":: %s => %s", page.Title, page.url)


@click.command()
@click.option(
    "--config",
    "-f",
    default="notes2notion.yaml",
    help="app config file (default: notes2notion.yaml)",
)
def main(config):
    cfg = AppConfig.load(config)
    app = MainApp(cfg)

    app()


### MAIN ENTRY
if __name__ == "__main__":
    main()
