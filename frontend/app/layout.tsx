import type { Metadata, Viewport } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import { AppProviders } from "@/components/providers/AppProviders";
import InstallApp from "@/components/app/InstallApp";

export const metadata: Metadata = {
  title: {
    default: "KING ZARRY AI",
    template: "%s | KING ZARRY AI",
  },
  description:
    "KING ZARRY AI — intelligent AI command centre. Your intelligence, amplified.",
  applicationName: "KING ZARRY AI",
  appleWebApp: {
    capable: true,
    title: "KING ZARRY AI",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#020914",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.gstatic.com"
          rel="preconnect"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Share+Tech+Mono&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full overflow-hidden">
        <AppProviders>
          <div className="kz-bg-grid" />
          <div className="kz-bg-radial" />
          <div className="relative z-10 flex h-full min-h-0 w-full">
            <Sidebar />
            <main className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden overflow-y-auto">
              {children}
            </main>
          </div>
          <InstallApp />
        </AppProviders>
      </body>
    </html>
  );
}
