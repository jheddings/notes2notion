# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# XXX with a bit of work, this could be a general-purpose HTML parser for Notion

# TODO preserve all text formatting when combining styles
# TODO support embedded pictures (e.g. from Apple Notes)
# TODO test this with other HTML, especially poorly formatted content

import logging
import re

from bs4 import BeautifulSoup
from notional import blocks

log = logging.getLogger(__name__)

# parse embedded image data
img_data_re = re.compile("^data:image/([^;]+);([^,]+),(.+)$")


def gather_text(elem):
    text = " ".join(elem.strings)
    return text.strip() or None


class DocumentParser(object):

    # TODO make configurable
    skip_title: bool = True

    def __init__(self, session, page):
        self.session = session
        self.page = page

    def parse(self, html):

        log.debug("BEGIN parsing")

        soup = BeautifulSoup(html, "html.parser")
        self.process(soup)

        log.debug("END parsing")

        return self.page

    def append(self, block, parent=None):
        if block is None:
            return

        if parent is None:
            parent = self.page

        self.session.blocks.children.append(parent, block)

        return block

    def process(self, elem, parent=None):
        log.debug("processing element - %s", elem.name)

        if parent is None:
            parent = self.page

        pending_text = list()

        for child in elem.children:
            if self.parse_elem(child, parent):
                continue

            # accumulate leftover text...
            text = self.strip_text(child)

            if text is not None:
                pending_text.append(text)

        log.debug("block complete; %d pending block(s)", len(pending_text))

        # ...deal with leftover text (if we found any)
        if len(pending_text) > 0:
            block = blocks.Paragraph.from_text(*pending_text)
            self.append(block, parent)

    # process as much text as possible from the element
    def strip_text(self, elem):

        if hasattr(self, f"text_{elem.name}"):
            log.debug("apply text -- text_%s", elem.name)
            strip = getattr(self, f"text_{elem.name}")

            return strip(elem)

        return self.text(elem)

    def text(self, elem, **style):
        txt = elem.string

        if txt is None or txt.isspace():
            return None

        return blocks.TextObject.from_value(txt, **style)

    def text_b(self, elem):
        return self.text(elem, bold=True)

    def text_strong(self, elem):
        return self.text_b(elem)

    def text_i(self, elem):
        return self.text(elem, italic=True)

    def text_em(self, elem):
        return self.text_i(elem)

    def text_u(self, elem):
        return self.text(elem, underline=True)

    def text_ins(self, elem):
        return self.text_u(elem)

    def text_s(self, elem):
        return self.text_del(elem)

    def text_strike(self, elem):
        return self.text_del(elem)

    def text_del(self, elem):
        return self.text(elem, strikethrough=True)

    def text_kbd(self, elem):
        return self.text_code(elem)

    def text_code(self, elem):
        return self.text(elem, code=True)

    # returns any collected text that could not be handled directly
    def parse_elem(self, elem, parent=None):
        if elem is None:
            return None

        log.debug("parsing element - %s", elem.name)

        # skip the first element if configured
        if self.skip_title:
            self.skip_title = False
            log.debug("skipping first element")
            return True

        # handle known blocks
        elif hasattr(self, f"parse_{elem.name}"):
            log.debug("parser func -- parse_%s", elem.name)
            pfunc = getattr(self, f"parse_{elem.name}")

            pfunc(elem, parent)
            return True

        return False

    def parse_html(self, elem, parent):
        self.process(elem, parent)

    def parse_head(self, elem, parent):
        # TODO parse the title only
        self.process(elem, parent)

    def parse_meta(self, elem, parent):
        pass

    def parse_title(self, elem, parent):
        self.page.title = self.strip_text(elem)

    def parse_body(self, elem, parent):
        self.process(elem, parent)

    def parse_br(self, elem, parent):
        pass

    def parse_hr(self, elem, parent):
        block = blocks.Divider()
        self.append(block, parent)

    def parse_iframe(self, elem, parent):
        src = elem.get("src")
        block = blocks.Embed.from_url(src)
        self.append(block, parent)

    def parse_div(self, elem, parent):
        self.process(elem, parent)

    def parse_object(self, elem, parent):
        self.process(elem, parent)

    def parse_h1(self, elem, parent):
        text = gather_text(elem)
        block = blocks.Heading1.from_text(text)
        self.append(block, parent)

    def parse_h2(self, elem, parent):
        text = gather_text(elem)
        block = blocks.Heading2.from_text(text)
        self.append(block, parent)

    def parse_h3(self, elem, parent):
        text = gather_text(elem)
        block = blocks.Heading3.from_text(text)
        self.append(block, parent)

    def parse_p(self, elem, parent):
        text = gather_text(elem)
        block = blocks.Paragraph.from_text(text)
        self.append(block, parent)

    def parse_list(self, elem, parent, list_type):
        item = None

        # lists are tricky since we have to keep an eye on the containing element,
        # which tells us the type of list item to create in Notion

        for child in elem.children:

            if child.name == "li":
                text = gather_text(child)

                if text is not None:
                    item = list_type.from_text(text)
                    self.append(item, parent)

            else:
                self.parse_elem(child, item)

    def parse_ul(self, elem, parent):
        self.parse_list(elem, parent, blocks.BulletedListItem)

    def parse_ol(self, elem, parent):
        self.parse_list(elem, parent, blocks.NumberedListItem)

    # def parse_dl(self, elem, parent):
    # def parse_dd(self, elem, parent):
    # def parse_dt(self, elem, parent):

    def parse_script(self, elem, parent):
        self.parse_pre(elem, parent=parent)

    def parse_tt(self, elem, parent):
        self.parse_pre(elem, parent=parent)

    def parse_pre(self, elem, parent):
        text = gather_text(elem)
        block = blocks.Code.from_text(text)
        self.append(block, parent)

    def parse_blockquote(self, elem, parent):
        text = gather_text(elem)
        block = blocks.Quote.from_text(text)
        self.append(block, parent)

    def parse_table(self, elem, parent):
        log.debug("building table")

        table = blocks.Table()

        self.process(elem, parent=table)

        if table.Width > 0:
            self.append(table, parent)

    def parse_thead(self, elem, parent):
        self.process(elem, parent=parent)

    def parse_tbody(self, elem, parent):
        self.process(elem, parent=parent)

    def parse_tfoot(self, elem, parent):
        self.process(elem, parent=parent)

    def parse_tr(self, elem, parent):
        # table rows must be directly appended to the table
        row = blocks.TableRow()
        self.process(elem, parent=row)
        parent.append(row)

    def parse_th(self, elem, parent):
        self.parse_td(elem, parent)

    def parse_td(self, elem, parent):
        # table data must be directly appended to the row
        text = gather_text(elem)
        parent.append(text or "")

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
