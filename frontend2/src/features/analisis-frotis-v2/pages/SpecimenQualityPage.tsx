import type { ComponentProps } from "react";
import { QualityView } from "../components/QualityView";
export function SpecimenQualityPage(props: ComponentProps<typeof QualityView>) {
  return <QualityView {...props} />;
}
