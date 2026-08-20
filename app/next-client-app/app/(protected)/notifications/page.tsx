import { Inbox } from "lucide-react";
import { Metadata } from "next";

import { getAppNotifications } from "@/api/notifications";
import { NotificationsList } from "@/components/notifications/NotificationsList";
import { objToQuery } from "@/lib/client-utils";

export const metadata: Metadata = {
  title: "Notifications | Carrot Mapper",
  description: "Notifications for the current user",
};

interface NotificationsPageProps {
  searchParams?: Promise<FilterParameters>;
}

export default async function NotificationsPage(props: NotificationsPageProps) {
  const searchParams = await props.searchParams;
  const defaultPageSize = 20;
  const combinedParams = { p: 1, page_size: defaultPageSize, ...searchParams };
  const query = objToQuery(combinedParams);
  const notifications = await getAppNotifications(query);

  return (
    <div className="space-y-2">
      <div className="flex font-semibold text-xl items-center">
        <Inbox className="mr-2 text-blue-700" />
        <h2>Notifications</h2>
      </div>
      <NotificationsList
        notifications={notifications?.results ?? []}
        count={notifications?.count ?? 0}
        defaultPageSize={defaultPageSize}
      />
    </div>
  );
}
