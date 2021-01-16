# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging

################################################################################
class ImportLog(object):

    #---------------------------------------------------------------------------
    def __init__(self, client, url=None):
        self.logger = logging.getLogger('notes2notion.logbook.ImportLog')

        self.client = client
        self.url = url
        self.collection = None

        if url is not None:
            self.logger.debug('initializing import log - %s', url)
            view = client.get_collection_view(url)
            self.collection = view.collection

    #---------------------------------------------------------------------------
    def get_latest_entry(self, note_id):
        if self.collection is None: return None

        self.logger.debug('query log entry: %s', note_id)

        # get the most recent log entry for the given node_id

        sort_params = [{
            'direction': 'descending',
            'property': 'timestamp'
        }]

        filter_params = {
            'filters': [{
                'property': 'note_id',
                'filter': {
                    'operator': 'string_is',
                    'value': {
                        'type': 'exact',
                        'value': note_id
                     }
                }
            }], 'operator': 'and'
        }

        result = self.collection.query(sort=sort_params, filter=filter_params)

        if len(result) == 0: return None

        entry = result[0]
        self.logger.debug('entry => %s', entry.id)

        return entry

    #---------------------------------------------------------------------------
    def new_entry(self, **kwargs):
        if self.collection is None: return None
        self.logger.debug('new log entry: %s', kwargs)
        entry = self.collection.add_row(**kwargs)
        self.logger.debug('entry => %s', entry.id)
        return entry

