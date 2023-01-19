"""Application configuration for notes2notion.

See `notes2notion.yaml` for information about config options.
"""

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
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"config file does not exist: {config_file}")

        with open(config_file, "r") as fp:
            data = yaml.load(fp, Loader=yaml.SafeLoader)
            conf = AppConfig(**data)

        logger = cls._configure_logging(conf)
        logger.info("loaded AppConfig from: %s", config_file)

        return conf

    @classmethod
    def _configure_logging(cls, conf):
        import logging.config

        if conf.logging is None:
            # using dictConfig() here replaces the existing configuration of all loggers
            # this approach is more predictable than logging.basicConfig(level=logging.WARN)
            logconf = {"version": 1, "incremental": False, "root": {"level": "WARN"}}

        else:
            logconf = conf.logging

        logging.config.dictConfig(logconf)

        return logging.getLogger()
