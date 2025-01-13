"use client";

import React, { forwardRef, useRef } from "react";

import { cn } from "@/lib/utils";
import { AnimatedBeam } from "@/components/magicui/animated-beam";
import Image from "next/image";
import { Rabbit } from "lucide-react";

export const Circle = forwardRef<
  HTMLDivElement,
  { className?: string; children?: React.ReactNode }
>(({ className, children }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "z-10 flex flex-col lg:size-24 size-20 items-center dark:text-black justify-center rounded-xl border-2 border-border bg-white p-3 shadow-[0_0_20px_-12px_rgba(0,0,0,0.8)]",
        className
      )}
    >
      {children}
    </div>
  );
});

Circle.displayName = "Circle";

export function AnimatedBeamMapping({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const div1Ref = useRef<HTMLDivElement>(null);
  const div2Ref = useRef<HTMLDivElement>(null);
  const div3Ref = useRef<HTMLDivElement>(null);
  const div6Ref = useRef<HTMLDivElement>(null);
  const div7Ref = useRef<HTMLDivElement>(null);
  const div8Ref = useRef<HTMLDivElement>(null);
  const div9Ref = useRef<HTMLDivElement>(null);

  return (
    <div
      className={cn(
        "relative flex items-center justify-center lg:p-8 mt-5",
        className
      )}
      ref={containerRef}
    >
      <div className="flex lg:size-full flex-row lg:items-stretch justify-between gap-10 lg:max-w-lg">
        <div className="flex flex-col justify-center gap-2">
          <Circle ref={div1Ref}>
            <Rabbit className="mr-2" /> Metadata
          </Circle>
          <Circle ref={div2Ref}>
            <h2>Cough</h2>
          </Circle>
        </div>
        <div className="flex flex-col justify-center">
          <Circle ref={div6Ref}>
            <img src="/icon.svg" alt="carrot-logo" className="w-[50px]" />
          </Circle>
        </div>
        <div className="flex flex-col justify-center gap-2 text-center">
          <Circle ref={div7Ref}>OMOP Mapping</Circle>
          <Circle ref={div8Ref}>
            <h2>254761 - Cough</h2>
          </Circle>
        </div>
      </div>

      <AnimatedBeam
        containerRef={containerRef}
        fromRef={div1Ref}
        toRef={div6Ref}
        duration={3}
      />
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={div2Ref}
        toRef={div6Ref}
        duration={4}
      />
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={div3Ref}
        toRef={div6Ref}
        duration={5}
      />
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={div6Ref}
        toRef={div7Ref}
        duration={3}
      />
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={div6Ref}
        toRef={div8Ref}
        duration={4}
      />
    </div>
  );
}
