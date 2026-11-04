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
    <aside className="w-64 sm:w-72 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col h-full text-slate-800 text-xs overflow-hidden select-none">
      {/* Search Input for fast differential filtering */}
      <div className="p-2 border-b border-slate-100 bg-slate-50/70">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2 top-2 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar célula o tipo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-7 pr-2 py-1 text-xs bg-white border border-slate-200 rounded-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
          />
        </div>
      </div>

      {/* Scrollable Differential Tables */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 custom-scrollbar">
        {/* Main Differential Section */}
        <div className="pb-2">
          {/* Section Header */}
          <div className="px-3 py-2 font-semibold text-slate-700 bg-slate-50/90 flex items-center justify-between border-b border-slate-200/60 sticky top-0 z-10">
            <span>Nucleated - differential - {totalNucleatedCount}</span>
          </div>

          {/* Table Header */}
          <div className="grid grid-cols-12 px-3 py-1.5 text-[11px] font-medium text-slate-400 border-b border-slate-100 uppercase tracking-wider">
            <div className="col-span-6">Name</div>
            <div className="col-span-3 text-right">Count</div>
            <div className="col-span-2 text-right">%</div>
            <div className="col-span-1 text-center">Seen</div>
          </div>

          {/* Rows */}
          <div className="divide-y divide-slate-50">
            {filteredCategories.map((cat) => {
              const isSelected = selectedCategory === cat.name;
              return (
                <div
                  key={cat.name}
                  onClick={() => onSelectCategory(cat.name)}
                  className={`grid grid-cols-12 px-3 py-1.5 items-center cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-indigo-50 text-indigo-900 font-semibold"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="col-span-6 truncate font-normal">
                    {cat.name}
                  </div>
                  <div className="col-span-3 text-right font-mono font-medium">
                    {cat.count}
                  </div>
                  <div className="col-span-2 text-right font-mono text-slate-600">
                    {cat.percentage > 0 ? `${cat.percentage}%` : "0%"}
                  </div>
                  <div className="col-span-1 flex justify-center text-emerald-600">
                    {cat.seen && <Check className="w-3.5 h-3.5 stroke-[2.5]" />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Additional Cells Section */}
        <div className="pt-1 pb-4">
          <div className="px-3 py-1.5 font-semibold text-slate-700 bg-slate-50/90 flex items-center justify-between border-y border-slate-200/60 sticky top-0 z-10">
            <span>Additional cells - 26</span>
          </div>

          <div className="grid grid-cols-12 px-3 py-1 text-[11px] font-medium text-slate-400 border-b border-slate-100 uppercase tracking-wider">
            <div className="col-span-8">Name</div>
            <div className="col-span-3 text-right">Count</div>
            <div className="col-span-1 text-center">Seen</div>
          </div>

          <div className="divide-y divide-slate-50">
            {filteredAdditional.map((cat) => {
              const isSelected = selectedCategory === cat.name;
              return (
                <div
                  key={cat.name}
                  onClick={() => onSelectCategory(cat.name)}
                  className={`grid grid-cols-12 px-3 py-1.5 items-center cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-indigo-50 text-indigo-900 font-semibold"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="col-span-8 truncate font-normal">
                    {cat.name}
                  </div>
                  <div className="col-span-3 text-right font-mono font-medium">
                    {cat.count}
                  </div>
                  <div className="col-span-1 flex justify-center text-emerald-600">
                    {cat.seen && <Check className="w-3.5 h-3.5 stroke-[2.5]" />}
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
        className="h-10 px-3 bg-slate-50 border-t border-slate-200 hover:bg-slate-100 text-slate-600 flex items-center justify-between text-xs font-medium transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
          <span>Click here to add comment</span>
        </div>
        {notesCount > 0 && (
          <span className="w-4 h-4 rounded-full bg-indigo-100 text-indigo-700 text-[10px] font-bold flex items-center justify-center">
            {notesCount}
          </span>
        )}
      </button>
    </aside>
  );
};
