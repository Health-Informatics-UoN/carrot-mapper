interface Project {
  id: number;
  name: string;
  members: User[];
  admins: User[];
  created_at: Date;
}
