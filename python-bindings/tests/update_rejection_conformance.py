"""Exercise default public update APIs only at deterministic pre-transport failure boundaries."""

import asyncio


def observe_update_rejection(fixture):
    """Require typed installed-version rejection or the native malformed-header builder error."""
    import classic_update

    if fixture["token"] != "synthetic\ninvalid":
        raise ValueError("only the synthetic invalid credential is permitted")
    if fixture["operation"] == "metadata":
        client = classic_update.GithubClient(
            fixture["owner"], fixture["repo"], fixture["token"]
        )
        return {"repoUrl": client.repo_url()}
    if fixture["operation"] == "notification":
        try:
            classic_update.check_app_notification(
                fixture["owner"], fixture["repo"], fixture["invalidVersion"]
            )
        except classic_update.ClassicNotificationInstalledVersionParseError:
            return {
                "boundary": "caller-validation",
                "error": "invalid-installed-version",
                "requestBuilt": False,
            }
        raise ValueError("invalid installed version was accepted")

    async def reject():
        """Await the real client; transport errors and successful requests are not accepted evidence."""
        client = classic_update.GithubClient(
            fixture["owner"], fixture["repo"], fixture["token"]
        )
        try:
            if fixture["operation"] == "latest":
                await client.get_latest_release()
            elif fixture["operation"] == "all":
                await client.get_all_releases(False, False)
            else:
                raise ValueError("unsupported rejection operation")
        except RuntimeError as error:
            if str(error) != "GitHub API error: HTTP error: builder error":
                raise
            return {
                "boundary": "request-builder",
                "error": "builder-error",
                "requestBuilt": False,
            }
        raise ValueError("malformed authorization header was accepted")

    return asyncio.run(reject())
