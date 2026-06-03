import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from "amazon-cognito-identity-js";

const poolData = {
  UserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID as string,
  ClientId: import.meta.env.VITE_COGNITO_CLIENT_ID as string,
};

let userPool: CognitoUserPool | null = null;

function getPool(): CognitoUserPool {
  if (!userPool) {
    userPool = new CognitoUserPool(poolData);
  }
  return userPool;
}

export async function signIn(email: string, password: string): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    const authDetails = new AuthenticationDetails({ Username: email, Password: password });
    const cognitoUser = new CognitoUser({ Username: email, Pool: getPool() });

    cognitoUser.authenticateUser(authDetails, {
      onSuccess: resolve,
      onFailure: reject,
    });
  });
}

export function signOut(): void {
  const currentUser = getPool().getCurrentUser();
  currentUser?.signOut();
}

export function getCurrentSession(): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    const currentUser = getPool().getCurrentUser();
    if (!currentUser) {
      reject(new Error("No hay usuario activo"));
      return;
    }
    currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) {
        reject(err || new Error("Sesión inválida"));
        return;
      }
      resolve(session);
    });
  });
}

export async function getAccessToken(): Promise<string> {
  const session = await getCurrentSession();
  return session.getAccessToken().getJwtToken();
}

// El ID Token contiene los custom claims de Cognito (custom:tenant_id, custom:role, etc.)
// que el Lambda Authorizer necesita para extraer el contexto del usuario.
// Para APIs propias con Cognito como único IdP, enviar el ID Token es el patrón correcto.
export async function getIdToken(): Promise<string> {
  const session = await getCurrentSession();
  return session.getIdToken().getJwtToken();
}
