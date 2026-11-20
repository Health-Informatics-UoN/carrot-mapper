import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MappingDetails } from "@/components/registry/mapping-details";
import { getMappingById } from "@/lib/registry/mock-data";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const mapping = getMappingById(id);
  return {
    title: mapping
      ? `${mapping.sourceTerm} — Carrot Mapper Registry`
      : "Mapping — Carrot Mapper Registry",
  };
}

export default async function RegistryMappingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const mapping = getMappingById(id);
  if (!mapping) notFound();
  return <MappingDetails mapping={mapping} />;
}
