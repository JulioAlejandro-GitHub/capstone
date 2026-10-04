"""Retrieve public documentation into audit evidence only; never downloads datasets."""
import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

OUT=Path('docs/audits/s1_1')
BASE='https://data.lhncbc.nlm.nih.gov/public/Malaria/'
URLS={
 'nlm_datasheet.html':'https://lhncbc.nlm.nih.gov/LHC-research/LHC-projects/image-processing/malaria-datasheet.html',
 'official_ReadMe.pdf':BASE+'NIH-NLM-ThinBloodSmearsPf/ReadMe.pdf',
 'official_Dataset_statistics.xlsx':BASE+'NIH-NLM-ThinBloodSmearsPf/Dataset_statistics.xlsx',
 'official_polygon_index.html':BASE+'NIH-NLM-ThinBloodSmearsPf/Polygon%20Set/index.html',
 'official_point_index.html':BASE+'NIH-NLM-ThinBloodSmearsPf/Point%20Set/index.html',
 'official_parasitized.csv':BASE+'patientid_cellmapping_parasitized.csv',
 'official_uninfected.csv':BASE+'patientid_cellmapping_uninfected.csv',
}

def main() -> None:
    metadata={}
    for name,url in URLS.items():
        with urllib.request.urlopen(url,timeout=45) as response:
            data=response.read()
        (OUT/name).write_bytes(data)
        metadata[name]={'url':url,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (OUT/'remote_sources.json').write_text(json.dumps(metadata,indent=2))

if __name__=='__main__':main()
