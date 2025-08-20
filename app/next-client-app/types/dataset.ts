interface DatasetStrict {
  id: number;
  name: string;
}

interface DataSet extends DatasetStrict {
  hidden: boolean;
  visibility: string;
  created_at: string;
  data_partner: DataPartner;
  admins: string[];
}

interface DataPartner {
  id: number;
  name: string;
  created_at: Date;
  updated_at: Date;
}

interface DataSetSRList {
  id: number;
  created_at: Date;
  updated_at: Date;
  name: string;
  visibility: string;
  hidden: boolean | null;
  data_partner: DataPartner;
  viewers: User[];
  admins: User[];
  editors: User[];
  projects: Project[];
}

export interface User {
  id: number;
  username: string;
}
