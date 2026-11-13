"""Generate browser metadata from the published reconstruction repository.

Usage: python tools/make_data.py /path/to/UASpeech-data-cleaning
Only public metadata and an already-authorized figure are used. No media decoding.
"""
import csv
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

repo = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={repo}', '-C', str(repo), *args], text=True)
def table(name):
    with (repo/'metadata'/name).open() as f:
        return list(csv.DictReader(f, delimiter='\t' if name.endswith('.tsv') else ','))
archive = 'archive/detailed-2026-11-13'
availability = {r['speaker']: r for r in csv.DictReader(io.StringIO(git('show', f'{archive}:metadata/speaker_availability.csv')))}
audit = list(csv.DictReader(io.StringIO(git('show', f'{archive}:metadata/legacy_audit.csv'))))
total = Counter(r['speaker'] for r in audit)
affected = Counter(r['speaker'] for r in audit if r['confirmed_affected']=='1')
frames = table('frame_index.tsv')
assert len(frames)==8415 and len({r['utterance_id'] for r in frames})==8415
assert len(audit)==6246 and sum(affected.values())==1246
groups = [('Very low',['M04','F03','M12','M01']),('Low',['M07','F02','M16']),
          ('Medium',['M05','F04','M11']),('High',['M09','M14','M08','M10','F05'])]
notes = {
 'F02': ('B2 video assignments shifted one word later. All B3 indices and one B2 index were missing.', 'Recovered missing indices and realigned word intervals.'),
 'F04': ('B3 video assignments shifted one word later; one B3 index was missing.', 'Realigned word intervals and recovered the missing index.'),
 'M07': ('Audio labels and video recording blocks were mismatched. The predominant mapping is B1 → B3, B2 → B1, B3 → B2, with exceptions.', 'Assigned the actual source video per utterance; retained per-word frame boundaries.'),
 'M12': ('All B3 indices and three B2 indices were missing; one issue was confirmed in the older audited subset.', 'Recovered indices and repaired the affected sample.'),
 'M11': ('84 B3 indices were missing. The older audit and later supplemental interval review cover different samples.', 'Recovered indices and reviewed supplemental boundaries.'),
 'M10': ('The actual B2 recording was missing; the B2-labeled file duplicated B3 content.', 'Not included in the reconstructed eleven-speaker set.'),
}
speakers=[]
for severity, ids in groups:
    for sid in ids:
        row=availability[sid]
        video=row['local_divx_available']=='1'
        indexed=int(row['legacy_frame_index_rows'])
        final=int(row['reconstructed_records'])
        issue, repair=notes.get(sid, (
            ('All three blocks lacked word-level video indices.' if sid in {'M05','M09'} else
             'No source video in the examined files.' if not video else f'{affected[sid]} isolated sample issues.'),
            ('Reconstructed all 765 word-level indices.' if sid in {'M05','M09'} else
             'Not included in the audiovisual set.' if not video else 'Reviewed and repaired the affected samples.')))
        speakers.append(dict(id=sid,severity=severity,video=video,indices=indexed,final=final,
                             audited=total[sid],affected=affected[sid],issue=issue,repair=repair))
m07={}
for block in ['B1','B2','B3']:
    rows=[r for r in frames if r['speaker']=='M07' and r['block']==block]
    counts=Counter(r['source_key'] for r in rows)
    m07[block]=[dict(source=k,count=v,example=next(r['utterance_id'] for r in rows if r['source_key']==k))
                for k,v in sorted(counts.items(),key=lambda kv:-kv[1])]
data=dict(commit=git('rev-parse','HEAD').strip(),revision=json.loads((repo/'metadata/release.json').read_text())['revision'],
          archive=archive,speakers=speakers,m07=m07,
          samples=[[r['utterance_id'],r['text'],r['source_key'],int(r['begin_frame']),int(r['end_frame_exclusive'])] for r in frames],
          case=json.loads((repo/'examples/alignment_case.json').read_text()),
          source_sha256={n:hashlib.sha256((repo/'metadata'/n).read_bytes()).hexdigest()
                         for n in ['frame_index.tsv','manifest.csv','audio_actions.tsv','source_files.tsv']})
(root/'data.js').write_text('window.UASPEECH_DATA = '+json.dumps(data,ensure_ascii=True,separators=(',',':'))+';\n')
print(f'Exported {len(speakers)} speaker summaries and {len(frames)} sample records; no audio arrays.')
