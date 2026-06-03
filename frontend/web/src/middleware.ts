import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Verificar si hay token de Cognito en cookies (Next.js no puede leer localStorage)
  // La validación real del JWT ocurre en el backend — aquí solo redirecteamos al login
  // si no hay ninguna cookie de sesión de Cognito
  const hasCognitoToken = Array.from(request.cookies.keys()).some(
    (key) => key.includes("CognitoIdentityServiceProvider") || key.includes("amplify")
  );

  if (!hasCognitoToken && pathname !== "/") {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
