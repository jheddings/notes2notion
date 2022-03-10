# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# XXX with a little work, this could be a more general-purpose HTML parser for Notion
# perhaps we could pull out the document parser and include it with Notional?

import logging
import re

import yaml
from bs4 import BeautifulSoup
from notional import blocks

log = logging.getLogger(__name__)

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

    # FIXME need to return list of RichTextObject's

    text = " ".join(strings)
    markup = markup_text(block.name, text)
    return markup.strip()

class DocumentParser(object):

    # TODO make configurable
    include_meta: bool = True
    include_html: bool = True

    def __init__(self):
        self.title = None
        self.content = list()

        self._first_block = True

    def parse(self, note):
        note_meta = note["meta"]

        self.title = note_meta["name"]

        log.debug("parsing note - %s :: %s", self.title, note_meta["id"])

        # Apple Notes exports pretty basic HTML...
        # there is no html, head or body wrapper.

        soup = BeautifulSoup(note["body"], "html.parser")

        for elem in soup.children:
            self.parse_elem(elem)

        if note["attachments"]:
            self.import_files(note["attachments"])

        if self.include_meta or self.include_html:
            self.append_divider()

        if self.include_meta:
            log.debug("adding metadata to page...")
            meta_text = yaml.dump(note_meta).strip()
            self.append_code(meta_text, language="yaml")

        if self.include_html:
            log.debug("appending raw HTML...")
            self.append_code(note["body"], language="html")

        log.debug("finished construction - %s", note_meta["id"])

        return True

    def import_files(self, attachments):
        log.debug("processing attachments...")

        self.append_divider()

        for attachment in attachments:
            log.debug("attachment[%s] => %s", attachment["id"], attachment["name"])

            # FIXME until we figure out how to upload attachments, we write metadata
            # to help track them down...  eventually this is only if self.include_meta
            meta_text = yaml.dump(attachment).strip()
            self.append_code(meta_text, language="yaml")

    def append_text(self, text, parent=None):
        if text is None or len(text) == 0:
            return

        if parent is None:
            parent = self.content

        log.debug('adding text: "%s..."', text[:7])

        block = blocks.Paragraph.from_text(text)

        parent.append(block)

        return block

    def append_code(self, text, language=None, parent=None):
        if text is None or len(text) == 0:
            return

        if parent is None:
            parent = self.content

        log.debug('adding code block: "%s..." [%s]', text[:7], language)

        block = blocks.Code.from_text(text)

        if language:
            block.code.language = language

        self.content.append(block)

        return block

    def append_divider(self, parent=None):
        if parent is None:
            parent = self.content

        log.debug('adding divider')

        block = blocks.Divider()

        parent.append(block)

        return block

    def append_li(self, text, parent, list_type):
        if parent is None:
            parent = self.content

        log.debug('adding list item: "%s..."', text[:7])

        item = list_type.from_text(text)

        parent.append(item)

        return item

    def parse_elem(self, elem, parent=None):
        if elem is None:
            return None

        if parent is None:
            parent = self.content

        log.debug("processing block - %s", elem.name)

        leftover_text = None

        # skip the first line (assuming it is the title)
        if self._first_block:
            self._first_block = False
            log.debug("skipping first element")

        elif hasattr(self, f"parse_{elem.name}"):
            log.debug("parser func -- parse_%s", elem.name)
            pfunc = getattr(self, f"parse_{elem.name}")
            pfunc(elem, parent)

        # track text from remaining blocks
        else:
            leftover_text = get_block_text(elem)

        return leftover_text

    def parse_br(self, elem, parent):
        log.debug("skipping element -- %s", elem.name)

    def parse_meta(self, elem, parent):
        log.debug("skipping element -- %s", elem.name)

    def parse_div(self, elem, parent):
        if parent is None:
            parent = self.content

        # collect text from unmapped blocks
        pending_text = list()

        for child in elem.children:
            text = self.parse_elem(child)

            if text is not None and len(text) > 0:
                log.debug('leftover text: "%s..."', text[:7])
                pending_text.append(text)

        # deal with leftover text (if we found any)
        log.debug("block complete; %d pending block(s)", len(pending_text))
        if len(pending_text) > 0:
            text = "".join(pending_text)
            self.append_text(text, parent)

    def parse_h1(self, elem, parent):
        text = get_block_text(elem)
        block = blocks.Heading1.from_text(text)
        parent.append(block)

    def parse_h2(self, elem, parent):
        text = get_block_text(elem)
        block = blocks.Heading2.from_text(text)
        parent.append(block)

    def parse_h3(self, elem, parent):
        text = get_block_text(elem)
        block = blocks.Heading3.from_text(text)
        parent.append(block)

    def parse_list(self, elem, parent, list_type):
        item = None

        for child in elem.children:
            if child.name == "li":
                text = get_block_text(child)
                item = self.append_li(text, parent, list_type)
            else:
                self.parse_elem(child, item)

    def parse_ul(self, elem, parent):
        self.parse_list(elem, parent, blocks.BulletedListItem)

    def parse_ol(self, elem, parent):
        self.parse_list(elem, parent, blocks.NumberedListItem)

    def parse_script(self, elem, parent):
        text = get_block_text(elem)
        self.append_code(text, parent=parent)

    def parse_tt(self, elem, parent):
        text = get_block_text(elem)
        self.append_code(text, parent=parent)

    def parse_object(self, elem, parent):
        log.debug("processing object")

        for child in elem.children:
            if child.name == "table":
                self.parse_table(child, parent)
            else:
                log.warning("Unsupported object: %s", elem.name)

    def parse_table(self, table, parent):
        log.debug("building table")

        # FIXME make an actual table...
        self.append_code(str(table), parent=parent, language="html")

    def parse_img(self, elem, parent):
        import base64
        import tempfile

        log.debug("processing image")

        # Notes uses embedded images...  we need to extract the image, upload it
        # and reference it in the block

        # TODO this probably needs more error handling and better flow

        img_src = elem["src"]
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