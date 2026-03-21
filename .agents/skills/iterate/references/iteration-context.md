# Iteration Context Handling

Use this reference instead of a helper script when managing `.agents/state/`.

## State File Placement

- `iteration_log.json` remains at the repository root.
- Active iteration context lives under `.agents/state/` because it is volatile local state.
- Keep `.agents/state/` as a reserved local runtime directory.
- Context files inside it are still created only when local iteration context is needed.
- Persistent per-iteration context path:
  - `.agents/state/iterations/<iter-id>/context.json`
- Active context path:
  - `.agents/state/current_iteration.json`

## Startup Cleanup

Before any `$iterate` sub-command:

1. Check whether `.agents/state/current_iteration.json` exists.
2. If it does not exist, continue normally.
3. If it exists:
   - read `iteration_id`
   - read `iteration_log.json`
   - if that iteration is still `coding`, revert it to `planned`
   - if that iteration is `training` or `running`, keep the status unchanged
   - remove `.agents/state/current_iteration.json`
4. Tell the user that interrupted local context was cleaned up.

## Writing Context For `$iterate code`

1. Select the latest planned iteration.
2. Build the canonical payload:
   - `caller`
   - `sub_command`
   - `mode`
   - `iteration_id`
   - hypothesis and summary fields
   - config diff
   - best-iteration context when relevant
3. Write the payload to:
   - `.agents/state/iterations/<iter-id>/context.json`
   - `.agents/state/current_iteration.json`
   - create parent directories only when needed
4. After `$code-debug` returns, remove only `.agents/state/current_iteration.json`.
5. Keep the per-iteration context file for crash recovery and traceability.

## Refreshing Context For `$iterate eval`

When reusing an existing context:

1. Read `.agents/state/iterations/<iter-id>/context.json`.
2. Copy its current contents into `.agents/state/current_iteration.json`.
3. Update fields only if the eval step adds new analysis context.

## Status Summary

For status inspection, report:

- whether active context exists
- `iteration_id`
- `sub_command`
- `mode`
