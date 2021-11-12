# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import logging
import re

import yaml
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# this maps the source HTML element from Notes to a Notion block type
block_map = {
    "h1": "heading_1",
    "h2": "heading_2",
    "h3": "heading_3",
    "ul": "bulleted_list_item",
    "ol": "numbered_list_item",
}

# parse embedded image data
img_data_re = re.compile("^data:image/([^;]+);([^,]+),(.+)$")


def markup_text(tag, text):

    # bold text
    if tag == "b" or tag == "strong":
        return "**" + text + "**"

    # italics
    elif tag == "i" or tag == "em":
        return "*" + text + "*"

    # strike-through text
    elif tag == "strike":
        return "~~" + text + "~~"

    # standard links
    elif tag == "a":
        return "<" + text + ">"

    # underline - not supported in markdown
    # elif tag == 'u':

    return text


def get_block_text(block):

    # no-name blocks are just strings...
    if block.name is None:
        return str(block)

    # otherwise, iterate over the text in the child elements

    # we could use this method to do additional processing on the text
    # e.g. we could look for things that look like URL's and make links
    # e.g. we could look for lines that start with '-' and make lists

    strings = list()

    for child in block.children:
        string = get_block_text(child)

        if string is None:
            continue
        if len(string) == 0:
            continue

        strings.append(string.strip())

    text = " ".join(strings)
    return markup_text(block.name, text)


def build_schema(thead):
    schema = dict()

    for idx, td in enumerate(thead):
        col_id = f"c{idx}"

        col_schema = {"name": td, "type": "text"}

        # treat the first column differently
        if idx == 0:
            col_id = "title"
            col_schema["type"] = "title"

        schema[col_id] = col_schema

    return schema


class PageArchive(object):
    def __init__(self, client, page_id):
        self.client = client
        self.parent_id = page_id

        log.debug("archive ready [%s]", self.parent_id)

    def add(self, note):
        note_meta = note["meta"]
        note_name = note_meta["name"]

        log.debug("creating page - %s", note_name)

        builder = PageBuilder(self.parent_id)
        page = builder.construct(note)

        # DEBUG - print the raw page content
        print(json.dumps(page, indent=4))

        return self.client.pages.create(**page)


class PageBuilder(object):

    # TODO make configurable
    include_meta = True
    include_html = True

    children = list()

    def __init__(self, parent_id):
        self.page = {
            "parent": {"page_id": parent_id},
            "properties": {},
            "children": [],
        }

    def construct(self, note):
        note_meta = note["meta"]

        log.debug("starting construction - %s", note_meta["id"])

        self.import_html(note["body"])

        if note["attachments"]:
            log.debug("processing attachments...")

            self.append_divider()
            self.append_heading("Attachments")

            for attachment in note["attachments"]:
                log.debug("attachment[%s] => %s", attachment["id"], attachment["name"])

                # TODO upload attachments
                if self.include_meta:
                    meta_text = yaml.dump(attachment)
                    self.append_code(meta_text, language="yaml")

        if self.include_meta or self.include_html:
            self.append_divider()

        if self.include_meta:
            log.debug("adding metadata to page...")
            meta_text = yaml.dump(note_meta)
            self.append_code(meta_text, language="yaml")

        if self.include_html:
            log.debug("appending raw HTML...")
            self.append_code(note["body"], language="html")

        log.debug("finished construction - %s", note_meta["id"])

        return self.page

    def import_html(self, html):
        log.debug("importing HTML (%d bytes)", len(html))

        soup = BeautifulSoup(html, "html.parser")

        # Apple Notes exports pretty basic HTML...
        # there is no html, head or body wrapper.

        for elem in soup.children:
            if elem.name is None:
                continue

            log.debug("append block: %s", elem.name)

            # let import_* methods do the heavy lifting
            if elem.name == "div":
                self.import_block(elem)

            # handle lists separately
            elif elem.name == "ul" or elem.name == "ol":
                self.import_list(elem)

            else:
                log.warning("Unknown Block: %s", elem.name)

    def import_block(self, elem):
        if elem is None:
            return None

        # collect blocks that are not directly mapped
        pending_blocks = list()

        for child in elem.children:
            log.debug("processing child - %s", child.name)

            # skip empty line breaks
            if child.name == "br":
                log.debug("skipping line break")
                continue

            # if this is the first h1 child on the page, assume it is the title
            elif child.name == "h1" and len(self.page["children"]) == 0:
                text = get_block_text(elem)
                self.set_title(text)

            # handle images (may be more than one per block)
            elif child.name == "img":
                # self.import_img(child)
                pass

            # handle objects (like tables)
            elif child.name == "object":
                self.import_object(child)

            # handle code blocks
            elif child.name == "tt":
                # TODO merge adjacent code blocks...
                # TODO don't strip leading whitespace...
                self.import_code(child)

            # look for known block mappings...
            elif child.name in block_map:
                self.import_text(child)

            # track text from remaining blocks
            else:
                text = get_block_text(child)
                log.debug('pending block [%d]: "%s..."', len(pending_blocks), text[:7])

                pending_blocks.append(text)

        # deal with pending blocks (if we found any)
        log.debug("block complete; %d pending block(s)", len(pending_blocks))
        if len(pending_blocks) > 0:
            text = "".join(pending_blocks)
            self.append_text(text)

    def import_text(self, elem):
        block_type = block_map.get(elem.name, "paragraph")
        text = get_block_text(elem)

        if text is None or len(text) == 0:
            log.debug("empty text block; skipping")
            return

        log.debug('mapped to Notion block: %s => "%s..."', block_type, text[:7])

        self.append_text(text, type=block_type)

    def import_code(self, elem):
        text = get_block_text(elem)
        self.append_code(text, language="plain text")

    def import_list(self, list_elem, parent=None):
        list_type = block_map.get(list_elem.name, None)

        log.debug("building Notion list: %s", list_type)

        if list_type is None:
            log.warning("Unknown list type: %s", list_type)
            return

        item = None

        for child in list_elem.children:
            if child.name == "li":
                item = self.import_list_item(parent, child, list_type)
            elif child.name == "ul" or child.name == "ol":
                self.import_list(child, parent=item)

    def import_list_item(self, parent, elem, list_type):
        text = get_block_text(elem)
        log.debug('adding list item: "%s..."', text[:7])

        item = self.append_text(text, type=list_type, parent=parent)

        return item[list_type]

    def import_img(self, img_elem):
        import base64
        import tempfile

        log.debug("processing image")

        # Notes uses embedded images...  we need to extract the image, upload it
        # and reference it in the block

        # TODO this probably needs more error handling and better flow

        img_src = img_elem["src"]
        m = img_data_re.match(img_src)

        if m is None:
            log.warning("Unsupported image in note")
            return

        img_type = m.groups()[0]
        img_data_enc = m.groups()[1]
        img_data_str = m.groups()[2]

        log.debug("found embedded image: %s [%s]", img_type, img_data_enc)

        if img_data_enc == "base64":
            log.debug("decoding base64 image: %d bytes", len(img_data_str))
            img_data_b64 = img_data_str.encode("ascii")
            img_data = base64.b64decode(img_data_b64)
        else:
            log.warning("Unsupported img encoding: %s", img_data_enc)
            return

        log.debug("preparing %d bytes for image upload", len(img_data))

        with tempfile.NamedTemporaryFile(suffix=f".{img_type}") as fp:
            log.debug("using temporary file: %s", fp.name)
            fp.write(img_data)

            # TODO upload the image to Notion

    def import_object(self, elem):
        log.debug("processing object")

        for child in elem.children:
            if child.name == "table":
                self.import_table(child)
            else:
                log.warning("Unsupported object: %s", elem.name)

    def import_table(self, table):
        log.debug("building table")

        # XXX it would make more sense if Notion supported basic markdown tables
        # instead, we have to build a full schema to represent the table

        # FIXME make an actual table...
        self.append_code(str(table), language="html")

    def set_title(self, text):
        self.page["properties"]["title"] = [{"text": {"content": text}}]

    def append_text(self, text, type="paragraph", href=None, parent=None):
        block_data = {
            "object": "block",
            "type": type,
            type: {
                "text": [
                    {
                        "type": "text",
                        "text": {"content": text[:2000], "link": href},
                    }
                ]
            },
        }

        return self.append_child(data=block_data, parent=parent)

    def append_heading(self, text, level=1, href=None):
        return self.append_text(text, type=f"heading_{level}", href=href)

    def append_code(self, text, language=None, parent=None):
        block_data = {
            "object": "block",
            "type": "code",
            "code": {
                "text": [{"type": "text", "text": {"content": text[:2000]}}],
                "language": language,
            },
        }

        return self.append_child(data=block_data, parent=parent)

    def append_divider(self, parent=None):
        block_data = {"object": "block", "type": "divider", "divider": {}}
        return self.append_child(data=block_data, parent=parent)

    def append_table(self, title=""):
        block_data = {
            "object": "block",
            "type": "child_database",
            "child_database": {"title": title},
        }

        return self.append_child(data=block_data)

    def append_child(self, data, parent=None):
        if parent is None:
            parent = self.page

        if "children" in parent:
            parent["children"].append(data)
        else:
            parent["children"] = [data]

        return data
