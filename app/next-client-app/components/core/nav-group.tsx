import { NavButton } from "./nav-button";

export type Item = {
  text: string;
  slug?: string;
  segment?: string;
  parallelRoutesKey?: string;
  iconName?: string;
  matchPrefixes?: string[];
};

export const NavGroup = ({
  path,
  parallelRoutesKey,
  items,
}: {
  path: string;
  parallelRoutesKey?: string;
  items: Item[];
}) => {
  return (
    <div className="flex flex-wrap items-center gap-2 md:gap-4">
      {items.map((item) => (
        <NavButton
          key={path + item.slug}
          item={item}
          path={path}
          parallelRoutesKey={parallelRoutesKey}
        />
      ))}
    </div>
  );
};
