import { getDataPartners } from "@/api/datasets";
import { getAllProjects } from "@/api/projects";
import { CreateScanReportForm } from "@/components/scanreports/CreateScanReportForm";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FileScan, Info } from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Upload Scan Report | Carrot Mapper",
  description: "Upload a scan report to the system",
};

export default async function ScanReports() {
  const partners = await getDataPartners();
  const projects = await getAllProjects();

  return (
    <>
      <div className="flex font-semibold text-xl items-center">
        <FileScan className="mr-2 text-green-700" />
        <Link href="/scanreports">
          <h2 className="text-muted-foreground">Scan Reports</h2>
        </Link>
      </div>
      <div className="flex justify-between mt-3">
        <h1 className="text-2xl font-semibold">Upload Scan Report</h1>
      </div>
      <div className="mt-4">
        <Alert className="mb-6 max-w-md">
          <Info />
          <AlertTitle>Need help uploading a scan report?</AlertTitle>
          <AlertDescription>
            Please ensure your scan report follows the correct format. 
            <Button variant="link" asChild className="p-0">
              <Link
                href="https://carrot.ac.uk/mapper/user_guide/upload_scan_report"
                target="_blank"
                rel="noopener noreferrer"
                className="underline text-primary hover:text-primary/80"
                >
                Read the guide
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
        <CreateScanReportForm dataPartners={partners} projects={projects} />
      </div>
    </>
  );
}
