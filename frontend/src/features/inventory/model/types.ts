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
}

export interface ApplicationDetail extends Application {
  components: Component[];
}

export interface ApplicationFinding {
  advisoryId: string;
  cveId: string | null;
  title: string;
  componentId: number;
  componentName: string;
  componentVersion: string;
  riskScore: number;
  riskLevel: string;
  fixVersion: string | null;
  status: string;
}
