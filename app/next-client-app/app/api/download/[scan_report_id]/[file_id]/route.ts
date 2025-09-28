import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { options as authOptions } from "@/auth/options";

export async function GET(
  request: NextRequest,
  { params }: { params: { scan_report_id: string; file_id: string } },
) {
  try {
    const { scan_report_id, file_id } = params;

    // Get the session for authentication
    const session = await getServerSession(authOptions);
    const token = session?.access_token;

    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Construct the Django backend URL
    const backendUrl = `${process.env.BACKEND_URL}/api/v2/scanreports/${scan_report_id}/rules/downloads/${file_id}/`;

    // Forward the request to Django backend
    const backendResponse = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Authorization: `JWT ${token}`,
        // Forward any relevant headers from the original request
        ...(request.headers.get("user-agent") && {
          "User-Agent": request.headers.get("user-agent")!,
        }),
      },
    });

    // If the backend request failed, return the same status
    if (!backendResponse.ok) {
      return new NextResponse(backendResponse.body, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
      });
    }

    // Get the content type and disposition from the backend response
    const contentType = backendResponse.headers.get("content-type");
    const contentDisposition = backendResponse.headers.get(
      "content-disposition",
    );
    const contentLength = backendResponse.headers.get("content-length");

    // Create headers for the Next.js response
    const responseHeaders = new Headers();

    if (contentType) {
      responseHeaders.set("content-type", contentType);
    }

    if (contentDisposition) {
      responseHeaders.set("content-disposition", contentDisposition);
    }

    if (contentLength) {
      responseHeaders.set("content-length", contentLength);
    }

    // Set cache headers to prevent caching of file downloads
    responseHeaders.set("cache-control", "no-cache, no-store, must-revalidate");
    responseHeaders.set("pragma", "no-cache");
    responseHeaders.set("expires", "0");

    // Stream the response body directly to the client
    return new NextResponse(backendResponse.body, {
      status: 200,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Error in download proxy:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
