"use client";

import { Formik } from "formik";
import { AlertCircle, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { createProject } from "@/api/projects";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { FormikSelect } from "../form-components/FormikSelect";
import { FormDataFilter } from "../form-components/FormikUtils";

interface FormData {
  name: string;
  members: number[];
  admins: number[];
}

export function CreateProjectForm({
  users,
  setDialogOpened,
}: {
  users: User[];
  setDialogOpened: (dialogOpened: boolean) => void;
}) {
  const userOptions = FormDataFilter<User>(users || []);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: FormData) => {
    const submittingData = {
      name: data.name,
      members: data.members || [],
      admins: data.admins || [],
    };

    const response = await createProject(submittingData);

    if (response) {
      setError(response.errorMessage);
      toast.error("Add New Project failed. Fix the error(s) first");
    } else {
      toast.success("New Project created!");
      setError(null);
      setDialogOpened(false);
    }
  };

  return (
    <>
      {error && (
        <Alert variant="destructive" className="mb-3">
          <div>
            <AlertTitle className="flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              Add New Project Failed. Error:
            </AlertTitle>
            <AlertDescription>
              <ul>
                {error.split(" * ").map((err, index) => (
                  <li key={index}>* {err}</li>
                ))}
                <li>* Notice: The name of a project should be unique *</li>
              </ul>
            </AlertDescription>
          </div>
        </Alert>
      )}
      <Formik
        initialValues={{
          name: "",
          members: [],
          admins: [],
        }}
        onSubmit={(data) => {
          toast.info("Creating Project ...");
          handleSubmit(data);
        }}
      >
        {({ values, handleChange, handleSubmit }) => (
          <form className="w-full max-w-2xl" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-5">
              <FormField name="name">
                {({ field }) => (
                  <FormItem>
                    <FormLabel>Project Name</FormLabel>
                    <FormDescription>Name of the new Project.</FormDescription>
                    <FormControl>
                      <Input
                        {...field}
                        onChange={handleChange}
                        name="name"
                        required
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <FormItem>
                <FormLabel>Members</FormLabel>
                <FormDescription>
                  Users who have access to this Project and its Datasets. You
                  will automatically be added as a member.
                </FormDescription>
                <FormControl>
                  <FormikSelect
                    options={userOptions}
                    name="members"
                    placeholder="Choose members"
                    isMulti={true}
                    isDisabled={false}
                  />
                </FormControl>
              </FormItem>

              <FormItem>
                <FormLabel>Admins</FormLabel>
                <FormDescription>
                  Project admins can edit the Project and manage its members
                  and admins. You will automatically be added as an admin.
                </FormDescription>
                <FormControl>
                  <FormikSelect
                    options={userOptions}
                    name="admins"
                    placeholder="Choose admins"
                    isMulti={true}
                    isDisabled={false}
                  />
                </FormControl>
              </FormItem>

              <div className="mb-5">
                <Button type="submit" disabled={values.name === ""}>
                  <Plus />
                  Create Project
                </Button>
              </div>
            </div>
          </form>
        )}
      </Formik>
    </>
  );
}
