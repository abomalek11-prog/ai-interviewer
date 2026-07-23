import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { extractErrorMessage } from "@/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OAuthButtons } from "@/components/auth/OAuthButtons";
import { useAuth } from "@/context/AuthContext";

import { AuthLayout } from "./AuthLayout";

const schema = z
  .object({
    full_name: z.string().min(2, "Enter your full name"),
    email: z.string().email("Enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      await registerUser({ email: values.email, password: values.password, full_name: values.full_name });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setFormError(extractErrorMessage(error, "Could not create your account"));
    }
  };

  return (
    <AuthLayout>
      <div>
        <h2 className="text-[34px] font-bold">Create your account</h2>
        <p className="mt-2 text-muted-foreground">Start assessing candidates with AI-backed interviews.</p>
      </div>

      {formError && (
        <Alert variant="destructive" className="mt-6">
          {formError}
        </Alert>
      )}

      <form className="mt-6 grid gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="grid gap-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input id="full_name" autoComplete="name" {...register("full_name")} />
          {errors.full_name && <p className="text-xs text-destructive">{errors.full_name.message}</p>}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="email">Email address</Label>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="confirm_password">Confirm password</Label>
          <Input id="confirm_password" type="password" autoComplete="new-password" {...register("confirm_password")} />
          {errors.confirm_password && <p className="text-xs text-destructive">{errors.confirm_password.message}</p>}
        </div>
        <Button type="submit" className="mt-2 w-full" disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Create Account"}
        </Button>
      </form>

      <OAuthButtons />

      <p className="mt-2 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
