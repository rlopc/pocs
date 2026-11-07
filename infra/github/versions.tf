# GitHub settings of this repository as code: what lives only in the GitHub UI
# (repository settings, security features, Actions permissions, the branch ruleset).
# Run from this folder: `terraform init`, then `terraform plan` to detect drift and
# `terraform apply` to restore the declared state.
#
# Settings the provider does not support yet are applied by `api-only.sh`; the one
# setting with no API at all is listed in docs/README.md.

terraform {
  # Import blocks (imports.tf) need 1.5+.
  required_version = ">= 1.5"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
    }
  }
}

# Authentication: GITHUB_TOKEN if set, else the GitHub CLI session (`gh auth token`).
# The account needs admin rights on the repository.
provider "github" {
  owner = "rlopc"
}
