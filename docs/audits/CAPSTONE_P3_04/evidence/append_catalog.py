"""Append only curated central function fiches after regenerating the static catalog."""
from pathlib import Path
B=Path(__file__).resolve().parents[1]
def add(name,text):
 p=B/name;p.write_text(p.read_text()+'\n'+text.strip()+'\n')
s=(B/'evidence/finish_docs.py').read_text()
exec(s[s.index('curated=['):s.index('# Reproducibility README.')])
