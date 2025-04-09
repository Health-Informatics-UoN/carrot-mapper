'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

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
      <div className="max-w-md mx-auto mt-20 p-4 border rounded shadow">
        <h1 className="text-xl font-semibold mb-4">Check your inbox</h1>
        <p>If an account exists for <strong>{email}</strong>, a password reset link has been sent.</p>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-20 p-4 border rounded shadow">
      <h1 className="text-xl font-semibold mb-4">Reset your password</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium mb-1">
            Email address
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          />
        </div>
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Send reset link
        </button>
      </form>
    </div>
  );
}
