"""Audit official workbook and cross-source name evidence, without identity merges."""
from __future__ import annotations
import csv,json,re,zipfile,xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
from inspect_images import candidate,write_csv

OUT=Path('docs/audits/s1_1')

def workbook_rows(path: Path) -> dict[str,list[list[str]]]:
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    result={}
    with zipfile.ZipFile(path) as z:
        strings=[''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
        for sheet,part in [('Polygon Set','sheet1.xml'),('Point Set','sheet2.xml')]:
            rows=[]
            for row in ET.fromstring(z.read('xl/worksheets/'+part)).findall('.//m:row',ns):
                cells=[]
                for c in row.findall('m:c',ns):
                    v=c.find('m:v',ns)
                    if v is not None:cells.append(strings[int(v.text)] if c.get('t')=='s' else v.text)
                if cells and '\\GT\\' in cells[0]: rows.append(cells)
            result[sheet]=rows
    return result

def main() -> None:
    cells=list(csv.DictReader((OUT/'image_comparison.csv').open()))
    names=defaultdict(set)
    for r in cells:
        names[r['patient_id']].add(r['filename'].split('_IMG_')[1].split('_cell_')[0])
    workbook=workbook_rows(OUT/'official_Dataset_statistics.xlsx')
    allrows=[];summary={}
    for sheet,rows in workbook.items():
        by_patient=defaultdict(list)
        for row in rows:by_patient[row[0].split('\\')[2]].append(row)
        summary[sheet]={'patients':len(by_patient),'images':len(rows),'images_per_patient':dict(Counter(map(len,by_patient.values()))),'WBC':sum(int(r[1]) for r in rows),'parasitized_RBC':sum(int(r[2]) for r in rows),'uninfected_RBC':sum(int(r[3]) for r in rows)}
        for pid,rr in sorted(by_patient.items()):
            cand=candidate(pid)
            stems={Path(r[0].split('\\')[-1].strip("'")).stem.removeprefix('IMG_') for r in rr}
            allrows.append({'set':sheet,'full_patient_id':pid,'numeric_prefix':re.match(r'\d+',pid).group(),'cell_candidate':cand,'candidate_present':cand in names,'images':len(rr),'source_image_stems_in_candidate_cells':len(stems & names[cand]),'image_stems':';'.join(sorted(stems)),'match_status':'UNRESOLVED'})
    write_csv('full_smear_candidates.csv',allrows)
    matrix=list(csv.DictReader((OUT/'polygon_cell_matrix.csv').open()))
    byid={r['full_patient_id']:r for r in allrows}
    for r in matrix:
        evidence=byid[r['polygon_patient_id']]
        r['evidence']=f"Official workbook directory suffix; {evidence['source_image_stems_in_candidate_cells']}/5 matching acquisition filename stems in official cell mapping. No documented cross-source mapping or image-content localization."
    write_csv('polygon_cell_matrix.csv',matrix)
    fullids={r['cell_candidate'] for r in allrows}
    summary['cell_identifiers_absent_from_full_smear'] = sorted(set(names)-fullids)
    summary['full_smear_candidates_absent_from_cell'] = sorted(fullids-set(names))
    summary['prefix_unique']=len({r['numeric_prefix'] for r in allrows})
    summary['prefix_range']=[min(int(r['numeric_prefix']) for r in allrows),max(int(r['numeric_prefix']) for r in allrows)]
    summary['prefix_semantics']='UNRESOLVED: unique directory index-like prefix; no official semantic definition found'
    summary['stem_overlap_distribution']=dict(Counter(r['source_image_stems_in_candidate_cells'] for r in allrows))
    (OUT/'smear_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
