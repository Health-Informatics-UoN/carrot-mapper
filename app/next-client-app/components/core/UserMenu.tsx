import { LogOut, Settings } from "lucide-react";
import Link from "next/link";

import { LoginButton, LogoutButton } from "@/auth/login";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export async function UserMenu({ username }: { username?: string }) {
  if (!username) {
    return <LoginButton />;
  }

  const initials =
    username
      ?.split(" ")
      .map((word) => word[0].toUpperCase())
      .join("") ?? "";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="group dark:text-white p-1 rounded-full"
        >
          <Avatar>
            <AvatarFallback className="dark:text-white bg-gray-200 dark:bg-gray-800 transition-colors">
              {initials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56">
        <DropdownMenuLabel>
          My Account
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <Link href="/password-reset" passHref>
            <DropdownMenuItem asChild>
              <button className="flex items-center w-full">
                <Settings />
                <span>Reset Password</span>
              </button>
            </DropdownMenuItem>
          </Link>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem>
          <LogOut />
          <LogoutButton />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
