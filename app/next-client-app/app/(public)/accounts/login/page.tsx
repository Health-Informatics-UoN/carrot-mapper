"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { CircleAlert, Eye, EyeOff } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function SignIn() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
        <div className="flex items-center justify-center gap-3 pr-6">
          <Image
            src="/icon.svg"
            alt="Carrot"
            width={36}
            height={36}
            priority
          />
          <h1 className="text-2xl font-semibold">Sign In</h1>
        </div>

        {error && (
          <Alert
            variant="destructive"
            className="px-4 py-3 border-destructive bg-destructive/10"
          >
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
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Enter your password"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
          <Button type="submit" className="w-full" variant="outline">
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}
