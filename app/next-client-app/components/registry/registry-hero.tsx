type RegistryHeroProps = {
  /** Compact title and no subtitle, used once results are showing. */
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
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        Carrot Mapper Registry
      </h1>
      {!compact && (
        <p className="mt-2 text-sm text-muted-foreground sm:text-base">
          Explore how researchers map source terms to OMOP concepts.
        </p>
      )}
    </div>
  );
}
