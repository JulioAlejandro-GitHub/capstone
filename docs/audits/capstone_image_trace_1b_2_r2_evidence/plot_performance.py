"""Standalone figure of every pair, including failures and negative ratios."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
data={stage:json.loads((ROOT/(stage+'_performance.json')).read_text()) for stage in ['reproduction','final']}
fig,axes=plt.subplots(3,2,figsize=(11,9),sharex=True,constrained_layout=True)
for row,arch in enumerate(['custom_cnn','vgg16','densenet121']):
    for col,(metric,label) in enumerate([('full_p95_percent','p95 global'),('warm_p95_percent','p95 tras calentamiento R1')]):
        ax=axes[row,col]
        for stage,name,color,marker in [('reproduction','R1 reproducido','#596579','o'),('final','Candidato R2','#075b9a','s')]:
            pairs=data[stage][arch]['pairs']
            ax.plot([p['pair'] for p in pairs],[p[metric] for p in pairs],label=name,color=color,marker=marker)
        ax.axhline(10,color='#b42222',linestyle='--',label='Límite 10%')
        ax.axhline(0,color='#999999',linewidth=.6)
        ax.set_title(arch+' · '+label)
        ax.set_ylabel('Overhead (%)')
        ax.set_xticks(range(1,6));ax.grid(alpha=.2)
        if row==2:ax.set_xlabel('Par independiente (AB, BA, AB, BA, AB)')
axes[0,0].legend(fontsize=8)
fig.suptitle('TRACE.1B.2-R2 · Todos los pares, sin excluir resultados\nLos valores negativos no prueban aceleración',fontsize=13)
for suffix in ['svg','png']:
    path=ROOT/f'performance_pairs.{suffix}'
    if path.exists():raise RuntimeError('REFUSE_OVERWRITE')
    fig.savefig(path,dpi=160)
plt.close(fig)
