import type { ComponentProps } from "react";
import { FullFieldView } from "../components/FullFieldView";
export function FullFieldReviewPage(
  props: ComponentProps<typeof FullFieldView>,
) {
  return <FullFieldView {...props} isAnalysisArea={false} />;
}
