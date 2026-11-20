import { RegistryLandingPage } from "@/components/registry/registry-landing-page";
import { MOCK_STATS } from "@/lib/registry/mock-data";

export default function RegistryPage() {
  return <RegistryLandingPage stats={MOCK_STATS} />;
}
