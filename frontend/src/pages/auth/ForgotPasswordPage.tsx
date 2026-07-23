import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { authApi } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { AuthLayout } from "./AuthLayout";

type Step = "email" | "otp" | "reset";

const emailSchema = z.object({ email: z.string().email("Enter a valid email address") });
const otpSchema = z.object({ code: z.string().length(6, "Enter the 6-digit code") });
const resetSchema = z
  .object({
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const emailForm = useForm<z.infer<typeof emailSchema>>({ resolver: zodResolver(emailSchema) });
  const otpForm = useForm<z.infer<typeof otpSchema>>({ resolver: zodResolver(otpSchema) });
  const resetForm = useForm<z.infer<typeof resetSchema>>({ resolver: zodResolver(resetSchema) });

  const submitEmail = emailForm.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await authApi.forgotPassword(values.email);
      setEmail(values.email);
      setNotice("If that email is registered, a 6-digit code has been sent.");
      setStep("otp");
    } catch (error) {
      setFormError(extractErrorMessage(error));
    }
  });

  const submitOtp = otpForm.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await authApi.verifyOtp(email, values.code);
      setCode(values.code);
      setNotice(null);
      setStep("reset");
    } catch (error) {
      setFormError(extractErrorMessage(error, "Invalid or expired code"));
    }
  });

  const submitReset = resetForm.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await authApi.resetPassword({ email, code, new_password: values.new_password });
      navigate("/login", { replace: true, state: { notice: "Password updated. Please sign in." } });
    } catch (error) {
      setFormError(extractErrorMessage(error, "Could not reset your password"));
    }
  });

  return (
    <AuthLayout>
      <div>
        <h2 className="text-[34px] font-bold">Reset your password</h2>
        <p className="mt-2 text-muted-foreground">
          {step === "email" && "Enter your account email to receive a verification code."}
          {step === "otp" && `Enter the 6-digit code sent to ${email}.`}
          {step === "reset" && "Choose a new password for your account."}
        </p>
      </div>

      {notice && (
        <Alert variant="success" className="mt-6">
          {notice}
        </Alert>
      )}
      {formError && (
        <Alert variant="destructive" className="mt-6">
          {formError}
        </Alert>
      )}

      {step === "email" && (
        <form className="mt-6 grid gap-4" onSubmit={submitEmail} noValidate>
          <div className="grid gap-2">
            <Label htmlFor="email">Email address</Label>
            <Input id="email" type="email" autoComplete="email" {...emailForm.register("email")} />
            {emailForm.formState.errors.email && (
              <p className="text-xs text-destructive">{emailForm.formState.errors.email.message}</p>
            )}
          </div>
          <Button type="submit" className="mt-2 w-full" disabled={emailForm.formState.isSubmitting}>
            {emailForm.formState.isSubmitting ? "Sending code..." : "Send Verification Code"}
          </Button>
        </form>
      )}

      {step === "otp" && (
        <form className="mt-6 grid gap-4" onSubmit={submitOtp} noValidate>
          <div className="grid gap-2">
            <Label htmlFor="code">Verification code</Label>
            <Input id="code" inputMode="numeric" maxLength={6} placeholder="000000" {...otpForm.register("code")} />
            {otpForm.formState.errors.code && <p className="text-xs text-destructive">{otpForm.formState.errors.code.message}</p>}
          </div>
          <Button type="submit" className="mt-2 w-full" disabled={otpForm.formState.isSubmitting}>
            {otpForm.formState.isSubmitting ? "Verifying..." : "Verify Code"}
          </Button>
        </form>
      )}

      {step === "reset" && (
        <form className="mt-6 grid gap-4" onSubmit={submitReset} noValidate>
          <div className="grid gap-2">
            <Label htmlFor="new_password">New password</Label>
            <Input id="new_password" type="password" autoComplete="new-password" {...resetForm.register("new_password")} />
            {resetForm.formState.errors.new_password && (
              <p className="text-xs text-destructive">{resetForm.formState.errors.new_password.message}</p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="confirm_password">Confirm new password</Label>
            <Input id="confirm_password" type="password" autoComplete="new-password" {...resetForm.register("confirm_password")} />
            {resetForm.formState.errors.confirm_password && (
              <p className="text-xs text-destructive">{resetForm.formState.errors.confirm_password.message}</p>
            )}
          </div>
          <Button type="submit" className="mt-2 w-full" disabled={resetForm.formState.isSubmitting}>
            {resetForm.formState.isSubmitting ? "Updating..." : "Update Password"}
          </Button>
        </form>
      )}

      <p className="mt-2 text-center text-sm text-muted-foreground">
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Back to sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
