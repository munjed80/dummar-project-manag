import { cn } from "@/lib/utils"
import { ComponentProps } from "react"

function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      // Neutral slate placeholder — matches the navy/blue platform identity.
      // Do NOT use `bg-accent`/green/emerald tokens here; loading state must
      // stay neutral (success/status colors are reserved for badges).
      className={cn(
        "animate-pulse rounded-md bg-[#E8EEF6] dark:bg-slate-700/40",
        className,
      )}
      {...props}
    />
  )
}

export { Skeleton }
