def register(slack_app) -> None:  # noqa: ANN001
    @slack_app.event("app_mention")
    def handle_mention(event, say):  # noqa: ANN001
        user = event.get("user")
        say(f"呼んだ？ <@{user}>")

