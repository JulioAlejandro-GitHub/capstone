import type { ComponentProps } from "react";
import { ReportView } from "../components/ReportView";
export function ReportPage(props: ComponentProps<typeof ReportView>) {
  return <ReportView {...props} />;
}
