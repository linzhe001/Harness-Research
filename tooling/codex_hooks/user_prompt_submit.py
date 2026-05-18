from __future__ import annotations

from harness_contracts import (
    additional_context_for_contract,
    classify_prompt_intent,
    contract_by_skill,
    daily_context_for_workspace,
    detect_skill_match,
    emit,
    is_continuation_prompt,
    is_harness_workspace,
    load_session_for_event,
    read_hook_event,
    repo_root,
    reset_read_ledger,
    save_session,
)


def continuation_match(root, prompt: str, event: dict) -> dict | None:
    if not is_continuation_prompt(prompt):
        return None
    previous = load_session_for_event(root, event)
    previous_session_id = previous.get("session_id")
    current_session_id = event.get("session_id")
    if not previous_session_id or not current_session_id:
        return None
    if previous_session_id != current_session_id:
        return None
    skill = previous.get("active_skill")
    if not isinstance(skill, str) or not skill:
        return None
    contract = contract_by_skill(root, skill)
    if not contract:
        return None
    return {
        "contract": contract,
        "skill": skill,
        "trigger": "continuation",
        "trigger_type": "continuation",
        "intent_class": previous.get("intent_class"),
        "read_contract_stop_required": bool(
            previous.get("read_contract_stop_required")
        ),
        "continued_from_previous_prompt": True,
    }


def main() -> int:
    event = read_hook_event()
    root = repo_root(event.get("cwd"))
    prompt = str(event.get("prompt") or "")
    match = continuation_match(root, prompt, event)
    continued = bool(match)
    if match is None:
        match = detect_skill_match(root, prompt)
    contract = match["contract"] if match else None
    if continued:
        session = load_session_for_event(root, event)
        session.pop("last_mutating_tool", None)
        session.pop("last_mutating_turn_id", None)
        session.update(
            {
                "session_id": event.get("session_id"),
                "turn_id": event.get("turn_id"),
                "active_skill": contract.get("skill") if contract else None,
                "intent_class": match.get("intent_class"),
                "skill_trigger": match.get("trigger"),
                "skill_trigger_type": match.get("trigger_type"),
                "read_contract_stop_required": bool(
                    match.get("read_contract_stop_required")
                ),
                "continued_from_previous_prompt": True,
                "continuation_prompt": prompt,
                "mutating_tool_seen": False,
            }
        )
    else:
        session = {
            "session_id": event.get("session_id"),
            "turn_id": event.get("turn_id"),
            "active_skill": contract.get("skill") if contract else None,
            "intent_class": match.get("intent_class")
            if match
            else classify_prompt_intent(prompt),
            "skill_trigger": match.get("trigger") if match else None,
            "skill_trigger_type": match.get("trigger_type") if match else None,
            "read_contract_stop_required": bool(
                match.get("read_contract_stop_required")
            )
            if match
            else False,
            "mutating_tool_seen": False,
        }
    save_session(root, session)
    if is_harness_workspace(root) and not continued:
        reset_read_ledger(root, event)
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
