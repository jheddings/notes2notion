"""Main interface to notes2notion."""


import logging

import click
import notional

from . import apple
from .builder import PageBuilder

logger = logging.getLogger(__name__)


class MainApp:
    """Context used during main execution."""

    def __init__(self, auth_token, page_ref):
        self.logger = logger.getChild("MainApp")

        self.session = notional.connect(auth=auth_token)
        self.archive = self.session.pages.retrieve(page_ref)

    def __call__(self, skip_title, include_meta, include_html):
        """Run the main app."""

        builder = PageBuilder(self.session, self.archive)

        builder.skip_title = skip_title
        builder.include_html = include_html
        builder.include_meta = include_meta

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
    "--auth",
    envvar="NOTION_ACCESS_TOKEN",
    help="Set your authentation token",
)
@click.option(
    "--page",
    required=True,
    help="The page URL or ID to store notes",
)
@click.option(
    "--meta/--no-meta",
    is_flag=True,
    default=False,
    help="Include metadata from exported notes",
)
@click.option(
    "--html/--no-html",
    is_flag=True,
    default=False,
    help="Include raw HTML from exported notes",
)
@click.option(
    "--title/--no-title",
    is_flag=True,
    default=False,
    help="Include note title in the body",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Only display warnings and errors",
)
def main(auth, page, meta, html, title, verbose, quiet):
    """Main entry point hanlder for notes2notion."""

    if verbose:
        logging.basicConfig(level=logging.DEBUG, force=True)
    elif quiet:
        logging.basicConfig(level=logging.ERROR, force=True)
    else:
        logging.basicConfig(level=logging.INFO, force=True)

    app = MainApp(auth_token=auth, page_ref=page)

    skip_title = not title

    app(skip_title=skip_title, include_html=html, include_meta=meta)


### MAIN ENTRY
if __name__ == "__main__":
    main()
