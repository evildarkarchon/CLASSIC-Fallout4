# Update decision fixtures

Authored valid strict semantic-version examples cover newer, equal, older and prerelease-to-stable. These call only GithubClient.has_update (plus Node standalone hasUpdate and CXX github_has_update); clients never fetch releases, manifests or assets. Construction reads optional local credentials but no request uses them. CXX returns false for invalid-version errors, so invalid inputs remain in existing adapter tests and earn no shared error credit. No network-dependent update orchestration receives conformance credit.
