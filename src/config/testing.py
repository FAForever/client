from .production import default_values as production_defaults

default_values = production_defaults.copy()
default_values['display_name'] = 'Test Server'
default_values['host'] = 'test.faforever.com'
default_values['oauth/client_id'] = 'faf-java-client'
