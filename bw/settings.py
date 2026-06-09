from bw.configuration import Configuration

import uuid

BW_UUID_NAMESPACE = uuid.UUID(hex='86878fc0-0db5-4d22-910c-c8e561292550')

GLOBAL_CONFIGURATION = None
if GLOBAL_CONFIGURATION is None:
    GLOBAL_CONFIGURATION = Configuration(Configuration.load('conf.kv') | Configuration.load_env(None))
