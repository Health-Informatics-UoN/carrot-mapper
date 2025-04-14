import { resetPassword } from "@/api/password-reset";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FormState {
  error?: string;
  success?: boolean;
}

async function handleResetPassword(formData: FormData): Promise<FormState> {


  const username = formData.get("username") as string;
  const newPassword = formData.get("newPassword") as string;
  const confirmPassword = formData.get("confirmPassword") as string;

  if (newPassword !== confirmPassword) {
    return { error: "Passwords do not match." };
  }

  const result = await resetPassword(username, newPassword, confirmPassword);
  return result.success ? { success: true } : { error: result.message };
}

export default function PasswordResetPage({ searchParams }: { searchParams: Record<string, string> }) {
  const success = searchParams.success === "true";
  const error = searchParams.error;

  return (
    <div className="flex min-h-96 items-center justify-center">
      <div className="w-full max-w-md p-8 space-y-6">
        {success ? (
          <>
            <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
              Password Reset Successful
            </h1>
            <p className="text-center text-sm text-gray-600 dark:text-gray-300">
              You can now log in with your new password.
            </p>
            <div className="text-center">
              <a href="/projects" className="text-blue-600 hover:underline text-sm">
                Dashboard
              </a>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
              Reset your password
            </h1>
            {error && <Alert variant="destructive">{error}</Alert>}

            <form action={handleResetPassword} className="space-y-4">
              <div>
                <Label htmlFor="username">Username</Label>
                <Input id="username" name="username" type="text" required placeholder="Enter your username" />
              </div>
              <div>
                <Label htmlFor="newPassword">New Password</Label>
                <Input id="newPassword" name="newPassword" type="password" required placeholder="Enter your new password" />
              </div>
              <div>
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input id="confirmPassword" name="confirmPassword" type="password" required placeholder="Re-enter your new password" />
              </div>
              <Button type="submit" className="w-full">Reset Password</Button>
            </form>

            <div className="text-sm text-center mt-2">
              <a href="/accounts/projects" className="text-blue-600 hover:underline">Back to login</a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
