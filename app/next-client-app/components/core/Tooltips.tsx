import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { InfoIcon } from "lucide-react";

export function Tooltips({
  content,
  link,
  side = "top",
}: {
  content: string;
  link?: string;
  side?: "top" | "bottom" | "left" | "right";
}) {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <InfoIcon className="ml-1 size-4 text-carrot" />
        </TooltipTrigger>
        <TooltipContent className="max-w-96 text-center" side={side}>
          <p>
            {content}
            {link && (
              <>
                {" "}
                Find out more{" "}
                <a
                  href={link}
                  style={{ textDecoration: "underline" }}
                  target="_blank"
                >
                  here
                </a>
                .
              </>
            )}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
