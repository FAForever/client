from .production import defaults as production_defaults

defaults = production_defaults.copy()
defaults['host'] = 'test.faforever.com'
defaults['client/logs/console'] = True
