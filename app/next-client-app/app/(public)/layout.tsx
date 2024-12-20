import React from "react";
import { MenuBar } from "@/components/core/menubar";
import Footer from "@/components/core/footer";
import { getServerSession } from "next-auth";
import { options } from "@/auth/options";

export default async function PublicLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getServerSession(options);
  const user = session?.token?.user;

  return (
    <>
      <section className="container">
        <MenuBar user={user} />
        {children}
        <Footer />
      </section>
    </>
  );
}
