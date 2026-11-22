import { z } from "zod";

import type { GitHubLevel } from "./types";

export const GITHUB_LEVELS: readonly GitHubLevel[] = ["kritisch", "hoch", "mittel", "niedrig"];

/** Owner/Repo wie im Backend; ``.`` und ``..`` als Repo-Name sind ungültig. */
const REPOSITORY_PATTERN = /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/;
const RESERVED_NAME_PATTERN = /\/\.{1,2}$/;

export function isValidRepository(value: string): boolean {
  return REPOSITORY_PATTERN.test(value) && !RESERVED_NAME_PATTERN.test(value);
}

export const githubSettingsSchema = z.object({
  repository: z.string().refine((value) => value === "" || isValidRepository(value), {
    message: "Format owner/repo, z. B. acme/shop",
  }),
  autoIssueMinLevel: z.enum(["", ...GITHUB_LEVELS] as const),
});
export type GitHubSettingsInput = z.infer<typeof githubSettingsSchema>;

export const githubCreateSchema = z.object({
  minLevel: z.enum(GITHUB_LEVELS as [GitHubLevel, ...GitHubLevel[]]),
});
export type GitHubCreateInput = z.infer<typeof githubCreateSchema>;
