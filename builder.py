# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging

from parser import DocumentParser

log = logging.getLogger(__name__)


class PageArchive(object):
    def __init__(self, session, page_id):
        self.session = session

        self.parent = session.pages.retrieve(page_id)

        log.debug("archive ready [%s]", self.parent)

    def add(self, note):
        note_meta = note["meta"]
        note_name = note_meta["name"]

        log.debug("creating page - %s", note_name)

        parser = DocumentParser()
        parser.parse(note)

        page = self.session.pages.create(
            parent=self.parent,
            title=parser.title,
            children=parser.content,
        )

        # DEBUG - print the raw page content
        # print(page.json(indent=4))

        return page

