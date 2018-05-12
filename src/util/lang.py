# TODO: Python has no "reasonably guess language from country"
# package, so use this rough guesstimate
COUNTRY_TO_LANGUAGE = {
    "ru": ["ru", "kz", "kg"],
    "by": ["by"],
    "de": ["de", "au"],
}
COUNTRY_TO_LANGUAGE = {
    country: lang
    for lang, countries in COUNTRY_TO_LANGUAGE.items()
    for country in countries
}
