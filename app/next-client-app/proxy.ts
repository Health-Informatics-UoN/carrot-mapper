import authMiddleware from "next-auth/middleware";

export default authMiddleware;

export const config = {
  matcher: [
    /*
     * Match all paths except for:
     * 1. / index page
     * 2. /api routes
     * 3. /registry and its subroutes
     * 4. /accounts/login
     * 5. /_next (Next.js internals)
     * 6. /_static (inside /public)
     * 7. all root files inside /public (e.g. /favicon.ico)
     * 8. folder containing logos inside "public"
     */
    "/((?!api/|registry(?:/|$)|accounts/login|_next/|_static/|logos|[\\w-]+\\.\\w+).*)",
  ],
};
