"use server";

import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { username, new_password, confirm_password } = await req.json();

    if (!username || !new_password || !confirm_password) {
      return NextResponse.json(
        { detail: "All fields are required." },
        { status: 400 },
      );
    }

    const backendUrl = process.env.NEXT_PUBLIC_NEXTAUTH_BACKEND_URL;
  

    if (!backendUrl) {
      return NextResponse.json(
        { detail: "Backend URL not defined." },
        { status: 500 },
      );
    }

    // Get CSRF token from backend
    const csrfRes = await fetch(`${backendUrl}auth/csrf-token/`, {
      credentials: "include",
    });

    if (!csrfRes.ok) {
      return NextResponse.json(
        { detail: "Unable to fetch CSRF token." },
        { status: 500 },
      );
    }

    const csrfData = await csrfRes.json();
    const csrfToken = csrfData.csrfToken;

    // Send password reset request to backend
    const resetRes = await fetch(
      `${backendUrl}auth/password/reset/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ username, new_password, confirm_password }),
      },
    );

    if (!resetRes.ok) {
      const errorData = await resetRes.json();
      console.log("Password reset failed:", errorData);
      return NextResponse.json(
        { detail: errorData.detail || "Password reset failed." },
        { status: resetRes.status },
      );
    }

    const data = await resetRes.json();

    return NextResponse.json(data, { status: resetRes.status });
  } catch (error: any) {
    console.error("Error during password reset process:", error);
    return NextResponse.json(
      { detail: error.message || "An unexpected error occurred." },
      { status: 500 },
    );
  }
}
