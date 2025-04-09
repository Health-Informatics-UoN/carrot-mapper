'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

export default function PasswordResetPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const res = await fetch(`${process.env.NEXTAUTH_BACKEND_URL}/auth/password-reset/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData.detail || 'Something went wrong.');
        return;
      }

      setSubmitted(true);
    } catch (err) {
      console.error(err);
      setError('An error occurred while trying to reset the password.');
    }
  };

  if (submitted) {
    return (
      <div className="flex min-h-96 items-center justify-center">
        <div className="w-full max-w-md p-8 space-y-4">
          <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
            Check your inbox
          </h1>
          <p className="text-center text-sm text-gray-600 dark:text-gray-300">
            If an account exists for <strong>{email}</strong>, a password reset link has been sent.
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

        {error && (
          <Alert variant="destructive">
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="email">Email address</Label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>
          <Button type="submit" className="w-full">
            Send reset link
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
