# Protection of main: every change lands through a squash-merged pull request whose
# required checks passed on the latest main.
resource "github_repository_ruleset" "protect_main" {
  name        = "protect-main"
  repository  = github_repository.pocs.name
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  # No bypass actors: the rules also apply to the owner.

  rules {
    deletion                = true
    non_fast_forward        = true
    required_linear_history = true

    pull_request {
      allowed_merge_methods = ["squash"]
      # 0 approvals: a single maintainer cannot approve their own pull requests.
      # Raise it when collaborators join (it is also what OpenSSF Scorecard's
      # Branch-Protection and Code-Review checks ask for).
      required_approving_review_count   = 0
      dismiss_stale_reviews_on_push     = true
      require_code_owner_review         = false
      require_last_push_approval        = false
      required_review_thread_resolution = true
      # The ruleset also has `require_extra_approval_for_unattributed_changes` = true,
      # set by GitHub and unknown to provider 6.13. Importing kept it; after an apply
      # that updates this ruleset, check it with:
      # gh api repos/rlopc/pocs/rulesets/<id> --jq '.rules[].parameters'
    }

    required_status_checks {
      # The PR must be tested against the latest main.
      strict_required_status_checks_policy = true

      # One gate job per POC (README "Adding a POC"), not its individual jobs.
      required_check {
        context = "docconv"
      }
      # Repository hooks: whitespace, YAML/TOML, gitleaks, actionlint, zizmor.
      required_check {
        context = "repo"
      }
      # PR title convention (README "Commit messages").
      required_check {
        context = "pr-title"
      }
      # CodeQL default setup (api-only.sh).
      required_check {
        context = "Analyze (python)"
      }
      required_check {
        context = "Analyze (actions)"
      }
    }
  }
}
