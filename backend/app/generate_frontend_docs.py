import json

from app.main import app


def main():
    schema = app.openapi()

    with open("app/FRONTEND_INTEGRATION.md", "w") as f:
        f.write("# REALITY.EXE Frontend Integration Contract\n\n")
        f.write(
            "This document provides the integration contract for connecting the frontend to the REALITY.EXE backend.\n\n"
        )

        f.write("## General Guidelines\n\n")
        f.write("### Auth Token Handling\n")
        f.write(
            "- **Storage**: Store the JWT token securely (e.g., in memory or HttpOnly cookies for web, secure storage for mobile).\n"
        )
        f.write(
            "- **Usage**: All authenticated routes require the `Authorization: Bearer <token>` header.\n"
        )
        f.write(
            "- **Refresh Behavior**: Not currently implemented. On token expiry (401), the user must re-authenticate (login).\n\n"
        )

        f.write("### Image Upload\n")
        f.write(
            "- Use `multipart/form-data` with the field `file` to upload evidence to `POST /api/v1/evidence/upload`.\n"
        )
        f.write(
            "- Images must be valid JPEGs/PNGs, max size configured by the server (default 10MB).\n\n"
        )

        f.write("### Quest State Polling\n")
        f.write(
            "- Quest state transitions are synchronous from the frontend's perspective. No polling is required. Call `/api/v1/quests/{id}/start`, `/api/v1/quests/{id}/pocket`, etc.\n"
        )
        f.write(
            '- AI analysis (`/api/v1/evidence/{id}/analyze`) is synchronous. Display a loading spinner (e.g. "Consulting the Game Master...") until it returns.\n\n'
        )

        f.write("### Loading States\n")
        f.write(
            "- Use playful system-style messages during API calls (e.g., `WORLD GENERATING...`, `CONSULTING THE GAME MASTER...`, `REALITY SYNCING...`).\n\n"
        )

        f.write("### Error States\n")
        f.write(
            '- Errors follow a strict envelope: `{"error": {"code": "...", "message": "...", "request_id": "..."}}`.\n'
        )
        f.write("- Code `UNAUTHORIZED` or HTTP 401 should redirect to login.\n")
        f.write("- Handle `VALIDATION_ERROR` (HTTP 422) gracefully with UI feedback.\n\n")

        f.write("### Offline / Idempotency Behavior\n")
        f.write(
            "- Endpoints like `complete` and `analyze_evidence` are idempotent. Retrying them after a network failure will return the success response without double-awarding XP or failing.\n"
        )
        f.write(
            "- During offline Pocket Mode, store completion evidence locally and attempt to upload/analyze when network returns.\n\n"
        )

        f.write("## API Endpoints\n\n")

        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                f.write(f"### {operation.get('summary', path)}\n\n")
                f.write(f"**METHOD:** `{method.upper()}`\n\n")
                f.write(f"**URL:** `{path}`\n\n")

                auth_req = "Bearer Token Required" if "security" in operation else "None"
                f.write(f"**AUTH:** {auth_req}\n\n")

                # Try to construct a simple request example
                req_example = "None"
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    if "application/json" in content:
                        ref = content["application/json"].get("schema", {}).get("$ref", "")
                        if ref:
                            schema_name = ref.split("/")[-1]
                            props = schema["components"]["schemas"][schema_name].get(
                                "properties", {}
                            )
                            example_dict = {k: "..." for k in props.keys()}
                            req_example = "```json\n" + json.dumps(example_dict, indent=2) + "\n```"
                    elif "multipart/form-data" in content:
                        req_example = "Multipart Form Data: `file` field containing image bytes."
                    elif "application/octet-stream" in content:
                        req_example = "Binary data containing image bytes."

                f.write(f"**REQUEST:**\n{req_example}\n\n")

                # Responses
                f.write("**RESPONSES & ERRORS:**\n")
                for status, resp in operation.get("responses", {}).items():
                    desc = resp.get("description", "")
                    f.write(f"- `{status}`: {desc}\n")
                f.write("\n---\n\n")


if __name__ == "__main__":
    main()
