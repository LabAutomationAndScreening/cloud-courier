/*
 * ============== WARNING ==============================================================================
 * File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
 * See .config/.copier-managed-files.json for details.
 *
 * You are welcome to make changes to this file in your repo if they are custom to your project,
 * but if the change should be shared with other projects, please backport it to the template repo.
 * =====================================================================================================
 */
import { RuleTester } from "eslint";
import { describe, it } from "vitest";
import rule from "../../../../.config/eslint-rules/istanbul-ignore-if-must-throw.mjs";

RuleTester.describe = describe;
RuleTester.it = it;

const ruleTester = new RuleTester({
  languageOptions: { ecmaVersion: "latest", sourceType: "module" },
});

// RuleTester.run registers its own describe/it blocks and must be called at module top level, not inside a hook.
// eslint-disable-next-line vitest/require-hook
ruleTester.run("istanbul-ignore-if-must-throw", rule, {
  valid: [
    {
      name: "braceless throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (typeof x !== "string") throw new Error("bad");
          return x;
        }`,
    },
    {
      name: "block throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            throw new Error("bad");
          }
        }`,
    },
    {
      name: "silent return allowed with return-ok escape carrying a reason",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve return-ok: absence is valid */
          if (!x) return;
        }`,
    },
    {
      name: "silent return allowed with return-ok escape whose reason has no colon",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve return-ok absence is valid */
          if (!x) return;
        }`,
    },
    {
      name: "if without an istanbul ignore comment is untouched",
      code: `function f(x) {
          if (!x) return;
        }`,
    },
    {
      name: "istanbul ignore next on a non-if statement is left alone",
      code: `/* istanbul ignore next -- @preserve */
        function unreachable() {
          return 1;
        }`,
    },
    {
      name: "istanbul ignore else is left alone",
      code: `function f(x) {
          /* istanbul ignore else -- @preserve */
          if (!x) {
            doSomething();
          } else {
            doOther();
          }
        }`,
    },
    {
      name: "nested if/else where both branches always throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            if (x === null) {
              throw new Error("null");
            } else {
              throw new Error("bad");
            }
          }
        }`,
    },
    {
      name: "non-exiting nested if followed by a real throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            if (x === null) {
              logIt();
            }
            throw new Error("bad");
          }
        }`,
    },
    {
      name: "try and catch both always throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            try {
              throw new Error("a");
            } catch {
              throw new Error("b");
            }
          }
        }`,
    },
    {
      name: "finally always throws regardless of the try block",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            try {
              doStuff();
            } finally {
              throw new Error("bad");
            }
          }
        }`,
    },
    {
      name: "switch with a default where every case always throws",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            switch (x) {
              case 1:
                throw new Error("one");
              default:
                throw new Error("other");
            }
          }
        }`,
    },
    {
      name: "break inside switch cases is absorbed, real throw follows",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            switch (x) {
              case 1:
                doStuff();
                break;
              default:
                doOther();
            }
            throw new Error("bad");
          }
        }`,
    },
    {
      name: "return inside a nested function belongs to that function, real throw follows",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            const describe = () => {
              return "missing";
            };
            throw new Error(describe());
          }
        }`,
    },
    {
      name: "break inside a nested loop is absorbed, real throw follows",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            for (const item of items) {
              if (bad(item)) break;
            }
            throw new Error("bad");
          }
        }`,
    },
    {
      name: "nested ignored ifs that both throw",
      code: `function f(a, b) {
          /* istanbul ignore if -- @preserve */
          if (!a) {
            /* istanbul ignore if -- @preserve */
            if (!b) throw new Error("b");
            throw new Error("a");
          }
        }`,
    },
    {
      name: "nested return-ok if whose break stays inside the outer branch",
      code: `function f(a, items) {
          /* istanbul ignore if -- @preserve */
          if (!a) {
            for (const item of items) {
              /* istanbul ignore if -- @preserve return-ok: stop scanning */
              if (!item) break;
            }
            throw new Error("a");
          }
        }`,
    },
  ],
  invalid: [
    {
      name: "nested ignored if throws but the outer one falls through after it",
      code: `function f(a, b) {
          /* istanbul ignore if -- @preserve */
          if (!a) {
            /* istanbul ignore if -- @preserve */
            if (!b) throw new Error("b");
            log(a);
          }
        }`,
      errors: [{ messageId: "mustThrow", line: 3 }],
    },
    {
      name: "nested ignored if returns silently; reported on the inner if only",
      code: `function f(a, b) {
          /* istanbul ignore if -- @preserve */
          if (!a) {
            /* istanbul ignore if -- @preserve */
            if (!b) return;
            throw new Error("a");
          }
        }`,
      errors: [{ messageId: "mustThrow", line: 5 }],
    },
    {
      name: "nested return-ok if excuses itself but not the outer branch it escapes",
      code: `function f(a, b) {
          /* istanbul ignore if -- @preserve */
          if (!a) {
            /* istanbul ignore if -- @preserve return-ok: b absent is fine */
            if (!b) return;
            throw new Error("a");
          }
        }`,
      errors: [{ messageId: "mustThrow", line: 3 }],
    },
    {
      name: "every violating ignored if in a file is reported, a compliant one between them is not",
      code: `function f(a, b, c) {
          /* istanbul ignore if -- @preserve */
          if (!a) return;
          /* istanbul ignore if -- @preserve */
          if (!b) throw new Error("b");
          /* istanbul ignore if -- @preserve */
          if (!c) {
            log(c);
          }
        }`,
      errors: [
        { messageId: "mustThrow", line: 3 },
        { messageId: "mustThrow", line: 7 },
      ],
    },
    {
      name: "silent return under istanbul ignore if",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) return;
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "return-ok escape with no reason at all",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve return-ok */
          if (!x) return;
        }`,
      errors: [{ messageId: "escapeNeedsReason" }],
    },
    {
      name: "return-ok escape whose colon is followed by nothing",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve return-ok:   */
          if (!x) return;
        }`,
      errors: [{ messageId: "escapeNeedsReason" }],
    },
    {
      name: "hyphen-prefixed lookalike is not a return-ok escape",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve not-return-ok: absence is valid */
          if (!x) return;
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "hyphen-suffixed lookalike is not a return-ok escape",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve return-ok-ish */
          if (!x) return;
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "reasonless return-ok on a branch that throws anyway",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve return-ok */
          if (!x) throw new Error("bad");
        }`,
      errors: [{ messageId: "escapeNeedsReason" }],
    },
    {
      name: "block that does not end in throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            doSomething();
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "silent return under istanbul ignore next on an if",
      code: `function f(x) {
          /* istanbul ignore next -- @preserve */
          if (!x) return;
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "recoverable return reachable before a final throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            if (x === null) return;
            throw new Error("bad");
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "nested if throws but its else silently returns",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            if (x === null) {
              throw new Error("null");
            } else {
              return;
            }
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "nested block statement returns silently before a later throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            {
              return;
            }
            throw new Error("bad");
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "recoverable break reachable before a final throw",
      code: `function f(x) {
          for (;;) {
            /* istanbul ignore if -- @preserve */
            if (!x) {
              if (x === null) break;
              throw new Error("bad");
            }
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "recoverable continue reachable before a final throw",
      code: `function f(x) {
          for (;;) {
            /* istanbul ignore if -- @preserve */
            if (!x) {
              if (x === null) continue;
              throw new Error("bad");
            }
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "return inside a nested loop reaches past a later throw",
      code: `function f(x) {
          /* istanbul ignore if -- @preserve */
          if (!x) {
            for (const item of items) {
              if (bad(item)) return;
            }
            throw new Error("bad");
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
    {
      name: "continue inside a switch case is not absorbed by the switch",
      code: `function f(x) {
          for (;;) {
            /* istanbul ignore if -- @preserve */
            if (!x) {
              switch (x) {
                case 1:
                  continue;
                default:
                  break;
              }
              throw new Error("bad");
            }
          }
        }`,
      errors: [{ messageId: "mustThrow" }],
    },
  ],
});
