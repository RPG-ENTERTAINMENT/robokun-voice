import json, subprocess, glob, os
src = [f for f in glob.glob('*.m4a')][0]
os.makedirs('data', exist_ok=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',src,'-ac','1','-ar','48000','data/rec.wav'],check=True)
S = json.load(open('scripts/segs.json'))
L = []
for i,(a,b,t) in enumerate(S):
    f = f'data/{i+1:02d}.wav'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(a),'-to',str(b),'-i','data/rec.wav','-af','highpass=f=70,afftdn=nf=-40,loudnorm=I=-20:TP=-2','-ar','32000','-ac','1',f],check=True)
    L.append(f'{os.path.abspath(f)}|robokun|ja|{t}')
open('data/list.txt','w').write('\n'.join(L)+'\n')
print('prepared', len(L))
