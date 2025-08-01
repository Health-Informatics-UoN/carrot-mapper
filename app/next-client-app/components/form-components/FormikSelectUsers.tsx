import {
  Field,
  FieldInputProps,
  FieldProps,
  FormikProps,
  FormikValues,
  useFormikContext,
} from "formik";
import Select from "react-select";
import makeAnimated from "react-select/animated";
import { getDataUsers } from "@/api/datasets";
import { useEffect, useState } from "react";
import { FindAndFormat } from "./FormikUtils";
import { getAllProjects } from "@/api/projects";

type Option = Object & {
  value: number;
  label: string | undefined;
};

async function fetchProjectMembers(selectedProjects: number[]) {
  const allProjects = await getAllProjects();
  const filterProjects = allProjects.filter((project) =>
    selectedProjects.includes(project.id)
  );
  const users = await getDataUsers();
  const membersIds = new Set<number>();
  filterProjects.forEach((project) => {
    project.members.forEach((member) => {
      membersIds.add(member.id);
    });
  });
  const membersArray = Array.from(membersIds);
  return FindAndFormat(users, membersArray);
}

const CustomSelect = ({
  field,
  form,
  isMulti = false,
  options,
  placeholder,
  isDisabled,
}: {
  options?: Option[];
  placeholder: string;
  isMulti: boolean;
  field: FieldInputProps<any>;
  form: FormikProps<any>;
  isDisabled: boolean;
}) => {
  const animatedComponents = makeAnimated();
  const onChange = (newValue: any, actionMeta: any) => {
    const selectedValues = isMulti
      ? (newValue as Option[]).map((option) => option.value)
      : (newValue as Option).value;

    form.setFieldValue(field.name, selectedValues);
  };

  const selected = () => {
    return options
      ? options.filter((option: Option) =>
          Array.isArray(field.value)
            ? field.value.includes(option.value)
            : field.value === option.value
        )
      : [];
  };

  return (
    <Select
      name={field.name}
      value={selected()}
      onChange={onChange}
      placeholder={placeholder}
      options={options}
      isMulti={isMulti}
      className="my-react-select-container"
      classNamePrefix="my-react-select"
      isDisabled={isDisabled}
      components={animatedComponents}
    />
  );
};

export const FormikSelectUsers = ({
  name,
  placeholder,
  isMulti,
  isDisabled,
}: {
  name: string;
  placeholder: string;
  isMulti: boolean;
  isDisabled: boolean;
}) => {
  const formik = useFormikContext<FormikValues>();
  const projects = formik?.values?.projects;
  const [editors, setOptions] = useState<Option[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (projects && projects !== 0) {
        const editors = await fetchProjectMembers(projects);
        setOptions(editors);
      }
    };
    fetchData();
  }, [projects]);

  return (
    <Field name={name}>
      {({ field, form }: FieldProps<any>) => (
        <CustomSelect
          field={field}
          form={form}
          isMulti={isMulti}
          options={editors}
          placeholder={placeholder}
          isDisabled={isDisabled}
        />
      )}
    </Field>
  );
};
