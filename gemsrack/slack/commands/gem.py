from __future__ import annotations

from ...gems.store import build_store
from ...gems.service import handle_gem_command


def register(slack_app) -> None:  # noqa: ANN001
    store = build_store()

    @slack_app.command("/gem")
    def gem_command(ack, respond, command):  # noqa: ANN001
        ack()
        team_id = command.get("team_id") or command.get("team_domain") or "unknown"
        user_id = command.get("user_id")
        text = command.get("text", "")

        result = handle_gem_command(store=store, team_id=team_id, user_id=user_id, text=text)

        if result.public:
            respond(result.message, response_type="in_channel")
        else:
            respond(result.message)

