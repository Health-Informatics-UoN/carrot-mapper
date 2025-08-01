import "./globals.css";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/core/theme-provider";
import { Metadata } from "next";
import { PublicEnvScript } from "next-runtime-env";

export const metadata: Metadata = {
  title: "Carrot Mapper",
  description: "Convenient And Reusable Rapid Omop Transformer",
  keywords: [
    "OMOP CDM",
    "Data standardization",
    "Healthcare interoperability",
    "Clinical data mapping",
    "OHDSI",
    "OMOP",
    "Common data model",
    "Medical vocabulary mapping",
    "Health data conversion",
    "Observational research",
    "ETL for OMOP",
  ],
  robots: {
    index: true,
    follow: true,
    nocache: true,
    googleBot: {
      index: true,
      follow: true,
      noimageindex: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": 160,
    },
  },
  icons: {
    icon: "/icons/favicon.ico",
    apple: "/icons/apple-touch-icon.png",
  },
  manifest: "/manifest.json",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <PublicEnvScript />
      </head>
      <body
        className="bg-background text-foreground"
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>

        <Toaster
          toastOptions={{
            classNames: {
              error: "bg-destructive text-destructive-foreground",
              success: "bg-success text-success-foreground",
              warning: "bg-warning text-warning-foreground",
              info: "bg-popover text-popover-foreground",
            },
          }}
        />
      </body>
    </html>
  );
}
