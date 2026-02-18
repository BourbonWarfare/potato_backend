from bw.configuration import Configuration

GLOBAL_CONFIGURATION = None
if GLOBAL_CONFIGURATION is None:
    GLOBAL_CONFIGURATION = Configuration(Configuration.load('conf.kv') | Configuration.load_env(None))
