interface Profile {
  data_partner: DataPartner | null;
  orcid: string | null;
}

interface UserProfile {
  id: number;
  username: string;
  profile: Profile;
}
