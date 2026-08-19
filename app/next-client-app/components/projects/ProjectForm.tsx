"use client";

import { Formik } from "formik";
import { Save } from "lucide-react";
import { toast } from "sonner";
import { updateProjectDetails } from "@/api/projects";
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
import { Textarea } from "@/components/ui/textarea";
import { FormikSelect } from "../form-components/FormikSelect";
import { FormDataFilter } from "../form-components/FormikUtils";

interface FormData {
  name: string;
  description: string;
  members: number[];
  admins: number[];
}

export function ProjectForm({
  project,
  users,
  permissions,
}: {
  project: Project;
  users: User[];
  permissions: Permission[];
}) {
  const canUpdate = permissions.includes("CanAdmin");

  const userOptions = FormDataFilter<User>(users);
  const initialMembersFilter = FormDataFilter<User>(project.members);
  const initialAdminsFilter = FormDataFilter<User>(project.admins);

  const handleSubmit = async (data: FormData) => {
    const submittingData = {
      name: data.name,
      description: data.description,
      members: data.members || [],
      admins: data.admins || [],
    };
    const response = await updateProjectDetails(project.id, submittingData);
    if (response) {
      toast.error(`Update Project failed. Error: ${response.errorMessage}`);
    } else {
      toast.success("Update Project successful!");
    }
  };

  return (
    <Formik
      initialValues={{
        name: project.name,
        description: project.description ?? "",
        members: initialMembersFilter.map((member) => member.value),
        admins: initialAdminsFilter.map((admin) => admin.value),
      }}
      onSubmit={(data) => {
        handleSubmit(data);
      }}
    >
      {({ handleChange, handleSubmit }) => (
        <form className="w-full max-w-2xl" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-5">
            <FormField name="name">
              {({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormDescription>Name of the Project.</FormDescription>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder={project.name}
                      onChange={handleChange}
                      name="name"
                      disabled={!canUpdate}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>

            <FormField name="description">
              {({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormDescription>
                    Optional description of the Project.
                  </FormDescription>
                  <FormControl>
                    <Textarea
                      {...field}
                      onChange={handleChange}
                      name="description"
                      disabled={!canUpdate}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>

            <FormItem>
              <FormLabel>Members</FormLabel>
              <FormDescription>
                Users who have access to this Project and its Datasets.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={userOptions}
                  name="members"
                  placeholder="Choose members"
                  isMulti={true}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <FormItem>
              <FormLabel>Admins</FormLabel>
              <FormDescription>
                Project admins can edit the Project and manage its members and
                admins.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={userOptions}
                  name="admins"
                  placeholder="Choose admins"
                  isMulti={true}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <div className="flex mt-3">
              <Button type="submit" disabled={!canUpdate}>
                <Save />
                Save
              </Button>
            </div>
          </div>
        </form>
      )}
    </Formik>
  );
}
