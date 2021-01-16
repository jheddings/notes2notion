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

from notion.client import NotionClient

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
archive = builder.PageArchive(top_page)
tracker = logbook.ImportLog(client, conf['import_log_url'])

# load each note and upload to Notion
for note in apple.Notes():

    note_meta = note['meta']
    note_name = note_meta['name']
    note_id = note_meta['id']

    # skip locked notes
    if note_meta['locked']:
        logger.warning('LOCKED - %s', note_name)
        continue

    logger.info('Processing - %s', note_name)

    # look for an existing 'Finished' entry, otherwise start a new one
    log = tracker.get_latest_entry(note_id)
    if log is not None and log.status == 'Finished':
        logger.debug('skipping - %s [Finished]', note_name)
        continue

    log = tracker.new_entry(
        name=note_name, status='Pending', note_id=note_id
    )

    # process the note in the target archive
    page = archive.store(note)
    log.page = page.get_browseable_url()

    # finally, update the logbook if needed...
    if log is not None: log.status = 'Finished'

    logger.debug('processing complete - %s', note_name)

