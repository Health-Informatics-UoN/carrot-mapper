import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
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
          <InfoIcon className="ml-1 h-4 w-4 text-muted-foreground" />
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
                  className="underline"
                  target="_blank"
                  rel="noopener noreferrer"
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
