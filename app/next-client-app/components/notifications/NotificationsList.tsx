"use client";

import { format } from "date-fns/format";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  markAllAppNotificationsRead,
  markAppNotificationRead,
} from "@/api/notifications";
import { DataTablePagination } from "@/components/data-table/DataTablePagination";
import { cn } from "@/lib/utils";

export function NotificationsList({
  notifications,
  count,
  defaultPageSize,
}: {
  notifications: AppNotification[];
  count: number;
  defaultPageSize: 10 | 20 | 30 | 40 | 50;
}) {
  const router = useRouter();
  const [readIds, setReadIds] = useState<Set<number>>(new Set());

  const isRead = (notification: AppNotification) =>
    !!notification.read_at || readIds.has(notification.id);
  const hasUnread = notifications.some((n) => !isRead(n));

  const handleSelect = async (notification: AppNotification) => {
    if (!isRead(notification)) {
      setReadIds((current) => new Set(current).add(notification.id));
      await markAppNotificationRead(notification.id);
    }
    router.refresh();
    if (notification.url) {
      router.push(notification.url);
    }
  };

  const handleMarkAllRead = async () => {
    setReadIds(
      (current) => new Set([...current, ...notifications.map((n) => n.id)]),
    );
    await markAllAppNotificationsRead();
    router.refresh();
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-end">
        {hasUnread && (
          <button
            className="text-sm text-muted-foreground hover:text-foreground"
            onClick={handleMarkAllRead}
          >
            Mark all as read
          </button>
        )}
      </div>
      <div className="rounded-md border divide-y">
        {notifications.length === 0 && (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No notifications yet
          </div>
        )}
        {notifications.map((notification) => {
          const read = isRead(notification);
          return (
            <button
              key={notification.id}
              className={cn(
                "flex w-full items-start justify-between gap-2 px-4 py-3 text-left hover:bg-muted/50 transition-colors",
                !read && "bg-muted/30",
              )}
              onClick={() => handleSelect(notification)}
            >
              <div className="flex flex-col gap-0.5">
                <span
                  className={read ? "text-muted-foreground" : "font-medium"}
                >
                  {notification.text}
                </span>
                <span className="text-xs text-muted-foreground">
                  {format(notification.created_at, "d MMM HH:mm")}
                </span>
              </div>
              {!read && (
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-orange-500" />
              )}
            </button>
          );
        })}
      </div>
      {count > 0 && (
        <DataTablePagination count={count} defaultPageSize={defaultPageSize} />
      )}
    </div>
  );
}
