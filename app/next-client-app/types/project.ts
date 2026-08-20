interface Project {
  id: number;
  name: string;
  description: string | null;
  members: User[];
  admins: User[];
  created_at: Date;
}

interface ProjectName {
  id: number;
  name: string;
}
