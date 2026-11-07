resource "github_repository" "pocs" {
  name        = "pocs"
  description = "Monorepo of proofs of concept"
  topics      = ["monorepo", "proof-of-concept", "python"]

  # Public: secret scanning and push protection are free only on public repositories,
  # and the code is meant to be reused (MIT license).
  visibility = "public"

  has_issues      = true
  has_discussions = false
  # Not used: planning lives in each POC, documentation in the repository.
  has_projects = false
  has_wiki     = false

  # Squash only: every pull request becomes one commit on main, titled with the PR
  # title, which the pr-title workflow checks against the commit convention.
  allow_squash_merge          = true
  allow_merge_commit          = false
  allow_rebase_merge          = false
  squash_merge_commit_title   = "PR_TITLE"
  squash_merge_commit_message = "PR_BODY"
  allow_auto_merge            = true
  delete_branch_on_merge      = true
  # The ruleset requires branches to be up to date, so offer the update button.
  allow_update_branch = true

  # Free on public repositories. Push protection blocks a push that contains a
  # known secret format before it reaches GitHub.
  security_and_analysis {
    secret_scanning {
      status = "enabled"
    }
    secret_scanning_push_protection {
      status = "enabled"
    }
  }

  # A `terraform destroy` must never delete the repository and its history.
  archive_on_destroy = true
  lifecycle {
    prevent_destroy = true
  }
}

# Dependabot alerts for known vulnerabilities in the dependencies.
resource "github_repository_vulnerability_alerts" "pocs" {
  repository = github_repository.pocs.name
  enabled    = true
}

# Security fix PRs as soon as an advisory is published, independent of the version
# updates scheduled in .github/dependabot.yml.
resource "github_repository_dependabot_security_updates" "pocs" {
  repository = github_repository.pocs.name
  enabled    = true
}
