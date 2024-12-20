import "react-tooltip/dist/react-tooltip.css";
import React from "react";
import { getServerSession } from "next-auth";
import { options } from "@/auth/options";
import { MenuBar } from "@/components/core/menubar";

export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getServerSession(options);
  const user = session?.token?.user;

  return (
    <>
      <section className="container mb-5">
        <MenuBar user={user} />
        {children}
      </section>
    </>
  );
}
