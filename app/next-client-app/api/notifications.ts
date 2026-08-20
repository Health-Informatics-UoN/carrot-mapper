"use server";
import request from "@/lib/api/request";

const fetchKeys = {
  list: (filter?: string) => `v2/notifications/?${filter ?? ""}`,
  unreadCount: () => `v2/notifications/unread-count/`,
  markRead: (id: number | string) => `v2/notifications/${id}/read/`,
  markAllRead: () => `v2/notifications/read-all/`,
};

export async function getAppNotifications(
  filter?: string,
): Promise<PaginatedResponse<AppNotification> | null> {
  try {
    return await request<PaginatedResponse<AppNotification>>(
      fetchKeys.list(filter),
    );
  } catch (error) {
    console.warn("Failed to fetch notifications.");
    return null;
  }
}

export async function getUnreadAppNotificationCount(): Promise<number> {
  try {
    const { count } = await request<{ count: number }>(fetchKeys.unreadCount());
    return count;
  } catch (error) {
    console.warn("Failed to fetch unread notification count.");
    return 0;
  }
}

export async function markAppNotificationRead(id: number | string) {
  try {
    await request(fetchKeys.markRead(id), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
}

export async function markAllAppNotificationsRead() {
  try {
    await request(fetchKeys.markAllRead(), {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
}
