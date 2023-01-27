"""Page builder for Notion."""

import logging
import re

import yaml
from notional import blocks
from notional.parser import HtmlParser

logger = logging.getLogger(__name__)

# parse embedded image data
img_data_re = re.compile("^data:image/([^;]+);([^,]+),(.+)$")


class PageBuilder(object):
    def __init__(self, session, parent):
        self.session = session
        self.parent = parent
        self.logger = logger.getChild("PageBuilder")

        self.skip_title = True
        self.include_meta = False
        self.include_html = False

    def build(self, note):
        note_meta = note["meta"]

        self.logger.debug("parsing note - %s :: %s", note_meta["name"], note_meta["id"])

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
            self.logger.debug("adding metadata to page...")
            meta_text = yaml.dump(note_meta).strip()
            self.append_h1(page, "Source Metadata")
            self.append_code(meta_text, page, language="yaml")

        if self.include_html:
            self.logger.debug("appending raw HTML...")
            self.append_h1(page, "Source Note Code")
            self.append_code(note["body"], page, language="html")

        self.logger.debug("finished construction - %s", note_meta["id"])

        return page

    def import_files(self, page, attachments):
        self.logger.debug("processing attachments...")

        self.append_divider(page)
        self.append_h1(page, "Attachments")

        for attachment in attachments:
            self.logger.debug(
                "attachment[%s] => %s", attachment["id"], attachment["name"]
            )

            # FIXME until we figure out how to upload attachments, we write metadata
            # to help track them down...  eventually this is only if self.include_meta
            meta_text = yaml.dump(attachment).strip()
            self.append_code(meta_text, page, language="yaml")

    def append_h1(self, page, text):
        block = blocks.Heading1[text]
        self.session.blocks.children.append(page, block)

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
