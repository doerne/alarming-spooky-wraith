import type { ReactNode } from "react";

const HTTP_URL = /^https?:\/\//i;

interface SafeLinkProps {
  href: string;
  testId: string;
  children?: ReactNode;
}

/** Externe Links nur für http(s); alles andere (z. B. javascript:) bleibt reiner Text. */
export function SafeLink({ href, testId, children }: SafeLinkProps) {
  const label = children ?? href;
  if (!HTTP_URL.test(href)) {
    return (
      <span className="break-all text-muted-foreground" data-testid={testId}>
        {label}
      </span>
    );
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="break-all text-primary hover:underline"
      data-testid={testId}
    >
      {label}
    </a>
  );
}
