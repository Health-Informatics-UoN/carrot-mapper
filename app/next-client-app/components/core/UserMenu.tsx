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
        <Button variant="ghost" className="dark:text-white">
          <Avatar>
            <AvatarFallback className="dark:text-white bg-gray-200 dark:bg-gray-800">
              {initials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56 bg-white dark:bg-gray-900 dark:text-white">
        <DropdownMenuLabel className="dark:text-white">
          My Account
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <Link href="/password-reset" passHref>
            <DropdownMenuItem asChild>
              <button className="flex items-center w-full dark:text-white">
                <Settings className="icon-md mr-2 dark:text-white" />
                <span>Reset Password</span>
              </button>
            </DropdownMenuItem>
          </Link>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="dark:text-white">
          <LogOut className="icon-md mr-2 dark:text-white" />
          <LogoutButton />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
