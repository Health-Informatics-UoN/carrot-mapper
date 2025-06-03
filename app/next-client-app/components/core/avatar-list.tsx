"use client";
import { cn } from "@/lib/utils";
import { Tooltip } from "react-tooltip";

export function AvatarList({ members }: { members: User[] | [] }) {
  return (
    <div className={cn("z-10 flex -space-x-2")}>
      {members
        .map((member) => member.username)
        .map((name, index) => (
          <a
            data-tooltip-id="icon-tooltip"
            data-tooltip-content={`${name}`}
            data-tooltip-place="top"
            className="flex justify-center"
            key={name}
          >
            <Tooltip id="icon-tooltip" className="hidden lg:block" />
            {/* The below is for mobile devices with an additional setting to support show on tapping */}
            <Tooltip id="icon-tooltip" className="lg:hidden" openOnClick />
            <div
              key={index}
              className="h-8 w-8 rounded-full border-2 border-background bg-primary text-primary-foreground flex text-sm items-center justify-center"
            >
              {name.charAt(0).toUpperCase()}
            </div>
          </a>
        ))}

      <div className="h-8 w-8 flex items-center justify-center rounded-full border-2 border-background bg-muted text-muted-foreground text-sm font-medium">
        {members.length}
      </div>
    </div>
  );
}
