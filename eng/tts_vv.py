"""VOICEVOX TTS for an episode: hana/narr (and robo placeholder unless --skip-robo).
Smooth reading: spaces between words are removed (they made VOICEVOX pause) and the remaining pauses are shortened."""
import sys, os, json, glob, argparse
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
ap = argparse.ArgumentParser(); ap.add_argument('ep'); ap.add_argument('out'); ap.add_argument('--vv', default='/home/claude/vv'); ap.add_argument('--skip-robo', action='store_true')
g = ap.parse_args(); os.makedirs(g.out, exist_ok=True)
ort = Onnxruntime.load_once(filename=glob.glob(g.vv+'/voicevox_onnxruntime*/lib/libvoicevox_onnxruntime.so*')[0])
s = Synthesizer(ort, OpenJtalk(glob.glob(g.vv+'/open_jtalk_dic*')[0]), cpu_num_threads=2)
for f in ['0.vvm', '6.vvm', '9.vvm']:
    with VoiceModelFile.open(os.path.join(g.vv, f)) as m: s.load_voice_model(m)
# who: (speaker id, speed, pitch, intonation, pause factor)
VOICE = {'hana': (10, 1.05, 0.02, 1.2, 0.7), 'narr': (31, 1.1, 0.0, 1.15, 0.6), 'robo': (32, 1.1, 0.04, 1.3, 0.8)}
ep = json.load(open(g.ep))
for i, b in enumerate(ep['beats']):
    sp = b.get('say')
    if not sp or (sp['who'] == 'robo' and g.skip_robo): continue
    sid, spd, pit, inton, pf = VOICE[sp['who']]
    text = sp['text'].replace(' ', '').replace('　', '')
    q = s.create_audio_query(text, sid); q.speed_scale = spd; q.pitch_scale = pit; q.intonation_scale = inton
    q.output_sampling_rate = 48000; q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.1
    for a in q.accent_phrases:
        pm = a.pause_mora
        if pm is None: continue
        if isinstance(pm, dict): pm['vowel_length'] *= pf
        else: pm.vowel_length *= pf
    open(f'{g.out}/{i:02d}.wav', 'wb').write(s.synthesis(q, sid))
print('tts ok')
