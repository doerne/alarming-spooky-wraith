import { RuleTester } from "eslint";
import { afterAll, describe, it } from "vitest";
import rule from "./require-testid.js";

RuleTester.afterAll = afterAll;
RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const ruleTester = new RuleTester({
  languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
});

ruleTester.run("require-testid", rule, {
  valid: [
    '<button data-testid="login-btn-submit">OK</button>',
    '<Button data-testid="todos-btn-create">OK</Button>',
    "<Button data-testid={`todos-btn-delete-${id}`}>X</Button>",
    "<button {...props} />",
    "<div>kein relevantes Element</div>",
    '<Field data-testid="nicht geprüft" />',
    {
      code: '<button id="login-btn-submit" />',
      options: [{ attribute: "id" }],
    },
  ],
  invalid: [
    {
      code: "<button>OK</button>",
      errors: [{ messageId: "missing" }],
    },
    {
      code: "<Input />",
      errors: [{ messageId: "missing" }],
    },
    {
      code: '<Button data-testid="submit">OK</Button>',
      errors: [{ messageId: "invalidFormat" }],
    },
    {
      code: '<Button data-testid="Todos_Btn_Create">OK</Button>',
      errors: [{ messageId: "invalidFormat" }],
    },
    {
      code: '<Card data-testid="x" />',
      options: [{ elements: ["Card"] }],
      errors: [{ messageId: "invalidFormat" }],
    },
  ],
});
