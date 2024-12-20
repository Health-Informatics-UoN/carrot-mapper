import { NextAuthOptions, Session } from "next-auth";
import { JWT } from "next-auth/jwt";
import CredentialsProvider from "next-auth/providers/credentials";

// These two values should be a bit less than actual token lifetimes
const BACKEND_ACCESS_TOKEN_LIFETIME = 45 * 60; // 45 minutes
const BACKEND_REFRESH_TOKEN_LIFETIME = 6 * 24 * 60 * 60; // 6 days

const getCurrentEpochTime = () => {
  return Math.floor(new Date().getTime() / 1000);
};

export const options: NextAuthOptions = {
  secret: process.env.AUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: BACKEND_REFRESH_TOKEN_LIFETIME,
  },
  pages: {
    signIn: "/accounts/login",
  },
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      // The data returned from this function is passed forward as the
      // `user` variable to the signIn() and jwt() callback
      async authorize(credentials, req) {
        try {
          const response = await fetch(
            process.env.NEXTAUTH_BACKEND_URL + "auth/login/",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(credentials),
            },
          );

          if (!response.ok) {
            throw new Error("Network response was not ok");
          }

          return await response.json();
        } catch (error) {
          console.error(error);
        }
        return null;
      },
    }),
  ],
  callbacks: {
    async jwt({ user, token, account }) {
      // If `user` and `account` are set that means it is a login event
      if (user && account) {
        let backendResponse: any =
          account.provider === "credentials" ? user : account.meta;
        token.user = backendResponse.user;
        token.access_token = backendResponse.access;
        token.refresh_token = backendResponse.refresh;
        token.expires_at =
          getCurrentEpochTime() + BACKEND_ACCESS_TOKEN_LIFETIME;
        return token;
      }
      // Refresh the backend token if necessary
      // TODO: move this out to a function above.
      if (getCurrentEpochTime() > token.expires_at) {
        try {
          const response = await fetch(
            process.env.NEXTAUTH_BACKEND_URL + "auth/token/refresh/",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                refresh: token.refresh_token,
              }),
            },
          );

          if (!response.ok) {
            throw new Error("Network response was not ok");
          }

          const responseData = await response.json();
          token.access_token = responseData.access;
          token.refresh_token = responseData.refresh;
          token.expires_at =
            getCurrentEpochTime() + BACKEND_ACCESS_TOKEN_LIFETIME;
        } catch (error) {
          console.error(error);
        }
      }
      return token;
    },
    // Since we're using Django as the backend we have to pass the JWT
    // token to the client instead of the `session`.
    async session({
      session,
      token,
    }: {
      session: Session;
      token: JWT;
    }): Promise<Session> {
      if (session) {
        session = Object.assign({}, session, {
          token: token,
          access_token: token.access_token,
        });
      }
      return session;
    },
  },
};
