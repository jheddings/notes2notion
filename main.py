#!/usr/bin/env python3

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import logging
import yaml
import requests

from notion.client import NotionClient
from notion.block import PageBlock

# local imports
import apple
import logbook
import builder

try:
    from yaml import CLoader as YamlLoader
except ImportError:
    from yaml import Loader as YamlLoader

################################################################################
def parse_args():
    import argparse

    argp = argparse.ArgumentParser()

    argp.add_argument('--config', default='./notes2notion.yaml',
                       help='configuration file (default: ./notes2notion.yaml)')

    return argp.parse_args()

################################################################################
def load_config(config_file):
    import logging.config

    if not os.path.exists(config_file):
        print('config file does not exist: %s', config_file)
        return None

    with open(config_file, 'r') as fp:
        conf = yaml.load(fp, Loader=YamlLoader)

        if 'logging' in conf:
            logging.config.dictConfig(conf['logging'])
        else:
            logging.basicConfig(level=logging.WARN)

    return conf

################################################################################
## MAIN ENTRY

args = parse_args()
conf = load_config(args.config)
logger = logging.getLogger('notes2notion')

client = NotionClient(token_v2=conf['token_v2'])
top_page = client.get_block(conf['import_page_url'])
#archive = builder.PageArchive(top_page)
tracker = logbook.ImportLog(client, conf['import_log_url'])

notes = apple.Notes()
note_ids = notes.get_all_ids()

# extracting notes one at a time takes a VERY long time...  we will use the
# ID's instead of the default iterator and skip notes that are 'Finished'

for note_id in note_ids:

    # look for an existing 'Finished' entry, otherwise start a new one
    log = tracker.get_latest_entry(note_id)
    if log is not None and log.status == 'Finished':
        logger.debug('skipping - %s [Finished]', log.name)
        continue

    note = notes[note_id]

    if note is None:
        # XXX should we track in the import log?
        logger.warning('empty note; skipping')
        continue

    note_meta = note['meta']
    note_name = note_meta['name']

    # skip locked notes
    if note_meta['locked']:
        logger.warning('LOCKED - %s', note_name)
        continue

    logger.info('Processing - %s', note_name)

    log = tracker.new_entry(
        name=note_name, status='Pending', note_id=note_id
    )

    # TODO support the folder heirarchy from the note metadata
    page = top_page.children.add_new(PageBlock, title=note_name)
    logger.debug('page => %s', page.id)

    # update the location of the page we are about to build...
    if log is not None:
        log.page = page.get_browseable_url()

    try:
        builder.PageBuilder(page).construct(note)
        if log is not None: log.status = 'Finished'

    except requests.exceptions.HTTPError as e:
        logger.error('HTTPError - %s', e)
        if log is not None: log.status = 'Failed'

    logger.debug('processing complete - %s', note_name)

