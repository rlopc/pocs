# Adopt the existing repository instead of creating it. The state is kept out of Git
# (.gitignore); if it is lost, the next plan imports everything again from these
# blocks. To replicate on a new repository, change the names and delete this file.

import {
  to = github_repository.pocs
  id = "pocs"
}

import {
  to = github_repository_vulnerability_alerts.pocs
  id = "pocs"
}

import {
  to = github_repository_dependabot_security_updates.pocs
  id = "pocs"
}

import {
  to = github_actions_repository_permissions.pocs
  id = "pocs"
}

import {
  to = github_workflow_repository_permissions.pocs
  id = "pocs"
}

import {
  to = github_repository_ruleset.protect_main
  id = "pocs:26652605"
}
