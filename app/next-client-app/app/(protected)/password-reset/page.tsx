"use client";

import { Formik, Form, Field, ErrorMessage } from "formik";
import * as Yup from "yup";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { passwordReset } from "@/api/password-reset";
import { useState } from "react";

// ✅ Validation schema
const validationSchema = Yup.object({
  newPassword: Yup.string().min(6, "Minimum 6 characters!").required("New password is required!"),
  confirmPassword: Yup.string()
    .oneOf([Yup.ref("newPassword"), ""], "Passwords must match!")
    .required("Confirm password is required!"),
});

const   = async (
  values: { newPassword: string; confirmPassword: string },
  setError: (error: string) => void,
  setSubmitted: (submitted: boolean) => void,
  setSubmitting: (isSubmitting: boolean) => void
) => {
  setError("");

  try {
    const res = await passwordReset({
      new_password: values.newPassword,
      confirm_password: values.confirmPassword,
    });

    if (res?.status && res.status !== 200) {
      setError(res?.detail || "Something went wrong.");
      console.error("Password reset error:", res);
    } else {
      setSubmitted(true);
    }
  } catch (err) {
    console.error("Password reset error:", err);
    setError("An error occurred while trying to reset the password.");
  }

  setSubmitting(false);
};

export default function PasswordResetPage() {
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  if (submitted) {
    return (
      <div className="flex min-h-96 items-center justify-center">
        <div className="w-full max-w-md p-8 space-y-4">
          <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
            Password Reset Successful
          </h1>
          <p className="text-center text-sm text-gray-600 dark:text-gray-300">
            Your password has been reset successfully. You can now log in with your new password.
          </p>
          <div className="text-sm text-center mt-2">
          <a href="/projects" className="text-blue-600 hover:underline">
            Back to Projects
          </a>
        </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-96 items-center justify-center">
      <div className="w-full max-w-md p-8 space-y-6">
        <h1 className="text-2xl font-semibold text-center text-gray-800 dark:text-white">
          Reset your password
        </h1>

        <Formik
          initialValues={{ newPassword: "", confirmPassword: "" }}
          validationSchema={validationSchema}
          onSubmit={(values, { setSubmitting }) =>
            handleSubmit(values, setError, setSubmitted, setSubmitting)
          }
        >
          {({ isSubmitting }) => (
            <Form className="space-y-4">
              {error && <Alert variant="destructive">{error}</Alert>}
              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <Field as={Input} id="newPassword" name="newPassword" type="password" placeholder="Enter new password" />
                <ErrorMessage name="newPassword" component="div" className="text-red-500 text-sm" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Field as={Input} id="confirmPassword" name="confirmPassword" type="password" placeholder="Re-enter password" />
                <ErrorMessage name="confirmPassword" component="div" className="text-red-500 text-sm" />
              </div>
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Reset Password"}
              </Button>
            </Form>
          )}
        </Formik>

        <div className="text-sm text-center mt-2">
          <a href="/projects" className="text-blue-600 hover:underline">
            Back to Projects
          </a>
        </div>
      </div>
    </div>
  );
}
