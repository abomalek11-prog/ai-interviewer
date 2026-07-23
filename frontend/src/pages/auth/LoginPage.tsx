import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { extractErrorMessage } from "@/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OAuthButtons } from "@/components/auth/OAuthButtons";
import { useAuth } from "@/context/AuthContext";

import { AuthLayout } from "./AuthLayout";

const schema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [formError, setFormError] = useState<string | null>(searchParams.get("oauth_error") ? "Social sign-in failed. Please try again." : null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      await login(values.email, values.password);
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      setFormError(extractErrorMessage(error, "Invalid email or password"));
    }
  };

  return (
    <AuthLayout>
      <div>
        <h2 className="text-[34px] font-bold">Welcome back</h2>
        <p className="mt-2 text-muted-foreground">Sign in to manage interviews, reports, and hiring decisions.</p>
      </div>

      {formError && (
        <Alert variant="destructive" className="mt-6">
          {formError}
        </Alert>
      )}

      <form className="mt-6 grid gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="grid gap-2">
          <Label htmlFor="email">Email address</Label>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs font-semibold text-primary hover:underline">
              Forgot password?
            </Link>
          </div>
          <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
        <Button type="submit" className="mt-2 w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign In"}
        </Button>
      </form>

      <OAuthButtons />

      <p className="mt-2 text-center text-sm text-muted-foreground">
        Don't have an account?{" "}
        <Link to="/register" className="font-semibold text-primary hover:underline">
          Create one
        </Link>
      </p>
    </AuthLayout>
  );
}
