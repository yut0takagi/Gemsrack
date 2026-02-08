def register(slack_app) -> None:  # noqa: ANN001
    @slack_app.command("/hello")
    def hello_command(ack, respond, command):  # noqa: ANN001
        ack()
        user_id = command.get("user_id")
        respond(f"Hello <@{user_id}>! (from Cloud Run)")

