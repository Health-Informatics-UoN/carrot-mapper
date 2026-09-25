import "react-tooltip/dist/react-tooltip.css";
import React from "react";
import { getServerSession } from "next-auth";
import { options } from "@/auth/options";
import { MenuBar } from "@/components/core/menubar";
import Footer from "@/components/core/footer";

export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getServerSession(options);
  const user = session?.token?.user;

  return (
    <>
      <MenuBar user={user} />
      <section className="flex flex-col min-h-svh">
        <div className="w-full max-w-[1800px] mx-auto px-4 md:px-8">
          {children}
        </div>
      </section>
      <Footer />
    </>
  );
}
