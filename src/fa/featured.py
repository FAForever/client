__author__ = "Thygrrr, humbly treading in the shadow of sheeo's awesomeness"

import os
import git
import util
import logging

logger = logging.getLogger(__name__)

def checkout_featured_mod(featured_mod, featured_repo, featured_version="faf/master", repo_dir=util.REPO_DIR):
    mod_repo = git.Repository(os.path.join(repo_dir, featured_mod), featured_repo)
    mod_repo.fetch()
    mod_repo.checkout(featured_version)
