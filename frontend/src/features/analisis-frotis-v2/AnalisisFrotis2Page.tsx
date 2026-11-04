import { useFrotisDemo } from "./hooks/useFrotisDemo";
import { ReportPage } from "./pages/ReportPage";
import { AnalysisAreaPage } from "./pages/AnalysisAreaPage";
import { SpecimenQualityPage } from "./pages/SpecimenQualityPage";
import { FullFieldReviewPage } from "./pages/FullFieldReviewPage";
import { ReviewCellsPage } from "./pages/ReviewCellsPage";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { workflowRoutes, frotis2Base } from "./routes";
import "./styles/tokens_frotis_v2.css";
import "./styles/module.css";
import "./styles/layout.css";
import "./styles/viewer.css";
import type { WorkflowTab, CaseStatus } from "./types/visor";
import { mockCases, initialCellsData } from "./data/mockData";
import { Header } from "./components/Header";
import { CellDetailModal } from "./components/CellDetailModal";
import { NotesDrawer } from "./components/NotesDrawer";
import { ExportModal } from "./components/ExportModal";
import { StandaloneHtmlModal } from "./components/StandaloneHtmlModal";

export function AnalisisFrotis2Page() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentTab =
    workflowRoutes.find((route) => location.pathname.endsWith("/" + route.path))
      ?.tab ?? "REVIEW CELLS";
  const setCurrentTab = (tab: WorkflowTab) =>
    navigate(
      `${frotis2Base}/${workflowRoutes.find((route) => route.tab === tab)!.path}${location.search}`,
    );
  const {
    layoutMode,
    setLayoutMode,
    activeCase,
    setActiveCase,
    cells,
    setCells,
    selectedCategory,
    setSelectedCategory,
    selectedCellId,
    setSelectedCellId,
    inspectedCell,
    setInspectedCell,
    isNotesOpen,
    setIsNotesOpen,
    isExportOpen,
    setIsExportOpen,
    isStandaloneHtmlOpen,
    setIsStandaloneHtmlOpen,
    imageAdjustments,
    setImageAdjustments,
    handleReclassify,
    handleToggleFlag,
    availableCategoryNames,
    activeCategoryStats,
  } = useFrotisDemo();

  return (
    <div className="af2 frotis-v2 flex flex-col overflow-hidden bg-frotis-surface-subtle font-sans">
      <Outlet />
      {/* Top Header Bar */}
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        layoutMode={layoutMode}
        onLayoutModeChange={setLayoutMode}
        activeCase={activeCase}
        availableCases={mockCases}
        onSelectCase={(c) => {
          setActiveCase(structuredClone(c));
          setCells(structuredClone(initialCellsData));
          setSelectedCellId(null);
          setInspectedCell(null);
          if (c.categories.length > 0) {
            setSelectedCategory(c.categories[0].name);
          }
        }}
        imageAdjustments={imageAdjustments}
        onChangeAdjustments={setImageAdjustments}
        onOpenExport={() => setIsExportOpen(true)}
        onOpenStandaloneHtml={() => setIsStandaloneHtmlOpen(true)}
        onStatusChange={(status: CaseStatus) =>
          setActiveCase({ ...activeCase, status })
        }
      />

      {/* Main Content Area based on active workflow tab */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* TAB 1: REVIEW CELLS (The Primary Visor Interface) */}
        {currentTab === "REVIEW CELLS" && (
          <ReviewCellsPage
            layoutMode={layoutMode}
            sidebar={{
              categories: activeCase.categories,
              additionalCategories: activeCase.additionalCategories,
              totalNucleatedCount: activeCase.totalNucleatedCells,
              selectedCategory: selectedCategory,
              onSelectCategory: setSelectedCategory,
              onOpenNotes: () => setIsNotesOpen(true),
            }}
            gallery={{
              selectedCategory: selectedCategory,
              categoryStats: activeCategoryStats,
              cells: cells.filter((c) => c.category === selectedCategory),
              selectedCellId: selectedCellId,
              onSelectCell: (cell) => setSelectedCellId(cell.id),
              onInspectCell: (cell) => setInspectedCell(cell),
              onReclassifyCell: handleReclassify,
              availableCategories: availableCategoryNames,
            }}
            viewer={{
              cells: cells,
              selectedCellId: selectedCellId,
              onSelectCell: (cell) => {
                setSelectedCellId(cell.id);
                setSelectedCategory(cell.category);
              },
              imageAdjustments: imageAdjustments,
              onChangeAdjustments: setImageAdjustments,
              createdDate: activeCase.createdDate,
              scanSizeCm2: activeCase.scanSizeCm2,
            }}
          />
        )}

        {/* TAB 2: FULL FIELD REVIEW */}
        {currentTab === "FULL FIELD REVIEW" && (
          <FullFieldReviewPage
            activeCase={activeCase}
            cells={cells}
            selectedCellId={selectedCellId}
            onSelectCell={(cell) => setSelectedCellId(cell.id)}
            imageAdjustments={imageAdjustments}
            onChangeAdjustments={setImageAdjustments}
            isAnalysisArea={false}
          />
        )}

        {/* TAB 3: SPECIMEN QUALITY */}
        {currentTab === "SPECIMEN QUALITY" && (
          <SpecimenQualityPage activeCase={activeCase} />
        )}

        {/* TAB 4: ANALYSIS AREA */}
        {currentTab === "ANALYSIS AREA" && (
          <AnalysisAreaPage
            activeCase={activeCase}
            cells={cells}
            selectedCellId={selectedCellId}
            onSelectCell={(cell) => setSelectedCellId(cell.id)}
            imageAdjustments={imageAdjustments}
            onChangeAdjustments={setImageAdjustments}
            isAnalysisArea={true}
          />
        )}

        {/* TAB 5: PATHOLOGY DIAGNOSTIC REPORT */}
        {currentTab === "REPORT" && (
          <ReportPage
            activeCase={activeCase}
            onSignReport={() =>
              setActiveCase({ ...activeCase, status: "Signed-off" })
            }
          />
        )}
      </main>

      {/* Cell Detail Modal (High-Magnification 100x Morphology) */}
      {inspectedCell && (
        <CellDetailModal
          cell={inspectedCell}
          onClose={() => setInspectedCell(null)}
          onPrevious={() => {
            const visible = cells.filter(
              (c) => c.category === selectedCategory,
            );
            const currIdx = visible.findIndex((c) => c.id === inspectedCell.id);
            if (currIdx > 0) setInspectedCell(visible[currIdx - 1]);
          }}
          onNext={() => {
            const visible = cells.filter(
              (c) => c.category === selectedCategory,
            );
            const currIdx = visible.findIndex((c) => c.id === inspectedCell.id);
            if (currIdx < visible.length - 1)
              setInspectedCell(visible[currIdx + 1]);
          }}
          onReclassify={(newCat) => handleReclassify(inspectedCell.id, newCat)}
          onToggleFlag={() => handleToggleFlag(inspectedCell.id)}
          availableCategories={availableCategoryNames}
        />
      )}

      {/* Clinical Notes Drawer */}
      <NotesDrawer
        key={activeCase.id}
        isOpen={isNotesOpen}
        onClose={() => setIsNotesOpen(false)}
        caseId={activeCase.id}
      />

      {/* Export Modal */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        activeCase={activeCase}
        onOpenStandaloneHtml={() => setIsStandaloneHtmlOpen(true)}
      />

      {/* Standalone HTML Single-File Delivery Modal */}
      <StandaloneHtmlModal
        isOpen={isStandaloneHtmlOpen}
        onClose={() => setIsStandaloneHtmlOpen(false)}
      />
    </div>
  );
}
