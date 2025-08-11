import {
  LucideIcon,
  CircleSlash,
  Folders,
  Database,
  FileScan
} from "lucide-react";

interface EmptyStateProps {
  icon?: "folders" | "database" | "filescan" | "circle-slash";
  title: string;
  description: string;
}

export function EmptyState({
  icon = "circle-slash",
  title,
  description
}: EmptyStateProps) {
  const getIcon = (iconName: string): LucideIcon => {
    switch (iconName) {
      case "folders":
        return Folders;
      case "database":
        return Database;
      case "filescan":
        return FileScan;
      case "circle-slash":
      default:
        return CircleSlash;
    }
  };

  const IconComponent = getIcon(icon);

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center w-full max-w-none">
      <div className="mb-4 text-gray-600 dark:text-gray-400 flex justify-center">
        <IconComponent className="h-16 w-16" />
      </div>
      <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-200 text-center w-full">
        {title}
      </h3>
      <p className="mb-6 text-sm text-gray-600 dark:text-gray-400 text-center leading-relaxed mx-auto">
        {description}
      </p>
    </div>
  );
}
