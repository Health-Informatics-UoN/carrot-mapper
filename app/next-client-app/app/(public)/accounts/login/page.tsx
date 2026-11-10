"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { CircleAlert } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function SignIn() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await signIn("credentials", {
      redirect: false,
      username,
      password,
    });
    if (result?.ok) {
      router.push("/projects");
    } else {
      setError("Login failed. Please check your credentials.");
    }
  };

  return (
    <div className="flex flex-1 items-start justify-center pt-20">
      <div className="w-full max-w-md p-8 space-y-6 rounded-xl border bg-card text-card-foreground shadow-sm">
        <div className="flex items-center justify-center gap-3">
          <img src="/icon.svg" alt="Carrot" className="h-9 w-9" />
          <h1 className="text-2xl font-semibold">Sign In</h1>
        </div>

        {error && (
          <Alert variant="destructive" className="px-4 py-3">
            <CircleAlert />
            <AlertDescription className="text-destructive">
              {error}
            </AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Username</Label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Enter your username"
            />
          </div>
          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
            />
          </div>
          <Button type="submit" className="w-full" variant="outline">
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}
