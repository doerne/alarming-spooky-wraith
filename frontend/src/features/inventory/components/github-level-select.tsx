import type { UseFormRegisterReturn } from "react-hook-form";

import { GITHUB_LEVELS } from "../model/github-schema";

interface GithubLevelSelectProps {
  id: string;
  testId: string;
  registration: UseFormRegisterReturn;
  emptyLabel?: string;
}

/** Auswahl einer Risikostufe; ``emptyLabel`` ergänzt eine Option für „keine“. */
export function GithubLevelSelect({
  id,
  testId,
  registration,
  emptyLabel,
}: GithubLevelSelectProps) {
  return (
    <select
      id={id}
      data-testid={testId}
      className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
      {...registration}
    >
      {emptyLabel !== undefined && <option value="">{emptyLabel}</option>}
      {GITHUB_LEVELS.map((level) => (
        <option key={level} value={level}>
          {level}
        </option>
      ))}
    </select>
  );
}
