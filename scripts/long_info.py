"""Print length and chapter cards of a landscape episode as JSON (run in its own process to keep memory low)."""
import sys, os, json
sys.path.insert(0, 'eng'); os.environ['ROBO_ASPECT'] = '16x9'
from engine_l import Ep
s = Ep(json.load(open(sys.argv[1])), sys.argv[2])
print(json.dumps({'T': s.T, 'cards': s.cards}, ensure_ascii=False))
