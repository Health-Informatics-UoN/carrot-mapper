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
import config from "@/tailwind.config";
import { getDataUsers } from "@/api/datasets";
import { useEffect, useState } from "react";
import { FindAndFormat } from "./FormikUtils";
import { getProjectsDataset } from "@/api/projects";

type Option = Object & {
  value: number;
  label: string | undefined;
};

async function fetchProjectMembers(dataset: string) {
  const projects = await getProjectsDataset(dataset);
  const users = await getDataUsers();
  const membersIds = new Set<number>();
  projects.results.forEach((project) => {
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
      styles={{
        multiValueLabel: (base) => ({
          ...base,
          color: "white",
        }),
        multiValueRemove: (base) => ({
          ...base,
          fontSize: "17px",
        }),
        singleValue: (base) => ({
          ...base,
          fontSize: "17px",
        }),
      }}
    />
  );
};

export const FormikSelectEditors = ({
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
  const {
    values: { dataset },
  } = useFormikContext<FormikValues>();

  const [editors, setOptions] = useState<Option[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (dataset !== 0 && dataset !== -1) {
        const editors = await fetchProjectMembers(dataset.toString());
        setOptions(editors);
      }
    };
    fetchData();
  }, [dataset]);

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
