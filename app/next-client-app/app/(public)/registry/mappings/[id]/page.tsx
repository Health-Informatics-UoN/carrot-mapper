import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MappingDetails } from "@/components/registry/mapping-details";
import { getMappingById, getMappingSetById } from "@/lib/registry/mock-data";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const mapping = getMappingById(id);
  return {
    title: mapping
      ? `${mapping.sourceTerm} — Carrot Mapper Registry`
      : "Mapping — Carrot Mapper Registry",
  };
}

export default async function RegistryMappingDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ fromMappingSet?: string }>;
}) {
  const { id } = await params;
  const { fromMappingSet } = await searchParams;
  const mapping = getMappingById(id);
  if (!mapping) notFound();

  const candidate =
    fromMappingSet === mapping.mappingSetId
      ? getMappingSetById(fromMappingSet)
      : undefined;
  const parentSet = candidate?.mappings.some((item) => item.id === mapping.id)
    ? candidate
    : undefined;

  return <MappingDetails mapping={mapping} parentSet={parentSet} />;
}
