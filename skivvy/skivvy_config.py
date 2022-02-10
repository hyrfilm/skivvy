import json

import os

from os import path


class SkivvyConfig:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, item):
        if item not in self.d:
            raise AttributeError("%s not found in %s" % (item, self.d))
        else:
            return self.d[item]

    def get(self, item, default=None):
        return self.d.get(item, default)

    def as_dict(self):
        return dict(self.d)


def read_config(config_name):
    cwd = os.getcwd()
    config_file = path.join(cwd, config_name)

    fp = open(config_file)
    config_dict = json.load(fp)
    return SkivvyConfig(config_dict)
