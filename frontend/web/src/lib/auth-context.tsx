import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getCurrentSession, signOut } from "./auth";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

export interface AuthUser {
  userId: string;
  email: string;
  tenantId: string | null;
  role: string;
  isSuperadmin: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  refreshSession: () => Promise<AuthUser | null>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  logout: () => {},
  refreshSession: async () => null,
});

function parseSession(session: CognitoUserSession): AuthUser {
  const payload = session.getIdToken().decodePayload();

  if (!payload.sub || !payload.email) {
    throw new Error("Invalid Cognito session: missing required claims (sub, email)");
  }

  return {
    userId: payload.sub as string,
    email: payload.email as string,
    tenantId: (payload["custom:tenant_id"] as string | undefined) ?? null,
    role: (payload["custom:role"] as string | undefined) ?? "viewer",
    isSuperadmin: payload["custom:is_superadmin"] === "true" || payload["custom:is_superadmin"] === true,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshSession = useCallback(async (): Promise<AuthUser | null> => {
    try {
      const session = await getCurrentSession();
      const parsed = parseSession(session);
      setUser(parsed);
      return parsed;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  const logout = useCallback(() => {
    signOut();
    setUser(null);
    window.location.href = "/login";
  }, []);

  useEffect(() => {
    refreshSession().finally(() => setIsLoading(false));
  }, [refreshSession]);

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
