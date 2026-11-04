import React, { useState } from "react";
import { X, Send, MessageSquare, Clock, User } from "lucide-react";

interface NoteItem {
  id: string;
  author: string;
  timestamp: string;
  text: string;
}

interface NotesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
}

export const NotesDrawer: React.FC<NotesDrawerProps> = ({
  isOpen,
  onClose,
  caseId,
}) => {
  const [notes, setNotes] = useState<NoteItem[]>([
    {
      id: "1",
      author: "Dr. Julián Morales (Patología)",
      timestamp: "04/05/2023 14:02",
      text: "Se aprecian promyelocitos hipergranulares atípicos con frecuentes cuerpos de Auer en haz (faggot cells). Altamente sugestivo de LPA (LMA M3). Se da aviso telefónico urgente a hematología de guardia.",
    },
  ]);
  const [inputNote, setInputNote] = useState("");

  if (!isOpen) return null;

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputNote.trim()) return;

    const newNote: NoteItem = {
      id: Date.now().toString(),
      author: "Especialista en Guardia",
      timestamp: new Date().toLocaleString(),
      text: inputNote.trim(),
    };

    setNotes([...notes, newNote]);
    setInputNote("");
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs select-none animate-in fade-in">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col justify-between border-l border-slate-200">
        {/* Header */}
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800">
            <MessageSquare className="w-4 h-4 text-indigo-600" />
            <h3 className="font-bold text-sm">Comentarios Clínicos y Notas</h3>
          </div>
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-800 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Notes List */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 custom-scrollbar text-xs">
          {notes.map((note) => (
            <div
              key={note.id}
              className="bg-slate-50 border border-slate-200 rounded-md p-3 space-y-1.5"
            >
              <div className="flex items-center justify-between text-slate-500 text-[11px]">
                <span className="font-semibold text-slate-700 flex items-center gap-1">
                  <User className="w-3 h-3" /> {note.author}
                </span>
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="w-3 h-3" /> {note.timestamp}
                </span>
              </div>
              <p className="text-slate-800 leading-relaxed font-normal">
                {note.text}
              </p>
            </div>
          ))}
        </div>

        {/* Input box */}
        <form
          onSubmit={handleAddNote}
          className="p-3 border-t border-slate-200 bg-slate-50 flex gap-2"
        >
          <input
            type="text"
            placeholder="Añadir comentario clínico o hallazgo..."
            value={inputNote}
            onChange={(e) => setInputNote(e.target.value)}
            className="flex-1 px-3 py-2 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20"
          />
          <button
            type="submit"
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-medium flex items-center gap-1 transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
