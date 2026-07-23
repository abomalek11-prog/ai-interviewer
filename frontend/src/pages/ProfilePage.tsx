import { zodResolver } from "@hookform/resolvers/zod";
import { Camera, LockKeyhole, ShieldCheck } from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { extractErrorMessage } from "@/api/client";
import { usersApi } from "@/api/endpoints";
import { Alert } from "@/components/ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";

const MAX_AVATAR_BYTES = 5 * 1024 * 1024;

const profileSchema = z.object({
  full_name: z.string().min(2, "Enter your full name"),
  title: z.string().optional(),
  bio: z.string().optional(),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

function initialsOf(name: string) {
  return name.split(" ").map((p) => p[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
}

export function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  const profileForm = useForm<z.infer<typeof profileSchema>>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name ?? "", title: user?.title ?? "", bio: user?.bio ?? "" },
  });
  const passwordForm = useForm<z.infer<typeof passwordSchema>>({ resolver: zodResolver(passwordSchema) });

  const saveProfile = profileForm.handleSubmit(async (values) => {
    setProfileError(null);
    setProfileNotice(null);
    try {
      await usersApi.updateProfile(values);
      await refreshUser();
      setProfileNotice("Profile updated");
    } catch (err) {
      setProfileError(extractErrorMessage(err));
    }
  });

  const savePassword = passwordForm.handleSubmit(async (values) => {
    setPasswordError(null);
    setPasswordNotice(null);
    try {
      await usersApi.changePassword({ current_password: values.current_password, new_password: values.new_password });
      passwordForm.reset();
      setPasswordNotice("Password updated");
    } catch (err) {
      setPasswordError(extractErrorMessage(err, "Could not update your password"));
    }
  });

  const handleAvatarChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setAvatarError(null);
    if (!file.type.startsWith("image/")) {
      setAvatarError("Please choose an image file");
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setAvatarError("Image must be smaller than 5MB");
      return;
    }

    setIsUploadingAvatar(true);
    try {
      await usersApi.uploadAvatar(file);
      await refreshUser();
    } catch (err) {
      setAvatarError(extractErrorMessage(err, "Could not upload image"));
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  if (!user) return null;

  return (
    <>
      <section className="mb-7">
        <h1 className="text-4xl leading-tight font-bold">Account Settings</h1>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(280px,0.9fr)_minmax(0,1.9fr)]">
        <Card className="grid justify-items-center content-start gap-1 p-9 text-center">
          <div className="relative">
            <Avatar className="size-33 border-4 border-white shadow-md">
              {user.profile_picture_url && <AvatarImage src={user.profile_picture_url} alt={user.full_name} />}
              <AvatarFallback className="text-3xl">{initialsOf(user.full_name)}</AvatarFallback>
            </Avatar>
            <button
              type="button"
              onClick={() => avatarInputRef.current?.click()}
              disabled={isUploadingAvatar}
              aria-label="Change profile photo"
              className="absolute right-0 bottom-0 grid size-10 place-items-center rounded-full border-2 border-white bg-primary text-primary-foreground shadow-md transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <Camera size={18} />
            </button>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarChange}
            />
          </div>
          {avatarError && (
            <p className="mt-2 text-xs text-destructive" role="alert">
              {avatarError}
            </p>
          )}
          <h2 className="mt-6 text-2xl font-bold">{user.full_name}</h2>
          <p className="mt-1 max-w-60 text-foreground/70">{user.title ?? "No title set"}</p>
        </Card>

        <Card className="p-8">
          <div className="flex items-center justify-between">
            <CardTitle>Personal Information</CardTitle>
            <ShieldCheck size={24} />
          </div>
          {profileNotice && <Alert variant="success" className="mt-4">{profileNotice}</Alert>}
          {profileError && <Alert variant="destructive" className="mt-4">{profileError}</Alert>}
          <form onSubmit={saveProfile} className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label>FULL NAME</Label>
              <Input {...profileForm.register("full_name")} />
              {profileForm.formState.errors.full_name && (
                <p className="text-xs text-destructive">{profileForm.formState.errors.full_name.message}</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label>EMAIL ADDRESS</Label>
              <Input value={user.email} disabled />
            </div>
            <div className="grid gap-2">
              <Label>JOB TITLE</Label>
              <Input {...profileForm.register("title")} />
            </div>
            <div className="col-span-full grid gap-2">
              <Label>BIO</Label>
              <Textarea rows={4} {...profileForm.register("bio")} />
            </div>
            <div className="col-span-full flex justify-end">
              <Button type="submit" disabled={profileForm.formState.isSubmitting}>
                {profileForm.formState.isSubmitting ? "Saving..." : "Save Details"}
              </Button>
            </div>
          </form>
        </Card>

        <Card className="col-span-full flex min-h-67 flex-col justify-center bg-secondary p-10 text-white lg:col-start-2">
          <h2 className="text-2xl font-bold">Security & Integrity</h2>
          <p className="mt-5 max-w-75 text-white/70">
            Manage account protection and authentication methods to ensure your data remains secure.
          </p>
        </Card>

        <Card className="col-span-full p-8 lg:col-start-2">
          <div className="flex items-center gap-3">
            <LockKeyhole size={23} />
            <CardTitle>Change Password</CardTitle>
          </div>
          {passwordNotice && <Alert variant="success" className="mt-4">{passwordNotice}</Alert>}
          {passwordError && <Alert variant="destructive" className="mt-4">{passwordError}</Alert>}
          <form onSubmit={savePassword} className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label>CURRENT PASSWORD</Label>
              <Input type="password" {...passwordForm.register("current_password")} />
              {passwordForm.formState.errors.current_password && (
                <p className="text-xs text-destructive">{passwordForm.formState.errors.current_password.message}</p>
              )}
            </div>
            <span />
            <div className="grid gap-2">
              <Label>NEW PASSWORD</Label>
              <Input type="password" {...passwordForm.register("new_password")} />
              {passwordForm.formState.errors.new_password && (
                <p className="text-xs text-destructive">{passwordForm.formState.errors.new_password.message}</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label>CONFIRM NEW PASSWORD</Label>
              <Input type="password" {...passwordForm.register("confirm_password")} />
              {passwordForm.formState.errors.confirm_password && (
                <p className="text-xs text-destructive">{passwordForm.formState.errors.confirm_password.message}</p>
              )}
            </div>
            <div className="col-span-full flex justify-end">
              <Button type="submit" disabled={passwordForm.formState.isSubmitting}>
                {passwordForm.formState.isSubmitting ? "Updating..." : "Update Password"}
              </Button>
            </div>
          </form>
        </Card>
      </section>
    </>
  );
}
