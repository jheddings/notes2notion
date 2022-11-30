# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, root_validator


class AppConfig(BaseModel):

    auth_token: str
    import_page_id: str

    skip_title: bool = True
    include_meta: bool = True
    include_html: bool = False

    logging: Optional[Dict] = None

    @root_validator(pre=False)
    def configure_root_logger(cls, values):
        import logging.config

        if values and values["logging"]:
            conf = values["logging"]
        else:
            conf = {"version": 1, "incremental": False, "root": {"level": "WARN"}}

        logging.config.dictConfig(conf)

        return values

    @classmethod
    def load(cls, config_file):
        """Load the config from the given config file (YAML)."""

        if not os.path.exists(config_file):
            print(f"ERROR: config file does not exist: {config_file}")
            return None

        with open(config_file, "r") as fp:
            data = yaml.safe_load(fp)
            conf = cls(**data)

        return conf
