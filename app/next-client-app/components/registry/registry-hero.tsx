import { RegistryLogo } from "./registry-logo";

type RegistryHeroProps = {
  /** Smaller logo and no subtitle, used once results are showing. */
  compact: boolean;
};

export function RegistryHero({ compact }: RegistryHeroProps) {
  return (
    <div
      className={
        compact
          ? "mb-4 text-center"
          : "flex flex-col items-center justify-end pb-3 text-center"
      }
    >
      {/* The key remounts the logo when returning to the landing page, so the
          entrance animation replays there; the compact results view stays static. */}
      <RegistryLogo
        key={compact ? "compact" : "landing"}
        animated={!compact}
        className={`mx-auto w-auto ${compact ? "h-24" : "h-44 sm:h-60"}`}
      />
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Discover reusable mappings</h1>
      {!compact && (
        <p className="mt-2 text-sm text-muted-foreground sm:text-base">
          Explore how researchers map source terms to OMOP concepts.
        </p>
      )}
    </div>
  );
}