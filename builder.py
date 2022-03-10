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
from parser import DocumentParser

import yaml
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


class PageBuilder(object):

    # TODO make configurable
    include_meta: bool = True
    include_html: bool = True

    def __init__(self, session, parent):
        self.session = session
        self.parent = parent

    def build(self, note):
        note_meta = note["meta"]

        log.debug("parsing note - %s :: %s", note_meta["name"], note_meta["id"])

        page = self.session.pages.create(
            parent=self.parent,
            title=note_meta["name"],
        )

        pdoc = DocumentParser(self.session, page)

        pdoc.parse(note["body"])

        if note["attachments"]:
            self.import_files(pdoc, note["attachments"])

        if self.include_meta or self.include_html:
            self.append_divider(pdoc)

        if self.include_meta:
            log.debug("adding metadata to page...")
            meta_text = yaml.dump(note_meta).strip()
            self.append_code(meta_text, pdoc, language="yaml")

        if self.include_html:
            log.debug("appending raw HTML...")
            self.append_code(note["body"], pdoc, language="html")

        log.debug("finished construction - %s", note_meta["id"])

        return page

    def import_files(self, pdoc, attachments):
        log.debug("processing attachments...")

        self.append_divider(pdoc)

        for attachment in attachments:
            log.debug("attachment[%s] => %s", attachment["id"], attachment["name"])

            # FIXME until we figure out how to upload attachments, we write metadata
            # to help track them down...  eventually this is only if self.include_meta
            meta_text = yaml.dump(attachment).strip()
            self.append_code(meta_text, pdoc, language="yaml")

    def append_divider(self, pdoc):
        log.debug("adding divider")

        block = blocks.Divider()

        return pdoc.append(block)

    def append_code(self, text, pdoc, language=None):
        if text is None or len(text) == 0:
            return

        log.debug('adding code block: "%s..." [%s]', text[:7], language)

        block = blocks.Code.from_text(text)

        if language:
            block.code.language = language

        return pdoc.append(block)
