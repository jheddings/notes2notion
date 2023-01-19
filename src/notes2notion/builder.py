"""Page builder for Notion."""

import logging
import re

import yaml
from notional import blocks
from notional.parser import HtmlParser

log = logging.getLogger(__name__)

# parse embedded image data
img_data_re = re.compile("^data:image/([^;]+);([^,]+),(.+)$")


class PageBuilder(object):

    # TODO make configurable
    include_meta: bool = True
    include_html: bool = False

    def __init__(self, session, parent):
        self.session = session
        self.parent = parent

    def build(self, note):
        note_meta = note["meta"]

        log.debug("parsing note - %s :: %s", note_meta["name"], note_meta["id"])

        parser = HtmlParser()

        parser.parse(note["body"])

        page = self.session.pages.create(
            parent=self.parent,
            title=note_meta["name"],
            children=parser.content,
        )

        if note["attachments"]:
            self.import_files(page, note["attachments"])

        if self.include_meta or self.include_html:
            self.append_divider(page)

        if self.include_meta:
            log.debug("adding metadata to page...")
            meta_text = yaml.dump(note_meta).strip()
            self.append_code(meta_text, page, language="yaml")

        if self.include_html:
            log.debug("appending raw HTML...")
            self.append_code(note["body"], page, language="html")

        log.debug("finished construction - %s", note_meta["id"])

        return page

    def import_files(self, page, attachments):
        log.debug("processing attachments...")

        self.append_divider(page)

        for attachment in attachments:
            log.debug("attachment[%s] => %s", attachment["id"], attachment["name"])

            # FIXME until we figure out how to upload attachments, we write metadata
            # to help track them down...  eventually this is only if self.include_meta
            meta_text = yaml.dump(attachment).strip()
            self.append_code(meta_text, page, language="yaml")

    def append_divider(self, page):
        block = blocks.Divider()
        self.session.blocks.children.append(page, block)

    def append_code(self, text, page, language=None):
        if text is None:
            return

        block = blocks.Code[text]

        if language:
            block.code.language = language

        self.session.blocks.children.append(page, block)
