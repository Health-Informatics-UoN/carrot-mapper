"use server";

export async function resetPassword(username: string, newPassword: string, confirmPassword: string): Promise<{ success: boolean; message?: string }> {
  const backendUrl = process.env.NEXT_PUBLIC_NEXTAUTH_BACKEND_URL;

  if (!backendUrl) return { success: false, message: "Backend URL not defined." };

  try {
    const csrfRes = await fetch(`${backendUrl}auth/csrf-token/`, {
      credentials: "include",
    });

    if (!csrfRes.ok) return { success: false, message: "Unable to fetch CSRF token." };

    const { csrfToken } = await csrfRes.json();

    const resetRes = await fetch(`${backendUrl}auth/password/reset/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        username,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });

    if (!resetRes.ok) {
      const errorData = await resetRes.json();
      return { success: false, message: errorData.detail || "Password reset failed." };
    }

    return { success: true };
  } catch (error: any) {
    console.error("Error in resetPassword:", error);
    return { success: false, message: error.message || "Unknown error occurred." };
  }
}
