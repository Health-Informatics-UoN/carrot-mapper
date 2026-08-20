"use client";

import { Formik } from "formik";
import { Save } from "lucide-react";
import { toast } from "sonner";
import { updateUserProfile } from "@/api/users";
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
  data_partner: number | null;
  orcid: string;
}

export function ProfileForm({
  user,
  dataPartners,
}: {
  user: UserProfile;
  dataPartners: DataPartner[];
}) {
  const dataPartnerOptions = FormDataFilter<DataPartner>(dataPartners);

  const handleSubmit = async (data: FormData) => {
    const response = await updateUserProfile(user.id, {
      data_partner: data.data_partner || null,
      orcid: data.orcid || null,
    });
    if (response) {
      toast.error(`Update profile failed. Error: ${response.errorMessage}`);
    } else {
      toast.success("Profile updated!");
    }
  };

  return (
    <Formik
      initialValues={{
        data_partner: user.profile.data_partner?.id ?? null,
        orcid: user.profile.orcid ?? "",
      }}
      onSubmit={(data) => {
        handleSubmit(data);
      }}
    >
      {({ handleChange, handleSubmit }) => (
        <form className="w-full max-w-xl" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-5">
            <FormItem>
              <FormLabel>Data Partner</FormLabel>
              <FormDescription>
                The Data Partner organisation you are affiliated with.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={dataPartnerOptions}
                  name="data_partner"
                  placeholder="Choose a Data Partner"
                  isMulti={false}
                  isDisabled={false}
                />
              </FormControl>
            </FormItem>

            <FormField name="orcid">
              {({ field }) => (
                <FormItem>
                  <FormLabel>ORCID iD</FormLabel>
                  <FormDescription>
                    Your ORCID iD, in the format 0000-0000-0000-0000.
                  </FormDescription>
                  <FormControl>
                    <Input
                      {...field}
                      onChange={handleChange}
                      name="orcid"
                      placeholder="0000-0001-2345-6789"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>

            <div className="flex mt-3">
              <Button type="submit">
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
