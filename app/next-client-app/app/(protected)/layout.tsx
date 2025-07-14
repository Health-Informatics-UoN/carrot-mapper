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
      <section className="container flex flex-col min-h-svh">
        <MenuBar user={user} />
        {children}
      </section>
      <Footer />
    </>
  );
}
