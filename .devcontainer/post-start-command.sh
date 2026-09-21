#!/bin/bash
set -ex

# For some reason the directory is not setup correctly and causes build of devcontainer to fail since
# it doesn't have access to the workspace directory. This can normally be done in post-start-command
script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(CDPATH='' cd -- "$script_dir/.." && pwd)"
git config --global --add safe.directory "$repo_root"
# bd >=1.0 warns on every command unless .beads is owner-only, and on-create's group-writable chmod over .claude
# undoes what bd init sets. Runs before the bd calls below so their output is clean too.
if [ -d "$repo_root/.claude/.beads" ]; then
    chmod 700 "$repo_root/.claude/.beads"
fi
pre-commit run merge-claude-settings -a
if ! bd ready; then
	echo "It's likely the Dolt server has not yet been initialized to support beads, running that now" # TODO: figure out a better way to match this specific scenario than just a non-zero exit code...but beads still seems like in high flux right now so not sure what to tie it to
    # the 'stealth' flag is just the only way I could figure out how to stop it from modifying AGENTS.md...if there's another way to avoid that, then fine.  Even without the stealth flag though, files inside the .claude/beads directory get modified, so restoring them at the end to what was set in git...these shouldn't really need to change regularly
    # trying to set 'prefix' to nothing doesn't seem to work (it just acts like the prefix flag wasn't there), so just setting to 'work' as an arbitrary name
    # --server is required as of bd 1.0: without it, init resolves to embedded dolt and hard-fails because the BEADS_DOLT_SERVER_* envvars are set
    rm -rf .claude/.beads && bd init --server --server-host="$BEADS_DOLT_SERVER_HOST" --database="$BEADS_DOLT_SERVER_DATABASE" --skip-hooks --stealth --prefix=work </dev/null
    # Best effort: a freshly generated repo has nothing tracked under .claude/.beads, and the failed pathspec would
    # otherwise trip 'set -e' and abandon the rest of this script
    git -c core.hooksPath=/dev/null restore --source=HEAD --staged --worktree .claude/.beads || true
fi

# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-base-template.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
