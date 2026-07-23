import { useEffect, useState } from "react";

import { authApi, type OAuthProvider } from "@/api/endpoints";
import { Button } from "@/components/ui/button";

const PROVIDER_LABELS: Record<OAuthProvider, string> = {
  google: "Google",
  github: "GitHub",
  apple: "Apple",
  x: "X",
};

export function OAuthButtons() {
  const [available, setAvailable] = useState<OAuthProvider[]>([]);

  useEffect(() => {
    let active = true;
    authApi
      .oauthProviders()
      .then((providers) => {
        if (!active) return;
        setAvailable((Object.keys(providers) as OAuthProvider[]).filter((key) => providers[key]));
      })
      .catch(() => setAvailable([]));
    return () => {
      active = false;
    };
  }, []);

  if (available.length === 0) return null;

  return (
    <div className="mt-6 grid gap-3">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        <span>or continue with</span>
        <div className="h-px flex-1 bg-border" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {available.map((provider) => (
          <Button
            key={provider}
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => {
              window.location.href = authApi.oauthLoginUrl(provider);
            }}
          >
            {PROVIDER_LABELS[provider]}
          </Button>
        ))}
      </div>
    </div>
  );
}
