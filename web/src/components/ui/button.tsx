import * as React from "react";
import { cn } from "@/lib/utils";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "ghost" | "danger" | "outline";
};

export function Button({ className, variant = "default", ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-40",
        variant === "default" &&
          "bg-lime-300 text-zinc-950 hover:bg-lime-200",
        variant === "ghost" &&
          "bg-transparent text-zinc-300 hover:bg-zinc-800 hover:text-white",
        variant === "danger" &&
          "bg-orange-500 text-zinc-950 hover:bg-orange-400",
        variant === "outline" &&
          "border border-zinc-700 bg-transparent text-zinc-200 hover:border-zinc-500",
        className,
      )}
      {...props}
    />
  );
}
