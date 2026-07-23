import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/context/AuthContext";
import { tokenStorage } from "@/api/tokenStorage";

import { AuthLayout } from "./AuthLayout";

export function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (!accessToken || !refreshToken) {
      setError("Sign-in did not complete. Please try again.");
      return;
    }

    tokenStorage.setTokens(accessToken, refreshToken);
    refreshUser()
      .then(() => navigate("/dashboard", { replace: true }))
      .catch(() => setError("Could not complete sign-in. Please try again."));
  }, [searchParams, refreshUser, navigate]);

  return (
    <AuthLayout>
      <div>
        <h2 className="text-[34px] font-bold">Signing you in…</h2>
        <p className="mt-2 text-muted-foreground">Hang tight while we finish setting up your session.</p>
      </div>
      {error && (
        <Alert variant="destructive" className="mt-6">
          {error}{" "}
          <Link to="/login" className="font-semibold underline">
            Back to sign in
          </Link>
        </Alert>
      )}
    </AuthLayout>
  );
}
