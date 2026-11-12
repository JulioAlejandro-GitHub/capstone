import type { ComponentProps } from "react";
import { FullFieldView } from "../components/FullFieldView";
export function AnalysisAreaPage(props: ComponentProps<typeof FullFieldView>) {
  return <FullFieldView {...props} isAnalysisArea={true} />;
}
