from __future__ import annotations

from harness_contracts import (
    additional_context_for_contract,
    classify_prompt_intent,
    daily_context_for_workspace,
    detect_skill_match,
    emit,
    is_harness_workspace,
    read_hook_event,
    repo_root,
    reset_read_ledger,
    save_session,
)


def main() -> int:
    event = read_hook_event()
    root = repo_root(event.get("cwd"))
    prompt = str(event.get("prompt") or "")
    match = detect_skill_match(root, prompt)
    contract = match["contract"] if match else None
    session = {
        "session_id": event.get("session_id"),
        "turn_id": event.get("turn_id"),
        "active_skill": contract.get("skill") if contract else None,
        "intent_class": match.get("intent_class")
        if match
        else classify_prompt_intent(prompt),
        "skill_trigger": match.get("trigger") if match else None,
        "skill_trigger_type": match.get("trigger_type") if match else None,
        "read_contract_stop_required": bool(match.get("read_contract_stop_required"))
        if match
        else False,
        "mutating_tool_seen": False,
    }
    save_session(root, session)
    if is_harness_workspace(root):
        reset_read_ledger(root)
    daily_context = daily_context_for_workspace(root)
    if not contract:
        if daily_context:
            emit(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": daily_context,
                    }
                }
            )
        return 0
    additional_context = additional_context_for_contract(contract, root, match)
    if daily_context:
        additional_context = additional_context + "\n\n" + daily_context
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": additional_context,
            }
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
