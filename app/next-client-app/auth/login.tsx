"use client";

import { signIn, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LogIn } from "lucide-react";

export const LoginButton = () => {
  return (
    <Button variant={"ghost"} onClick={() => signIn()}>
      <LogIn className="icon-sm mr-2" />
      Sign in
    </Button>
  );
};

export const LogoutButton = () => {
  return (
    <button onClick={() => signOut({ callbackUrl: "/" })}>Sign Out</button>
  );
};
