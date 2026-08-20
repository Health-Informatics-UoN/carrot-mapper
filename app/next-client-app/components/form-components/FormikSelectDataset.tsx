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
import { getDatasetList } from "@/api/datasets";
import { useEffect, useId, useState } from "react";
import { getAllProjects } from "@/api/projects";

type Option = {
  value: number;
  label: string | undefined;
};

type GroupedOption = {
  label: string;
  options: Option[];
};

async function fetchDataset(dataPartner: string): Promise<GroupedOption[]> {
  const datasets = await getDatasetList(dataPartner);
  const projects = await getAllProjects();

  // Initialize projectMap with all projects, ensuring each is represented
  const projectMap = new Map<number, GroupedOption>();
  projects.forEach((project) => {
    projectMap.set(project.id, {
      label: `Project: ${project.name}`,
      options: [], // Initially empty, to be filled with datasets or a placeholder
    });
  });

  // Process datasets, adding them to the appropriate project group in projectMap
  datasets.forEach((dataset) => {
    dataset.projects
      .map((project) => project.id)
      .forEach((projectId) => {
        const projectGroup = projectMap.get(projectId);
        if (projectGroup) {
          projectGroup.options.push({
            value: dataset.id,
            label: dataset.name,
          });
        }
      });
  });

  // Ensure all projects without datasets have a "None" option
  projectMap.forEach((group, projectId) => {
    if (group.options.length === 0) {
      group.options.push({
        value: -1, // A placeholder value for "None"
        label: "----------------------",
      });
    }
  });

  return Array.from(projectMap.values());
}

const CustomSelect = ({
  field,
  form,
  isMulti = false,
  options,
  placeholder,
  isDisabled,
  required,
}: {
  options?: GroupedOption[];
  placeholder: string;
  isMulti: boolean;
  field: FieldInputProps<any>;
  form: FormikProps<any>;
  isDisabled: boolean;
  required?: boolean;
}) => {
  const instanceId = useId();
  const animatedComponents = makeAnimated();
  const onChange = (newValue: any, actionMeta: any) => {
    const selectedValues = isMulti
      ? (newValue as Option[]).map((option) => option.value)
      : (newValue as Option).value;

    form.setFieldValue(field.name, selectedValues);
  };

  const selected = () => {
    const flattenedOptions = options
      ? options.flatMap((group) => group.options)
      : [];
    return flattenedOptions.filter((option: Option) =>
      Array.isArray(field.value)
        ? field.value.includes(option.value)
        : field.value === option.value
    );
  };

  return (
    <Select
      instanceId={instanceId}
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
        singleValue: (base) => ({
          ...base,
          fontSize: "17px",
        }),
      }}
      required={required}
    />
  );
};

export const FormikSelectDataset = ({
  name,
  placeholder,
  isMulti,
  isDisabled,
  required,
  reloadDataset,
}: {
  name: string;
  placeholder: string;
  isMulti: boolean;
  isDisabled: boolean;
  required?: boolean;
  reloadDataset?: boolean;
}) => {
  const {
    values: { dataPartner },
  } = useFormikContext<FormikValues>();

  const [datasets, setOptions] = useState<GroupedOption[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (dataPartner !== 0 || reloadDataset) {
        const dataset = await fetchDataset(dataPartner.toString());
        setOptions(dataset);
      }
    };
    fetchData();
  }, [dataPartner, reloadDataset]);

  return (
    <Field name={name}>
      {({ field, form }: FieldProps<any>) => (
        <CustomSelect
          field={field}
          form={form}
          isMulti={isMulti}
          options={datasets}
          placeholder={placeholder}
          isDisabled={isDisabled}
          required={required}
        />
      )}
    </Field>
  );
};
