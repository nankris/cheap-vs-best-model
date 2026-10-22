from defaults import DEFAULTS
from merge import deep_merge

def load(override):
    return deep_merge(DEFAULTS, override)
