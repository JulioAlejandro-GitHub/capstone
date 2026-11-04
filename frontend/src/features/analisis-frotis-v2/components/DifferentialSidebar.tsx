import React, { useState } from "react";
import { DifferentialCategory } from "../types/visor";
import { Check, MessageSquare, Search, PlusCircle } from "lucide-react";

interface DifferentialSidebarProps {
  categories: DifferentialCategory[];
  additionalCategories: DifferentialCategory[];
  totalNucleatedCount: number;
  selectedCategory: string;
  onSelectCategory: (name: string) => void;
  onOpenNotes: () => void;
  notesCount?: number;
}

export const DifferentialSidebar: React.FC<DifferentialSidebarProps> = ({
  categories,
  additionalCategories,
  totalNucleatedCount,
  selectedCategory,
  onSelectCategory,
  onOpenNotes,
  notesCount = 1,
}) => {
  const [search, setSearch] = useState("");

  const filterRow = (cat: DifferentialCategory) => {
    if (!search.trim()) return true;
    return cat.name.toLowerCase().includes(search.toLowerCase());
  };

  const filteredCategories = categories.filter(filterRow);
  const filteredAdditional = additionalCategories.filter(filterRow);

  return (
    <aside className="w-frotis-sidebar-width-compact sm:w-frotis-sidebar-width flex-shrink-0 bg-frotis-surface border-r border-frotis-border flex flex-col h-full text-frotis-text-heading text-xs overflow-hidden select-none">
      {/* Search Input for fast differential filtering */}
      <div className="p-2 border-b border-frotis-surface-subtle bg-frotis-surface-muted/70">
        <div className="relative">
          <Search className="w-frotis-icon-size-sm h-frotis-icon-size-sm absolute left-2 top-2 text-frotis-text-muted" />
          <input
            type="text"
            placeholder="Buscar célula o tipo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-7 pr-2 py-1 text-xs bg-frotis-surface border-frotis border-frotis-border rounded-sm focus:outline-none focus:border-frotis-accent focus:ring-1 focus:ring-frotis-accent/30"
          />
        </div>
      </div>

      {/* Scrollable Differential Tables */}
      <div className="flex-1 overflow-y-auto divide-y divide-frotis-surface-subtle custom-scrollbar">
        {/* Main Differential Section */}
        <div className="pb-2">
          {/* Section Header */}
          <div className="px-3 py-2 font-semibold text-frotis-text-body bg-frotis-surface-muted/90 flex items-center justify-between border-b border-frotis-border/60 sticky top-0 frotis-layer-overlay">
            <span>Nucleated - differential - {totalNucleatedCount}</span>
          </div>

          {/* Table Header */}
          <div className="grid grid-cols-12 px-3 py-1.5 text-frotis-label font-medium text-frotis-text-muted border-b border-frotis-surface-subtle uppercase tracking-wider">
            <div className="col-span-6">Name</div>
            <div className="col-span-3 text-right">Count</div>
            <div className="col-span-2 text-right">%</div>
            <div className="col-span-1 text-center">Seen</div>
          </div>

          {/* Rows */}
          <div className="divide-y divide-frotis-surface-muted">
            {filteredCategories.map((cat) => {
              const isSelected = selectedCategory === cat.name;
              return (
                <div
                  key={cat.name}
                  onClick={() => onSelectCategory(cat.name)}
                  className={`grid grid-cols-12 px-3 py-1.5 items-center cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-frotis-selected text-frotis-secondary-dark font-semibold"
                      : "hover:bg-frotis-surface-muted text-frotis-text-body"
                  }`}
                >
                  <div className="col-span-6 truncate font-normal">
                    {cat.name}
                  </div>
                  <div className="col-span-3 text-right font-mono font-medium">
                    {cat.count}
                  </div>
                  <div className="col-span-2 text-right font-mono text-frotis-text-control">
                    {cat.percentage > 0 ? `${cat.percentage}%` : "0%"}
                  </div>
                  <div className="col-span-1 flex justify-center text-frotis-success">
                    {cat.seen && <Check className="w-frotis-icon-size-sm h-frotis-icon-size-sm stroke-[2.5]" />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Additional Cells Section */}
        <div className="pt-1 pb-4">
          <div className="px-3 py-1.5 font-semibold text-frotis-text-body bg-frotis-surface-muted/90 flex items-center justify-between border-y border-frotis-border/60 sticky top-0 frotis-layer-overlay">
            <span>Additional cells - 26</span>
          </div>

          <div className="grid grid-cols-12 px-3 py-1 text-frotis-label font-medium text-frotis-text-muted border-b border-frotis-surface-subtle uppercase tracking-wider">
            <div className="col-span-8">Name</div>
            <div className="col-span-3 text-right">Count</div>
            <div className="col-span-1 text-center">Seen</div>
          </div>

          <div className="divide-y divide-frotis-surface-muted">
            {filteredAdditional.map((cat) => {
              const isSelected = selectedCategory === cat.name;
              return (
                <div
                  key={cat.name}
                  onClick={() => onSelectCategory(cat.name)}
                  className={`grid grid-cols-12 px-3 py-1.5 items-center cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-frotis-selected text-frotis-secondary-dark font-semibold"
                      : "hover:bg-frotis-surface-muted text-frotis-text-body"
                  }`}
                >
                  <div className="col-span-8 truncate font-normal">
                    {cat.name}
                  </div>
                  <div className="col-span-3 text-right font-mono font-medium">
                    {cat.count}
                  </div>
                  <div className="col-span-1 flex justify-center text-frotis-success">
                    {cat.seen && <Check className="w-frotis-icon-size-sm h-frotis-icon-size-sm stroke-[2.5]" />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Notes / Comments bar */}
      <button
        onClick={onOpenNotes}
        className="h-10 px-3 bg-frotis-surface-muted border-t border-frotis-border hover:bg-frotis-hover text-frotis-text-control flex items-center justify-between text-xs font-medium transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <MessageSquare className="w-frotis-icon-size-sm h-frotis-icon-size-sm text-frotis-text-muted" />
          <span>Click here to add comment</span>
        </div>
        {notesCount > 0 && (
          <span className="w-frotis-icon-size h-frotis-icon-size rounded-full bg-frotis-selected-hover text-frotis-secondary-hover text-frotis-caption font-bold flex items-center justify-center">
            {notesCount}
          </span>
        )}
      </button>
    </aside>
  );
};
