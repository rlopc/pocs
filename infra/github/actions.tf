resource "github_actions_repository_permissions" "pocs" {
  repository      = github_repository.pocs.name
  enabled         = true
  allowed_actions = "all"
  # Every action must resolve to a full commit SHA. The workflows reference tags and
  # .github/workflows/actions.lock pins their commits, which satisfies this policy.
  sha_pinning_required = true
}

# Least privilege for GITHUB_TOKEN: read-only unless a workflow asks for more, and
# workflows cannot approve pull requests (they would satisfy review rules on their own).
resource "github_workflow_repository_permissions" "pocs" {
  repository                       = github_repository.pocs.name
  default_workflow_permissions     = "read"
  can_approve_pull_request_reviews = false
}
