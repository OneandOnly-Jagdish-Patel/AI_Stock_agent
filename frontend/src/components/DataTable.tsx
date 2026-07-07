import type { ReactNode } from "react";

interface Props {
  desktop: ReactNode;
  mobile: ReactNode;
}

export function DataTable({ desktop, mobile }: Props) {
  return (
    <>
      <div className="data-table-desktop">{desktop}</div>
      <div className="data-table-mobile">{mobile}</div>
    </>
  );
}
