import { Fira_Code as FontMono, Bricolage_Grotesque as FontSans } from "next/font/google";

export const fontSans = FontSans({
  subsets: ["latin"],
  variable: "--font-bricolage-grotesque",
});

export const fontMono = FontMono({
  subsets: ["latin"],
  variable: "--font-mono",
});
