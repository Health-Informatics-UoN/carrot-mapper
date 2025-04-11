"use client";

import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

export default function PasswordResetPage() {
  const [username, setUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
  
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
  
    try {
      const res = await fetch("/api/password/reset", { 
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
  
      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData?.detail || "Something went wrong.");
        return;
      }
  
      setSubmitted(true);
    } catch (err) {
      console.error("Password reset error:", err);
      setError("An error occurred while trying to reset the password.");
    }
  };
  
  

  if (submitted) {
    return (
      <div className="flex min-h-96 items-center justify-center">
        <div className="w-full max-w-md p-8 space-y-4">
          <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
            Password Reset Successful
          </h1>
          <p className="text-center text-sm text-gray-600 dark:text-gray-300">
            Your password has been reset successfully. You can now log in with your new password.
          </p>
          <div className="text-center">
            <a
              href="/accounts/login"
              className="text-blue-600 hover:underline text-sm"
            >
              Back to login
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-96 items-center justify-center">
      <div className="w-full max-w-md p-8 space-y-6">
        <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
          Reset your password
        </h1>

        {error && <Alert variant="destructive">{error}</Alert>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
            />
          </div>
          <div>
            <Label htmlFor="newPassword">New Password</Label>
            <Input
              id="newPassword"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter your new password"
            />
          </div>
          <div>
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your new password"
            />
          </div>
          <Button type="submit" className="w-full">
            Reset Password
          </Button>
        </form>

        <div className="text-sm text-center mt-2">
          <a href="/accounts/login" className="text-blue-600 hover:underline">
            Back to login
          </a>
        </div>
      </div>
    </div>
  );
}
