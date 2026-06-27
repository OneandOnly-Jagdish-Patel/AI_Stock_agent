import { useEffect, useState } from "react";

interface Props {
  value?: string;
  onChange: (date: string) => void;
}

export function DateFilter({ value, onChange }: Props) {
  const [date, setDate] = useState(value ?? "");

  useEffect(() => {
    if (value) setDate(value);
  }, [value]);

  return (
    <div className="date-picker">
      <label htmlFor="date-filter">Date (CST)</label>
      <input
        id="date-filter"
        type="date"
        value={date}
        onChange={(e) => {
          setDate(e.target.value);
          onChange(e.target.value);
        }}
      />
    </div>
  );
}

export function useDateFilter(initial?: string) {
  const [date, setDate] = useState(initial ?? "");
  return { date, setDate };
}
