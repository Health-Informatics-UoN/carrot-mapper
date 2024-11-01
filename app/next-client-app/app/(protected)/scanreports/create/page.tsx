import { getDataPartners } from "@/api/datasets";
import { getAllProjects } from "@/api/projects";
import { CreateScanReportForm } from "@/components/scanreports/CreateScanReportForm";
import { FileScan } from "lucide-react";
import Link from "next/link";

export default async function ScanReports() {
  const partners = await getDataPartners();
  const projects = await getAllProjects();

  return (
    <>
      <div className="flex font-semibold text-xl items-center">
        <FileScan className="mr-2 text-green-700" />
        <Link href="/scanreports">
          <h2 className="text-gray-500 dark:text-gray-400">Scan Reports</h2>
        </Link>
      </div>
      <div className="flex justify-between mt-3">
        <h1 className="text-4xl font-semibold">Upload Scan Report</h1>
      </div>
      <div className="mt-4">
        <CreateScanReportForm dataPartners={partners} projects={projects} />
      </div>
    </>
  );
}
