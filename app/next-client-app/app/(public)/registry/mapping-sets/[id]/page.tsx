import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MappingSetDetails } from "@/components/registry/mapping-set-details";
import { getMappingSetById } from "@/lib/registry/mock-data";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const mappingSet = getMappingSetById(id);
  return {
    title: mappingSet
      ? `${mappingSet.title} — Carrot Mapper Registry`
      : "Mapping set — Carrot Mapper Registry",
  };
}

export default async function RegistryMappingSetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const mappingSet = getMappingSetById(id);
  if (!mappingSet) notFound();
  return <MappingSetDetails mappingSet={mappingSet} />;
}
