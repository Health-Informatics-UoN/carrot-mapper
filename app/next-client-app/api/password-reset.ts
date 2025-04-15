"use server";

import request from "@/lib/api/request";

const fetchKeys = {
  passwordReset: () => `auth/password/reset/`,
  csrfToken: () => `auth/csrf-token/`,
};

export async function passwordReset({
  new_password,
  confirm_password,
}: {
  new_password: string;
  confirm_password: string;
}) {
  try {
    if (!new_password || !confirm_password) {
      throw new Error("All fields are required.");
    }

    const backendUrl = process.env.NEXT_PUBLIC_NEXTAUTH_BACKEND_URL;
    console.log("Backend URL:", backendUrl);

    if (!backendUrl) {
      throw new Error("Backend URL not defined.");
    }

    // Get CSRF token from backend
    const csrfRes = await request(fetchKeys.csrfToken());

    const csrfToken = csrfRes.csrfToken;

    // Send password reset request to backend
    const resetRes = await request(
      fetchKeys.passwordReset(),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ new_password, confirm_password }),
      },
    );

    return resetRes;
  } catch (error: any) {
    throw new Error(error.message || "An unexpected error occurred.");
  }
}