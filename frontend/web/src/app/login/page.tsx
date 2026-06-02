export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 rounded-lg border border-border p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold">CodeLabs Billing</h1>
          <p className="text-sm text-muted-foreground">Inicia sesión en tu cuenta</p>
        </div>
        {/* TODO Fase 2: implementar formulario de login con Cognito */}
        <p className="text-center text-sm text-muted-foreground">
          Login con Cognito — implementar en Fase 2
        </p>
      </div>
    </main>
  );
}
