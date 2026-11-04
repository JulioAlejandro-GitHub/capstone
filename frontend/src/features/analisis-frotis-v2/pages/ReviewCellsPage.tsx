import { DifferentialSidebar } from "../components/DifferentialSidebar";
import { CellGallery } from "../components/CellGallery";
import { SlideViewer } from "../components/SlideViewer";
import type { ComponentProps } from "react";
type Props = {
  sidebar: ComponentProps<typeof DifferentialSidebar>;
  gallery: ComponentProps<typeof CellGallery>;
  viewer: ComponentProps<typeof SlideViewer>;
  layoutMode: "split" | "grid" | "slide";
};
export function ReviewCellsPage({
  sidebar,
  gallery,
  viewer,
  layoutMode,
}: Props) {
  return (
    <div className="flex-1 flex h-full w-full overflow-hidden">
      <DifferentialSidebar {...sidebar} />
      {layoutMode !== "slide" && <CellGallery {...gallery} />}
      {layoutMode !== "grid" && <SlideViewer {...viewer} />}
    </div>
  );
}
