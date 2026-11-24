import { CARROT_SRC } from "@/constants/mapping-registry";
import {
  TAGLINE_PATHS,
  TITLE_PATHS,
  type LogoPath,
} from "./registry-logo-paths";
import styles from "./registry-logo.module.css";

// Layout, in the coordinate space of the "CARROT MAPPER / REGISTRY" text paths.
// The text spans x 72–559 and y 547–657; the carrot sits centred above it.
const CARROT_SIZE = 340;
const CARROT_GAP = 34;

const TEXT_LEFT = 72;
const TEXT_RIGHT = 559;
const TEXT_TOP = 547;
const TEXT_BOTTOM = 657;
const TEXT_CENTER_X = (TEXT_LEFT + TEXT_RIGHT) / 2;
const PADDING = 4;

const carrotX = TEXT_CENTER_X - CARROT_SIZE / 2;
const carrotY = TEXT_TOP - CARROT_GAP - CARROT_SIZE;
const viewX = Math.min(TEXT_LEFT, carrotX) - PADDING;
const viewY = carrotY - PADDING;
const viewWidth = Math.max(TEXT_RIGHT, carrotX + CARROT_SIZE) + PADDING - viewX;
const viewHeight = TEXT_BOTTOM + PADDING - viewY;

type RegistryLogoProps = {
  className?: string;
  /** Play the entrance animation on mount. The final frame is the static logo. */
  animated?: boolean;
};

function LogoPaths({ paths }: { paths: LogoPath[] }) {
  return (
    <>
      {paths.map((path, index) => (
        <path key={index} fill={path.fill} d={path.d} />
      ))}
    </>
  );
}

/** Carrot icon with the "CARROT MAPPER / REGISTRY" text underneath. */
export function RegistryLogo({
  className,
  animated = false,
}: RegistryLogoProps) {
  const classes = [className, animated ? styles.animated : undefined]
    .filter(Boolean)
    .join(" ");

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`${viewX} ${viewY} ${viewWidth} ${viewHeight}`}
      width={viewWidth}
      height={viewHeight}
      role="img"
      aria-label="Carrot Mapper Registry"
      className={classes}
    >
      <image
        href={CARROT_SRC}
        x={carrotX}
        y={carrotY}
        width={CARROT_SIZE}
        height={CARROT_SIZE}
        className={styles.carrot}
      />
      <g className={styles.title}>
        <LogoPaths paths={TITLE_PATHS} />
      </g>
      <g className={styles.tagline}>
        <LogoPaths paths={TAGLINE_PATHS} />
      </g>
    </svg>
  );
}
