from bw.configuration import Configuration

AUTH_SETTINGS = None
if AUTH_SETTINGS is None:
    AUTH_SETTINGS = Configuration.load('auth.txt')
