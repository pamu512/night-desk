import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function apiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_URL;
  if (env && env !== "same-origin") return env;
  if (typeof window !== "undefined" && window.location.port !== "43147") return "";
  return "http://127.0.0.1:43148";
}
