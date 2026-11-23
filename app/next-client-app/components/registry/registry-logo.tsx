import styles from "./registry-logo.module.css";

type RegistryLogoProps = {
  className?: string;
  animated?: boolean;
};

/** Existing Carrot Mapper icon, with an optional entrance animation. */
export function RegistryLogo({ className, animated = false }: RegistryLogoProps) {
  const classes = [
    className,
    styles.icon,
    animated ? styles.animated : undefined,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/icon.svg"
      alt="Carrot Mapper"
      width={200}
      height={200}
      className={classes}
    />
  );
}
