"""Read-only links to prior R1 science and repeated A arms; no new inference."""
import json
from campaign import HERE,R1,compare

for arch in ['custom_cnn','vgg16','densenet121']:
    cases=[('historical',R1/f'{arch}_aa1',HERE/f'reproduction_{arch}_perf_0_a'),
           ('reproduction_aa',HERE/f'reproduction_{arch}_perf_0_a',HERE/f'reproduction_{arch}_perf_1_a'),
           ('candidate_baseline',HERE/f'reproduction_{arch}_perf_0_a',HERE/f'{arch}_aa1')]
    for label,left,right in cases:
        result=compare(left,right)
        with (HERE/f'{label}_{arch}_science.json').open('x') as stream:json.dump(result,stream,indent=2)
        print(label,arch,result['passed'],result['failed'],flush=True)
        assert result['passed']
