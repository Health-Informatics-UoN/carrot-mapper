import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MappingSetDetails } from "@/components/registry/mapping-set-details";
import { getMappingById, getMappingSetById } from "@/lib/registry/mock-data";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const mappingSet = getMappingSetById(id);
  return {
    title: mappingSet
      ? `${mappingSet.title} — Carrot Mapper Registry`
      : "Mapping set — Carrot Mapper Registry",
  };
}

export default async function RegistryMappingSetDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ fromMapping?: string }>;
}) {
  const { id } = await params;
  const { fromMapping } = await searchParams;
  const mappingSet = getMappingSetById(id);
  if (!mappingSet) notFound();

  const candidate = fromMapping ? getMappingById(fromMapping) : undefined;
  const originMapping =
    candidate && mappingSet.mappings.some((item) => item.id === candidate.id)
      ? candidate
      : undefined;

  return (
    <MappingSetDetails mappingSet={mappingSet} originMapping={originMapping} />
  );
}
