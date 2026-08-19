"use client";

import { Inbox } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUnreadNotificationCount } from "@/lib/hooks/useUnreadNotificationCount";

export function NotificationsLink({
  initialUnreadCount,
}: {
  initialUnreadCount: number;
}) {
  const unreadCount = useUnreadNotificationCount(initialUnreadCount);

  return (
    <Button
      variant="outline"
      size="icon"
      className="relative"
      aria-label="Notifications"
      asChild
    >
      <Link href="/notifications">
        <Inbox className="h-[1.2rem] w-[1.2rem]" />
        {unreadCount > 0 && (
          <Badge className="absolute -top-1.5 -right-1.5 h-5 min-w-5 items-center justify-center rounded-full border-transparent bg-orange-500 px-1 text-[10px] text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </Badge>
        )}
      </Link>
    </Button>
  );
}
