import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function CardRow({ title, action, children, className }: { title: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
      className={cn("space-y-4", className)}
    >
      <div className="flex items-end justify-between gap-4">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight">{title}</h2>
        {action}
      </div>
      {children}
    </motion.section>
  );
}

export function CardGrid({ children, cols = 5 }: { children: ReactNode; cols?: 4 | 5 | 6 }) {
  const c = cols === 4 ? "sm:grid-cols-3 lg:grid-cols-4" : cols === 6 ? "sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6" : "sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5";
  return <div className={cn("grid grid-cols-2 gap-4 sm:gap-5", c)}>{children}</div>;
}
