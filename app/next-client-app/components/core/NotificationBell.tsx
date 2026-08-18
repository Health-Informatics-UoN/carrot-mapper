"use client";

import { Bell, Loader2 } from "lucide-react";
import { format } from "date-fns/format";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  getAppNotifications,
  markAllAppNotificationsRead,
  markAppNotificationRead,
} from "@/api/notifications";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";

export function NotificationBell({
  initialUnreadCount,
}: {
  initialUnreadCount: number;
}) {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState(initialUnreadCount);
  const [notifications, setNotifications] = useState<AppNotification[] | null>(
    null,
  );
  const [loading, setLoading] = useState(false);

  const loadNotifications = async () => {
    setLoading(true);
    const data = await getAppNotifications();
    setNotifications(data?.results ?? []);
    setLoading(false);
  };

  const handleOpenChange = (open: boolean) => {
    if (open) {
      loadNotifications();
    }
  };

  const handleSelect = async (notification: AppNotification) => {
    if (!notification.read_at) {
      setUnreadCount((count) => Math.max(0, count - 1));
      setNotifications(
        (current) =>
          current?.map((n) =>
            n.id === notification.id
              ? { ...n, read_at: new Date().toISOString() }
              : n,
          ) ?? null,
      );
      await markAppNotificationRead(notification.id);
    }
    if (notification.url) {
      router.push(notification.url);
    }
  };

  const handleMarkAllRead = async () => {
    setUnreadCount(0);
    setNotifications(
      (current) =>
        current?.map((n) => ({
          ...n,
          read_at: n.read_at ?? new Date().toISOString(),
        })) ?? null,
    );
    await markAllAppNotificationsRead();
  };

  return (
    <DropdownMenu onOpenChange={handleOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="relative p-2"
          aria-label="Notifications"
        >
          <Bell size={20} />
          {unreadCount > 0 && (
            <Badge className="absolute -top-1 -right-1 h-5 min-w-5 items-center justify-center rounded-full border-transparent bg-orange-500 px-1 text-[10px] text-white">
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-96">
        <div className="flex items-center justify-between px-2 py-1.5">
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {unreadCount > 0 && (
            <button
              className="text-xs text-muted-foreground hover:text-foreground"
              onClick={handleMarkAllRead}
            >
              Mark all as read
            </button>
          )}
        </div>
        <DropdownMenuSeparator />
        {loading && (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="animate-spin" size={20} />
          </div>
        )}
        {!loading && notifications && notifications.length === 0 && (
          <div className="py-6 text-center text-sm text-muted-foreground">
            No notifications yet
          </div>
        )}
        {!loading && notifications && notifications.length > 0 && (
          <ScrollArea className="max-h-96">
            {notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="flex flex-col items-start gap-0.5 whitespace-normal py-2"
                onSelect={() => handleSelect(notification)}
              >
                <div className="flex w-full items-start justify-between gap-2">
                  <span
                    className={
                      notification.read_at
                        ? "text-muted-foreground"
                        : "font-medium"
                    }
                  >
                    {notification.text}
                  </span>
                  {!notification.read_at && (
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-orange-500" />
                  )}
                </div>
                <span className="text-xs text-muted-foreground">
                  {format(notification.created_at, "d MMM HH:mm")}
                </span>
              </DropdownMenuItem>
            ))}
          </ScrollArea>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
