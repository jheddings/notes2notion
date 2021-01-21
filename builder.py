# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import re
import logging
import yaml

from notion.block import PageBlock, TextBlock, CodeBlock, ImageBlock
from notion.block import HeaderBlock, SubheaderBlock, SubsubheaderBlock
from notion.block import BulletedListBlock, NumberedListBlock
from notion.block import CollectionViewBlock, DividerBlock, QuoteBlock

from bs4 import BeautifulSoup

try:
    from yaml import CLoader as YamlLoader
except ImportError:
    from yaml import Loader as YamlLoader

# this maps the source HTML element from Notes to a Notion block type
block_map = {
    'h1' : HeaderBlock,
    'h2' : SubheaderBlock,
    'h3' : SubsubheaderBlock,
    'tt' : CodeBlock,
    'ul' : BulletedListBlock,
    'ol' : NumberedListBlock
}

# parse embedded image data
img_data_re = re.compile('^data:image/([^;]+);([^,]+),(.+)$')

################################################################################
# Notion supports inline markdown for common formatting...
def markup_text(tag, text):

    # bold text
    if tag == 'b' or tag == 'strong':
        return '**' + text + '**'

    # italics
    elif tag == 'i' or tag == 'em':
        return '*' + text + '*'

    # strike-through text
    elif tag == 'strike':
        return '~~' + text + '~~'

    # standard links
    elif tag == 'a':
        return '<' + text + '>'

    # underline - not supported in markdown
    #elif tag == 'u':

    return text

################################################################################
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

        if string is None: continue
        if len(string) == 0: continue

        strings.append(string.strip())

    text = ' '.join(strings)
    return markup_text(block.name, text)

################################################################################
def build_schema(thead):
    schema = dict()

    for idx, td in enumerate(thead):
        col_id = f'c{idx}'

        col_schema = {
            'name' : td,
            'type' : 'text'
        }

        # treat the first column differently
        if idx == 0:
            col_id = 'title'
            col_schema['type'] = 'title'

        schema[col_id] = col_schema

    return schema

################################################################################
class PageArchive(object):

    #---------------------------------------------------------------------------
    def __init__(self, archive):
        self.archive = archive
        self.logger = logging.getLogger('notes2notion.builder.PageArchive')

        self.logger.debug('archive ready - %s', archive.title)

    #---------------------------------------------------------------------------
    def store(self, note):
        note_meta = note['meta']
        note_name = note_meta['name']

        self.logger.debug('creating page - %s', note_name)

        # TODO support the folder heirarchy from the note metadata
        page = self.archive.children.add_new(PageBlock, title=note_name)
        self.logger.debug('page => %s', page.id)

        builder = PageBuilder(page)
        builder.construct(note)

        return page

################################################################################
class PageBuilder(object):

    # TODO make configurable
    skip_title = True
    include_meta = True
    include_html = False
    upload_attachments = True

    #---------------------------------------------------------------------------
    def __init__(self, page):
        self.page = page
        self.logger = logging.getLogger('notes2notion.builder.PageBuilder')

        self.logger.debug('builder ready - %s', page.title)

    #---------------------------------------------------------------------------
    def get_url(self):
        if self.page is None:
            return None

        return self.page.get_browseable_url()

    #---------------------------------------------------------------------------
    def construct(self, note):
        note_meta = note['meta']

        self.logger.debug('starting construction - %s', note_meta['id'])

        self.append_html(note['body'])

        if note['attachments']:
            self.logger.debug('processing attachments...')

            self.page.children.add_new(DividerBlock)
            self.page.children.add_new(SubheaderBlock, title='Attachments')

            for attachment in note['attachments']:
                self.logger.debug('attachment[%s] => %s', attachment['id'], attachment['name'])

                # TODO upload attachments
                if self.include_meta:
                    meta_text = yaml.dump(attachment)
                    self.page.children.add_new(CodeBlock, title=meta_text, language='yaml')

        if self.include_meta or self.include_html:
            self.page.children.add_new(DividerBlock)

        if self.include_meta:
            self.logger.debug('adding metadata to page...')
            meta_text = yaml.dump(note_meta)
            self.page.children.add_new(CodeBlock, title=meta_text, language='yaml')

        if self.include_html:
            self.logger.debug('appending raw HTML...')
            self.page.children.add_new(CodeBlock, title=html, language='html')

        self.logger.debug('finished construction - %s', note_meta['id'])

    #---------------------------------------------------------------------------
    def append_html(self, html):
        self.logger.debug('importing HTML (%d bytes)', len(html))

        soup = BeautifulSoup(html, 'html.parser')

        # Apple Notes exports pretty basic HTML...
        # there is no html, head or body wrapper.

        for elem in soup.children:
            if elem.name is None: continue

            self.logger.debug('append block: %s', elem.name)

            # let append_* methods do the heavy lifting
            if elem.name == 'div':
                self.append_block(elem)

            # handle lists separately
            elif elem.name == 'ul' or elem.name == 'ol':
                self.append_list(elem)

            else:
                self.logger.warning('Unknown Block: %s', elem.name)

    #---------------------------------------------------------------------------
    def append_block(self, elem):
        if elem is None: return None

        # collect blocks that are not directly mapped
        pending_blocks = list()

        for child in elem.children:
            self.logger.debug('processing child - %s', child.name)

            # skip empty line breaks
            if child.name == 'br':
                self.logger.debug('skipping line break')
                continue

            # if this is the first h1 child on the page, assume it is the title
            elif child.name == 'h1' and len(self.page.children) == 0:
                self.logger.debug('skipping title element')
                continue

            # handle images (may be more than one per block)
            elif child.name == 'img':
                self.append_img(child)

            # handle objects (like tables)
            elif child.name == 'object':
                self.append_object(child)

            # look for known block mappings...
            elif child.name in block_map:
                self.append_text(child)

            # track text from remaining blocks
            else:
                text = get_block_text(child)
                self.logger.debug('pending block [%d]: "%s..."',
                                  len(pending_blocks), text[:7])

                pending_blocks.append(text)

        # deal with pending blocks (if we found any)
        self.logger.debug('block complete; %d pending block(s)', len(pending_blocks))
        if len(pending_blocks) > 0:
            text = ' '.join(pending_blocks)
            self.page.children.add_new(TextBlock, title=text)

    #---------------------------------------------------------------------------
    def append_text(self, elem):
        block_type = block_map.get(elem.name, TextBlock)
        text = get_block_text(elem)

        if text is None or len(text) == 0:
            self.logger.debug('empty text block; skipping')
            return

        self.logger.debug('mapped to Notion block: %s => "%s..."', block_type, text[:7])

        block = self.page.children.add_new(block_type, title=text)
        self.logger.debug('block => %s', block.id)

    #---------------------------------------------------------------------------
    def append_list(self, list_elem):
        block_type = block_map.get(list_elem.name, None)

        self.logger.debug('building Notion list: %s', block_type)

        if block_type is None:
            self.logger.warning('Unknown list type: %s', block_type)
            return

        for li in list_elem.find_all('li', recursive=False):
            text = get_block_text(li)
            self.logger.debug('adding list item: "%s..."', text[:7])
            self.page.children.add_new(block_type, title=text)

    #---------------------------------------------------------------------------
    def append_img(self, img_elem):
        import base64
        import tempfile

        self.logger.debug('processing image')

        # Notes uses embedded images...  we need to extract the image, upload it
        # and reference it in the block

        # TODO this probably needs more error handling and better flow

        img_src = img_elem['src']
        m = img_data_re.match(img_src)

        if m is None:
            self.logger.warning('Unsupported image in note')
            return

        img_type = m.groups()[0]
        img_data_enc = m.groups()[1]
        img_data_str = m.groups()[2]

        self.logger.debug('found embedded image: %s [%s]', img_type, img_data_enc)

        if img_data_enc == 'base64':
            self.logger.debug('decoding base64 image: %d bytes', len(img_data_str))
            img_data_b64 = img_data_str.encode('ascii')
            img_data = base64.b64decode(img_data_b64)
        else:
            self.logger.warning('Unsupported img encoding: %s', img_data_enc)
            return

        self.logger.debug('preparing %d bytes for image upload', len(img_data))

        with tempfile.NamedTemporaryFile(suffix=f'.{img_type}') as fp:
            self.logger.debug('using temporary file: %s', fp.name)
            fp.write(img_data)

            # upload the image to Notion
            block = self.page.children.add_new(ImageBlock)

            try:
                block.upload_file(fp.name)
            except Exception:
                self.logger.error('UPLOAD FAILED')

    #---------------------------------------------------------------------------
    def append_object(self, elem):
        self.logger.debug('processing object')

        for child in elem.children:
            if child.name == 'table':
                self.append_table(child)
            else:
                self.logger.warning('Unsupported object: %s', block.name)

    #---------------------------------------------------------------------------
    def append_table(self, table):
        self.logger.debug('building table')

        # XXX it would make more sense if Notion supported basic markdown tables
        # instead, we have to build a collection view to capture the table data

        block = self.page.children.add_new(CollectionViewBlock)
        self.logger.debug('table => %s', block.id)

        # does Apple ever set a header?  I don't think so...
        # XXX maybe we want a flag to use the first table row as a header or not?
        thead = None

        tbody = table.find('tbody')
        for tr in tbody.find_all('tr', recursive=False):
            # if no header was provided, we will build it from this row...
            if thead is None:
                self.logger.debug('initializing header')
                thead = list()

            # if we have a header, but no Collection (yet)
            elif block.collection is None:
                schema = build_schema(thead)
                self.logger.debug('initializing schema: %s', schema)

                # XXX directly accessing _client here is a bit of a hack...
                client = self.page._client
                block.collection = client.get_collection(
                    client.create_record('collection', parent=block, schema=schema)
                )

                # we need a new view to see our lovely table...
                block.views.add_new(view_type='table')

            # if we have a valid collection, add data directly to rows
            row = None if block.collection is None else block.collection.add_row()

            # start processing the column data...
            tds = tr.find_all('td', recursive=False)
            for idx, td in enumerate(tds):
                text = get_block_text(td)
                if text is None: continue

                col_id = 'title' if idx == 0 else f'c{idx}'
                self.logger.debug('table data: %s => "%s..."', col_id, text[:7])

                if block.collection is None:
                    thead.append(text)

                if row is not None:
                    row.set_property(col_id, text)

