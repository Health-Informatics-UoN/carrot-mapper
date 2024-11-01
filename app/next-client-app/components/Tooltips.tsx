import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { InfoIcon } from "lucide-react";
import { ReactElement } from "react";

export function Tooltips({
  content,
  link,
}: {
  content: string | ReactElement;
  link?: string;
}) {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <InfoIcon className="ml-1 size-4 text-carrot" />
        </TooltipTrigger>
        <TooltipContent>
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
