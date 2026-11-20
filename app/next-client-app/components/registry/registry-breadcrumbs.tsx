import Link from "next/link";

export type RegistryBreadcrumbItem = {
  label: string;
  href?: string;
};

export function RegistryBreadcrumbs({ items }: { items: RegistryBreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      {items.map((item, index) => (
        <span key={`${item.label}-${index}`} className="flex items-center gap-2">
          {index > 0 && <span aria-hidden="true">/</span>}
          {item.href ? (
            <Link className="hover:text-foreground" href={item.href}>{item.label}</Link>
          ) : (
            <span aria-current="page" className="font-medium text-foreground">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
