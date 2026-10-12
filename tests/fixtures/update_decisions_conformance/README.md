# Update decision fixtures

Authored valid strict semantic-version examples cover newer, equal, older and prerelease-to-stable. These call only GithubClient.has_update; clients never fetch releases, manifests or assets. Construction reads optional local credentials but no request uses them. No network-dependent update orchestration receives conformance credit.
