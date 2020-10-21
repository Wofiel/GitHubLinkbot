import configparser

class Config():
    def __init__(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)

        self.STRING_LENGTH = config.getint('configuration','string_length', fallback=200)
        self.MAX_EMBEDS = config.getint('configuration','max_embeds', fallback=5) # -1 is unlimited
        self.USERNAME = config.get('default_repository','username')
        self.REPOSITORY = config.get('default_repository','repository')

        self.CHANNEL_OVERRIDES = {}
        for override in config.items('channel_overrides'):
            channel = override[0]
            repo = override[1]
            if '/' in repo:
                username,repo = repo.split('/')
            else: # use default username if it's not provided
                username = self.USERNAME
            self.CHANNEL_OVERRIDES.update({channel:(username,repo)})