__author__ = "Thygrrr, humbly treading in the shadow of sheeo's awesomeness"

import os
import git
import util
import logging
from collections import namedtuple

from git import Version

logger = logging.getLogger(__name__)

FEATURED_MOD_TO_REPO_NAME = {
    "faf": "fa",
    "coop": "fa",
    "gw": "fa",
    "balancetesting": "fa",
    "ladder1v1": "fa",
    "matchmaker": "fa",
    "nomads": "nomads",
    "murderparty": "murderparty",
    "labwars": "labwars",
    "wyvern": "wyvern",
    "blackops": "blackops",
    "xtremewars": "xtremewars",
    "diamond": "diamong",
    "phantomx": "phantomx",
    "vanilla": "vanilla",
    "civilians": "civilians",
    "koth": "koth",
    "claustrophobia": "claustrophobia",
    "supremeDestruction": "supremeDestruction"
}

DEFAULT_REPO_BASE = "FAForever"

FeaturedMod = namedtuple('FeaturedMod', 'name version')
Mod = namedtuple('Mod', 'name version')

def checkout_featured_mod(featured_mod, featured_repo, featured_version="faf/master", repo_dir=util.REPO_DIR):
    mod_repo = git.Repository(os.path.join(repo_dir, featured_mod), featured_repo)
    mod_repo.fetch()
    mod_repo.checkout(featured_version)

def is_featured_mod(mod):
    return isinstance(mod, FeaturedMod) and mod.name in FEATURED_MOD_TO_REPO_NAME.keys()

def featured_versions_to_repo_tag(featured_versions_hash):
    return str(reduce(max, featured_versions_hash.itervalues(), 0))

def replay_info_to_featured_mod_version(replay_info):
    return Version("/".join([DEFAULT_REPO_BASE, FEATURED_MOD_TO_REPO_NAME[replay_info["featured_mod"]]]),
                              featured_versions_to_repo_tag(replay_info["featured_mod_versions"]),
                              None)