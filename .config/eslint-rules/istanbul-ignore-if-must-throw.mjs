/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
/*
 * Enforces the defensive-assertion contract for coverage-ignored branches:
 *
 * A branch marked `istanbul ignore if` (or `istanbul ignore next` when it sits on
 * an `if`) must throw: per ESLint's code path analysis, the end of the branch is
 * unreachable and no reachable return/break/continue inside it targets a construct
 * outside it. Coverage-ignoring a guard means "this is unreachable"; a silent
 * `return` there hides a real bug instead of surfacing it. If the absence is a
 * legitimate state rather than a contract violation, the author opts out with
 * `return-ok <reason>` in the ignore comment (a colon after the token is optional) —
 * "cannot happen" is what the throw is for, not what the escape is for. The reason is
 * required rather than conventional, since a bare `return-ok` is indistinguishable
 * from silencing the guard.
 * Ignore comments on anything other than an `if` are left alone — the rule
 * only makes a claim about branches whose shape it can verify.
 */

const IGNORE_IF_OR_NEXT = /istanbul ignore (?:if|next)\b/;
// `return-ok` contains a hyphen, so `\b` would accept one as a boundary and read the token out of
// `not-return-ok`; the delimiter must exclude hyphens on both sides.
const RETURN_OK = /(?<![-\w])return-ok(?![-\w])/;
// The reason may not start with the colon, or `return-ok:` would backtrack into being its own reason.
const RETURN_OK_WITH_REASON = /(?<![-\w])return-ok(?![-\w]):?\s*[^\s:]/;

const LOOP_TYPES = new Set(["ForStatement", "ForInStatement", "ForOfStatement", "WhileStatement", "DoWhileStatement"]);
const SILENT_EXIT_TYPES = new Set(["ReturnStatement", "BreakStatement", "ContinueStatement"]);

function isExitTarget(exit, ancestor) {
  if (exit.label !== null) {
    return ancestor.type === "LabeledStatement" && ancestor.label.name === exit.label.name;
  }
  if (exit.type === "BreakStatement") return LOOP_TYPES.has(ancestor.type) || ancestor.type === "SwitchStatement";
  return LOOP_TYPES.has(ancestor.type);
}

function leavesBranch(exit, branch) {
  if (exit.type === "ReturnStatement") return true;
  for (let cur = exit.parent; cur !== branch.parent; cur = cur.parent) {
    if (isExitTarget(exit, cur)) return false;
  }
  return true;
}

/** @type {import("eslint").Rule.RuleModule} */
export default {
  meta: {
    type: "problem",
    docs: {
      description:
        "Require `istanbul ignore if` branches to throw a defensive assertion naming the violated invariant",
    },
    schema: [],
    messages: {
      mustThrow:
        '`istanbul ignore if` claims this branch cannot be reached, so it must throw and name the invariant that was violated — a silent exit hides exactly the bug the guard exists to catch. `return-ok` is not a shortcut for "cannot happen": use it only when the absence is a legitimate state the code tolerates, and say in the comment why it is legitimate.',
      escapeNeedsReason:
        "A `return-ok` escape must say why the absence is legitimate, as `return-ok <reason>`. The escape claims this branch is a state the code tolerates rather than a violated invariant, and that claim is the reviewer's only evidence the guard was not simply silenced.",
    },
  },
  create(context) {
    const sourceCode = context.sourceCode;
    const segmentStacks = [];
    // Ignored ifs can nest; depth-first traversal keeps the innermost one on top.
    const branchStack = [];

    function isReachable() {
      return [...segmentStacks.at(-1)].some((segment) => segment.reachable);
    }

    function report(entry) {
      if (entry.reported) return;
      entry.reported = true;
      context.report({ node: entry.node, messageId: "mustThrow" });
    }

    function onSilentExit(node) {
      const entry = branchStack.at(-1);
      // Depth check keeps exits inside a nested function (its own code path) from counting.
      if (entry === undefined || entry.depth !== segmentStacks.length) return;
      if (isReachable() && leavesBranch(node, entry.consequent)) report(entry);
    }

    return {
      onCodePathStart() {
        segmentStacks.push(new Set());
      },
      onCodePathEnd() {
        segmentStacks.pop();
      },
      onCodePathSegmentStart(segment) {
        segmentStacks.at(-1).add(segment);
      },
      onCodePathSegmentEnd(segment) {
        segmentStacks.at(-1).delete(segment);
      },
      onUnreachableCodePathSegmentStart(segment) {
        segmentStacks.at(-1).add(segment);
      },
      onUnreachableCodePathSegmentEnd(segment) {
        segmentStacks.at(-1).delete(segment);
      },
      IfStatement(node) {
        const leading = sourceCode.getCommentsBefore(node);
        const ignoreComment = leading.find((comment) => IGNORE_IF_OR_NEXT.test(comment.value));
        if (ignoreComment === undefined) return;
        if (RETURN_OK.test(ignoreComment.value)) {
          if (RETURN_OK_WITH_REASON.test(ignoreComment.value)) return;
          context.report({ node, messageId: "escapeNeedsReason" });
          return;
        }
        branchStack.push({ node, consequent: node.consequent, depth: segmentStacks.length, reported: false });
      },
      ":statement:exit"(node) {
        if (node !== branchStack.at(-1)?.consequent) return;
        const entry = branchStack.pop();
        // ESLint applies a throw/return/break/continue to the code path only after emitting that
        // node's :exit, so for a braceless consequent the segments seen here are still the ones
        // from before it. A bare throw satisfies the rule; a bare silent exit was already judged
        // by onSilentExit on entry.
        const { type } = entry.consequent;
        if (type === "ThrowStatement" || SILENT_EXIT_TYPES.has(type)) return;
        if (isReachable()) report(entry);
      },
      ReturnStatement: onSilentExit,
      BreakStatement: onSilentExit,
      ContinueStatement: onSilentExit,
    };
  },
};
