from __future__ import annotations

from harness_contracts import (
    ENFORCEMENT_CONTEXT_ONLY,
    ENFORCEMENT_NONE,
    additional_context_for_candidate,
    additional_context_for_contract,
    classify_prompt_intent,
    contract_by_skill,
    daily_context_for_workspace,
    detect_skill_match,
    emit,
    is_continuation_prompt,
    is_harness_workspace,
    load_session_for_event,
    notice_once,
    read_hook_event,
    repo_root,
    reset_read_ledger,
    save_session,
    truncate_user_prompt_context,
)


def _candidate_continuation_prompt(prompt: str) -> bool:
    text = prompt.strip()
    return bool(
        is_continuation_prompt(text)
        or "按这个方案" in text
        or "按上面" in text
        or "直接落地" in text
        or "继续落地" in text
    )


def continuation_match(root, prompt: str, event: dict) -> dict | None:
    if not _candidate_continuation_prompt(prompt):
        return None
    previous = load_session_for_event(root, event)
    previous_session_id = previous.get("session_id")
    current_session_id = event.get("session_id")
    if not previous_session_id or not current_session_id:
        return None
    if previous_session_id != current_session_id:
        return None
    skill = previous.get("active_skill")
    if isinstance(skill, str) and skill:
        contract = contract_by_skill(root, skill)
        if not contract:
            return None
        return {
            "contract": contract,
            "skill": skill,
            "candidate_contract": None,
            "candidate_skill": None,
            "trigger": "continuation",
            "trigger_type": "continuation",
            "intent_class": previous.get("intent_class"),
            "enforcement_mode": previous.get("enforcement_mode"),
            "read_contract_stop_required": bool(
                previous.get("read_contract_stop_required")
            ),
            "continued_from_previous_prompt": True,
        }

    candidate_skill = previous.get("candidate_skill")
    if not isinstance(candidate_skill, str) or not candidate_skill:
        return None
    contract = contract_by_skill(root, candidate_skill)
    if not contract:
        return None
    return {
        "contract": None,
        "skill": None,
        "candidate_contract": contract,
        "candidate_skill": candidate_skill,
        "candidate_trigger": previous.get("candidate_trigger"),
        "candidate_trigger_type": previous.get("candidate_trigger_type"),
        "candidate_reason": (
            "continued advisory context; tool-time policy checks concrete writes"
        ),
        "trigger": "candidate_continuation",
        "trigger_type": "continuation",
        "intent_class": previous.get("intent_class")
        or classify_prompt_intent(prompt),
        "enforcement_mode": ENFORCEMENT_CONTEXT_ONLY,
        "read_contract_stop_required": False,
        "continued_from_previous_prompt": True,
        "pending_candidate_activation": True,
    }


def emit_user_prompt_context(context: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": truncate_user_prompt_context(context),
            }
        }
    )


def main() -> int:
    event = read_hook_event()
    root = repo_root(event.get("cwd"))
    prompt = str(event.get("prompt") or "")
    match = continuation_match(root, prompt, event)
    continued = bool(match)
    if match is None:
        match = detect_skill_match(root, prompt)
    contract = match.get("contract") if match else None
    candidate_contract = match.get("candidate_contract") if match else None
    if continued:
        session = load_session_for_event(root, event)
        session.pop("last_mutating_tool", None)
        session.pop("last_mutating_turn_id", None)
        session.update(
            {
                "session_id": event.get("session_id"),
                "turn_id": event.get("turn_id"),
                "active_skill": contract.get("skill") if contract else None,
                "candidate_skill": match.get("candidate_skill"),
                "candidate_trigger": match.get("candidate_trigger"),
                "candidate_trigger_type": match.get("candidate_trigger_type"),
                "candidate_reason": match.get("candidate_reason"),
                "intent_class": match.get("intent_class"),
                "skill_trigger": match.get("trigger"),
                "skill_trigger_type": match.get("trigger_type"),
                "enforcement_mode": match.get("enforcement_mode")
                or ENFORCEMENT_NONE,
                "read_contract_stop_required": bool(
                    match.get("read_contract_stop_required")
                ),
                "continued_from_previous_prompt": True,
                "continuation_prompt": prompt,
                "pending_candidate_activation": bool(
                    match.get("pending_candidate_activation")
                ),
                "mutating_tool_seen": False,
            }
        )
    else:
        session = {
            "session_id": event.get("session_id"),
            "turn_id": event.get("turn_id"),
            "active_skill": contract.get("skill") if contract else None,
            "candidate_skill": match.get("candidate_skill") if match else None,
            "candidate_trigger": match.get("candidate_trigger") if match else None,
            "candidate_trigger_type": match.get("candidate_trigger_type")
            if match
            else None,
            "candidate_reason": match.get("candidate_reason") if match else None,
            "intent_class": match.get("intent_class")
            if match
            else classify_prompt_intent(prompt),
            "skill_trigger": match.get("trigger") if match else None,
            "skill_trigger_type": match.get("trigger_type") if match else None,
            "enforcement_mode": match.get("enforcement_mode")
            if match
            else ENFORCEMENT_NONE,
            "read_contract_stop_required": bool(
                match.get("read_contract_stop_required")
            )
            if match
            else False,
            "pending_candidate_activation": bool(
                match.get("pending_candidate_activation")
            )
            if match
            else False,
            "mutating_tool_seen": False,
        }
    save_session(root, session)
    if is_harness_workspace(root) and not continued:
        reset_read_ledger(root, event)
    daily_context = daily_context_for_workspace(root)
    contexts = []
    if not contract:
        if candidate_contract:
            if notice_once(
                root,
                event,
                "candidate_context",
                [
                    str(match.get("candidate_skill")),
                    str(match.get("candidate_trigger")),
                    str(match.get("intent_class")),
                ],
            ):
                contexts.append(
                    additional_context_for_candidate(candidate_contract, match)
                )
            if daily_context and notice_once(
                root,
                event,
                "workspace_capsule",
                ["AGENTS.md", "CLAUDE.md"],
                scope="session",
            ):
                contexts.append(daily_context)
            if contexts:
                emit_user_prompt_context("\n\n".join(contexts))
            return 0
        if daily_context and notice_once(
            root,
            event,
            "workspace_capsule",
            ["AGENTS.md", "CLAUDE.md"],
            scope="session",
        ):
            emit_user_prompt_context(daily_context)
        return 0
    if notice_once(
        root,
        event,
        "contract_context",
        [str(contract.get("skill")), str(match.get("trigger") if match else "")],
    ):
        contexts.append(additional_context_for_contract(contract, root, match))
    if daily_context and notice_once(
        root,
        event,
        "workspace_capsule",
        ["AGENTS.md", "CLAUDE.md"],
        scope="session",
    ):
        contexts.append(daily_context)
    if contexts:
        emit_user_prompt_context("\n\n".join(contexts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
