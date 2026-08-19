type NotificationType =
  | "scanreport.processing_complete"
  | "scanreport.processing_failed"
  | "automap.complete"
  | "automap.failed"
  | "rules.export_complete"
  | "rules.export_failed"
  | "broadcast";

// Named AppNotification, not Notification - the latter is the browser's
// built-in Notifications API global and would silently merge with it.
interface AppNotification {
  id: number;
  notif_type: NotificationType;
  text: string;
  url: string;
  created_at: string;
  read_at: string | null;
}
