import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signIn } from "@/lib/auth";
import { useAuth } from "@/lib/auth-context";
import { getApiErrorMessage } from "@/lib/api-errors";
import { required } from "@/lib/validation";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Form";

export function LoginPage() {
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");

    const nextErrors = {
      email: required(email, "Correo electrónico"),
      password: required(password, "Contraseña"),
    };
    setFieldErrors(nextErrors);
    if (nextErrors.email || nextErrors.password) return;

    setIsLoading(true);
    try {
      await signIn(email, password);
      await refreshSession();
      navigate("/dashboard");
    } catch (err: unknown) {
      // Cognito SDK lanza objetos con `name` como código de error (no depender del mensaje)
      const cognitoName = (typeof err === "object" && err !== null && "name" in err)
        ? (err as { name: string }).name
        : "";
      if (cognitoName === "NotAuthorizedException") {
        setError("Correo o contraseña incorrectos");
      } else if (cognitoName === "UserNotFoundException") {
        setError("Usuario no encontrado");
      } else {
        setError(getApiErrorMessage(err, "Error al iniciar sesión"));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-sidebar px-4">
      <Card className="w-full max-w-md border-white/10 bg-card shadow-lift">
        <CardContent className="space-y-7 p-8">
          <div className="space-y-3 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-brand text-sm font-black text-brand-foreground shadow-lift">
              CL
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">CodeLabs Billing</h1>
              <p className="mt-1 text-sm text-muted-foreground">Inicia sesión en tu cuenta</p>
            </div>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="Correo electrónico" error={fieldErrors.email}>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="tu@empresa.com"
                value={email}
                hasError={!!fieldErrors.email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>
            <Field label="Contraseña" error={fieldErrors.password}>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="************"
                value={password}
                hasError={!!fieldErrors.password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            {error && <Alert tone="danger">{error}</Alert>}
            <Button type="submit" disabled={!email || !password} isLoading={isLoading} className="w-full">
              Iniciar sesión
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
