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
      <MenuBar user={user} />
      <section className="w-full max-w-[1800px] mx-auto px-4 md:px-8">
        {children}
      </section>
      <Footer />
    </>
  );
}
