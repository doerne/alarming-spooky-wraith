export interface Application {
  id: number;
  name: string;
  description: string;
}

export interface Component {
  id: number;
  applicationId: number;
  name: string;
  version: string;
  category: string;
  ecosystem: string | null;
  direct: boolean;
  sbomId: number | null;
  checked: boolean;
}

export interface ApplicationDetail extends Application {
  components: Component[];
  githubRepository: string | null;
  autoIssueMinLevel: GitHubLevel | null;
  githubSyncedAt: string | null;
  githubSyncMessage: string;
}

/** Risikostufen für GitHub-Automatik und Issue-Anlage (wie im Backend). */
export type GitHubLevel = "kritisch" | "hoch" | "mittel" | "niedrig";

export interface ApplicationFinding {
  advisoryId: string;
  cveId: string | null;
  title: string;
  componentId: number;
  componentName: string;
  componentVersion: string;
  ecosystem: string | null;
  riskScore: number;
  riskLevel: string;
  fixVersion: string | null;
  status: string;
  issueUrl: string | null;
}
