import { CARROT_SRC, LOGO_HEIGHT, LOGO_WIDTH } from "@/constants/mapping-registry";
import {
  CLOUD_PATHS,
  COUGH_PATHS,
  TAGLINE_PATHS,
  TITLE_PATHS,
  type LogoPath,
} from "./registry-logo-paths";
import styles from "./registry-logo.module.css";

type RegistryLogoProps = {
  className?: string;
  animated?: boolean;
};

function LogoPaths({
  paths,
  strokeWidth,
}: {
  paths: LogoPath[];
  strokeWidth?: number;
}) {
  return (
    <>
      {paths.map((path, index) => (
        <path
          key={index}
          fill={path.fill}
          d={path.d}
          stroke={strokeWidth ? path.fill : undefined}
          strokeWidth={strokeWidth}
          strokeLinejoin="round"
        />
      ))}
    </>
  );
}

/**
 * The Carrot Mapper Registry logo, assembled from separate layers so each one
 * can be animated: the carrot comes from public/mapper-registry-carrot.svg and
 * the rest is drawn here. All layers share the same 565 x 660 canvas, so at
 * rest it is identical to the original single-file logo.
 */
export function RegistryLogo({ className, animated = false }: RegistryLogoProps) {
  const classes = [className, animated ? styles.animated : undefined].filter(Boolean).join(" ");

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 ${LOGO_WIDTH} ${LOGO_HEIGHT}`}
      width={LOGO_WIDTH}
      height={LOGO_HEIGHT}
      role="img"
      aria-label="Carrot Mapper Registry"
      className={classes}
    >
      <image
        href={CARROT_SRC}
        x={0}
        y={0}
        width={LOGO_WIDTH}
        height={LOGO_HEIGHT}
        className={styles.carrot}
      />
      <g className={styles.cloud}>
        <LogoPaths paths={CLOUD_PATHS} />
      </g>
      <g className={styles.cough}>
        <LogoPaths paths={COUGH_PATHS} strokeWidth={1.5} />
      </g>
      <g className={styles.title}>
        <LogoPaths paths={TITLE_PATHS} />
      </g>
      <g className={styles.tagline}>
        <LogoPaths paths={TAGLINE_PATHS} />
      </g>
    </svg>
  );
}
