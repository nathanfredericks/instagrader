"use client"

import { useActionState } from "react"
import Link from "next/link"
import { CircleAlert } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { signupAction, type AuthActionState } from "@/lib/actions/auth"

export function SignupForm({ ...props }: React.ComponentProps<typeof Card>) {
  const [state, formAction, pending] = useActionState<AuthActionState, FormData>(
    signupAction,
    null
  )

  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>Create an account</CardTitle>
        <CardDescription>
          Enter your information below to create your account
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction}>
          <FieldGroup>
            {state?.error && (
              <Alert variant="destructive">
                <CircleAlert />
                <AlertDescription>{state.error}</AlertDescription>
              </Alert>
            )}
            <Field>
              <FieldLabel htmlFor="full_name">Full Name</FieldLabel>
              <Input
                id="full_name"
                name="full_name"
                type="text"
                placeholder="John Doe"
                defaultValue={state?.values?.full_name ?? ""}
                required
              />
              {state?.fieldErrors?.full_name && (
                <FieldError>
                  {state.fieldErrors.full_name.join(", ")}
                </FieldError>
              )}
            </Field>
            <Field>
              <FieldLabel htmlFor="email">Email</FieldLabel>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="m@example.com"
                defaultValue={state?.values?.email ?? ""}
                required
              />
              <FieldDescription>
                We&apos;ll use this to contact you. We will not share your
                email with anyone else.
              </FieldDescription>
              {state?.fieldErrors?.email && (
                <FieldError>
                  {state.fieldErrors.email.join(", ")}
                </FieldError>
              )}
            </Field>
            <Field>
              <FieldLabel htmlFor="password">Password</FieldLabel>
              <Input
                id="password"
                name="password"
                type="password"
                required
              />
              <FieldDescription>
                Must be at least 8 characters long.
              </FieldDescription>
              {state?.fieldErrors?.password && (
                <FieldError>
                  {state.fieldErrors.password.join(", ")}
                </FieldError>
              )}
            </Field>
            <Field>
              <FieldLabel htmlFor="password_confirm">
                Confirm Password
              </FieldLabel>
              <Input
                id="password_confirm"
                name="password_confirm"
                type="password"
                required
              />
              <FieldDescription>
                Please confirm your password.
              </FieldDescription>
              {state?.fieldErrors?.password_confirm && (
                <FieldError>
                  {state.fieldErrors.password_confirm.join(", ")}
                </FieldError>
              )}
            </Field>
            <Field>
              <Button type="submit" disabled={pending}>
                {pending ? "Creating account..." : "Create Account"}
              </Button>
              <FieldDescription className="text-center">
                Already have an account?{" "}
                <Link href="/login">Login</Link>
              </FieldDescription>
            </Field>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}
