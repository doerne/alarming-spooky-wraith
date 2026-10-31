/**
 * Erzwingt data-testid an allen relevanten UI-Elementen.
 *
 * Optionen:
 *   elements  – Liste der Tags/Komponenten, die eine ID brauchen
 *   attribute – Name des Attributs (Standard: "data-testid", alternativ "id")
 *   pattern   – Regex für feste Werte (Standard: <feature>-<element>-<zweck>)
 *
 * Spread-Props ({...props}) gelten als erfüllt, damit Wrapper-Komponenten
 * die ID von außen durchreichen können.
 */

export const DEFAULT_ELEMENTS = [
  // native Elemente
  "button", "input", "select", "textarea", "a", "form",
  "table", "dialog", "main", "nav", "section", "header",
  // shadcn/ui-Komponenten
  "Button", "Input", "Textarea", "Checkbox", "Switch", "RadioGroup",
  "Slider", "SelectTrigger", "TabsTrigger", "DialogContent",
  "SheetContent", "DropdownMenuItem", "Table", "Card",
];

export const DEFAULT_PATTERN = "^[a-z][a-z0-9]*(-[a-z0-9]+){2,}$";

function elementName(node) {
  return node.name.type === "JSXIdentifier" ? node.name.name : null;
}

function findAttribute(node, attribute) {
  return node.attributes.find(
    (attr) => attr.type === "JSXAttribute" && attr.name.name === attribute,
  );
}

function hasSpread(node) {
  return node.attributes.some((attr) => attr.type === "JSXSpreadAttribute");
}

function literalValue(attr) {
  const { value } = attr;
  if (value?.type === "Literal" && typeof value.value === "string") return value.value;
  const expression = value?.type === "JSXExpressionContainer" ? value.expression : null;
  if (expression?.type === "Literal" && typeof expression.value === "string") {
    return expression.value;
  }
  return null;
}

/** @type {import("eslint").Rule.RuleModule} */
export default {
  meta: {
    type: "problem",
    docs: { description: "Relevante UI-Elemente brauchen ein data-testid nach Namensschema" },
    schema: [
      {
        type: "object",
        properties: {
          elements: { type: "array", items: { type: "string" } },
          attribute: { type: "string" },
          pattern: { type: "string" },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      missing: '<{{element}}> braucht {{attribute}}="<feature>-<element>-<zweck>".',
      invalidFormat:
        '{{attribute}}="{{value}}" folgt nicht dem Schema <feature>-<element>-<zweck> (kebab-case).',
    },
  },

  create(context) {
    const options = context.options[0] ?? {};
    const elements = new Set(options.elements ?? DEFAULT_ELEMENTS);
    const attribute = options.attribute ?? "data-testid";
    const pattern = new RegExp(options.pattern ?? DEFAULT_PATTERN);

    return {
      JSXOpeningElement(node) {
        const element = elementName(node);
        if (!element || !elements.has(element)) return;

        const attr = findAttribute(node, attribute);
        if (!attr) {
          if (!hasSpread(node)) {
            context.report({ node, messageId: "missing", data: { element, attribute } });
          }
          return;
        }

        const value = literalValue(attr);
        if (value !== null && !pattern.test(value)) {
          context.report({ node: attr, messageId: "invalidFormat", data: { attribute, value } });
        }
      },
    };
  },
};
