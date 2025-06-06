import { Field, FieldInputProps, FieldProps, FormikProps } from "formik";
import Select from "react-select";
import makeAnimated from "react-select/animated";
import config from "@/tailwind.config";
import { useTheme } from "next-themes";

type Option = Object & {
  value: number;
  label: string | undefined;
};

const CustomSelect = ({
  field,
  form,
  isMulti = false,
  options,
  placeholder,
  isDisabled,
  required,
}: {
  options: Option[];
  placeholder: string;
  isMulti: boolean;
  field: FieldInputProps<any>;
  form: FormikProps<any>;
  isDisabled: boolean;
  required?: boolean;
}) => {
  const animatedComponents = makeAnimated();

  // Optional: detect dark mode for better contrast
  let isDark = false;
  if (typeof window !== "undefined") {
    isDark = document.documentElement.classList.contains("dark");
  }

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
      required={required}
    />
  );
};

export const FormikSelect = ({
  options,
  name,
  placeholder,
  isMulti,
  isDisabled,
  required,
}: {
  options: Option[];
  name: string;
  placeholder: string;
  isMulti: boolean;
  isDisabled: boolean;
  required?: boolean;
}) => {
  return (
    <Field name={name}>
      {({ field, form }: FieldProps<any>) => (
        <CustomSelect
          field={field}
          form={form}
          isMulti={isMulti}
          options={options}
          placeholder={placeholder}
          isDisabled={isDisabled}
          required={required}
        />
      )}
    </Field>
  );
};
