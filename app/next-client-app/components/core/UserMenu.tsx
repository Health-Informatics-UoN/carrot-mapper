import { LogOut, Settings } from "lucide-react";

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
  DropdownMenuTrigger,
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
        <Button variant="ghost">
          <Avatar>
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56">
        <DropdownMenuLabel>My Account</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {/* TODO: Add change password here */}
        {/* <DropdownMenuGroup>
          <DropdownMenuItem>
            <Settings className="icon-md mr-2" />
            <span>Change Password</span>
            <DropdownMenuShortcut>⌘S</DropdownMenuShortcut>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator /> */}

        <DropdownMenuItem>
          <LogOut className="icon-md mr-2" />
          <LogoutButton />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
