export { default } from "next-auth/middleware";

export const config = {
  matcher: [
    /*
     * Match all paths except for:
     * 1. / index page
     * 2. /api routes
     * 3. /accounts/login
     * 4. /_next (Next.js internals)
     * 5. /_static (inside /public)
     * 6. all root files inside /public (e.g. /favicon.ico)
     * 7. folder containing logos inside "public"
     */
    "/((?!$|api/|accounts/login|_next/|_static/|logos|[\\w-]+\\.\\w+).*)",
  ],
};
