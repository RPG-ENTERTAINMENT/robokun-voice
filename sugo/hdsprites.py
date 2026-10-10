"""キャラ絵をAI(Real-ESRGAN anime6B)で4倍高画質化: python hdsprites.py 入力dir 出力dir 重み.pth"""
import torch, torch.nn as nn, torch.nn.functional as F, numpy as np, cv2, glob, os, sys
from PIL import Image
class RDB(nn.Module):
    def __init__(s,nf=64,gc=32):
        super().__init__()
        s.conv1=nn.Conv2d(nf,gc,3,1,1);s.conv2=nn.Conv2d(nf+gc,gc,3,1,1);s.conv3=nn.Conv2d(nf+2*gc,gc,3,1,1)
        s.conv4=nn.Conv2d(nf+3*gc,gc,3,1,1);s.conv5=nn.Conv2d(nf+4*gc,nf,3,1,1);s.lrelu=nn.LeakyReLU(0.2,True)
    def forward(s,x):
        x1=s.lrelu(s.conv1(x));x2=s.lrelu(s.conv2(torch.cat((x,x1),1)));x3=s.lrelu(s.conv3(torch.cat((x,x1,x2),1)))
        x4=s.lrelu(s.conv4(torch.cat((x,x1,x2,x3),1)));x5=s.conv5(torch.cat((x,x1,x2,x3,x4),1));return x5*0.2+x
class RRDB(nn.Module):
    def __init__(s,nf,gc=32):
        super().__init__();s.rdb1=RDB(nf,gc);s.rdb2=RDB(nf,gc);s.rdb3=RDB(nf,gc)
    def forward(s,x): return s.rdb3(s.rdb2(s.rdb1(x)))*0.2+x
class Net(nn.Module):
    def __init__(s,nf=64,nb=6,gc=32):
        super().__init__()
        s.conv_first=nn.Conv2d(3,nf,3,1,1);s.body=nn.Sequential(*[RRDB(nf,gc) for _ in range(nb)]);s.conv_body=nn.Conv2d(nf,nf,3,1,1)
        s.conv_up1=nn.Conv2d(nf,nf,3,1,1);s.conv_up2=nn.Conv2d(nf,nf,3,1,1);s.conv_hr=nn.Conv2d(nf,nf,3,1,1);s.conv_last=nn.Conv2d(nf,3,3,1,1);s.lrelu=nn.LeakyReLU(0.2,True)
    def forward(s,x):
        f=s.conv_first(x);f=f+s.conv_body(s.body(f))
        f=s.lrelu(s.conv_up1(F.interpolate(f,scale_factor=2,mode='nearest')));f=s.lrelu(s.conv_up2(F.interpolate(f,scale_factor=2,mode='nearest')))
        return s.conv_last(s.lrelu(s.conv_hr(f)))
IN=sys.argv[1];OUT=sys.argv[2];WT=sys.argv[3]
torch.set_num_threads(os.cpu_count() or 2)
net=Net();sd=torch.load(WT,map_location='cpu');net.load_state_dict(sd.get('params_ema',sd.get('params',sd)),strict=True);net.eval()
def sr(a):  # a: HxWx3 uint8
    t=torch.from_numpy(a[:,:,::-1].copy()).permute(2,0,1).float().div(255)[None]
    with torch.no_grad(): o=net(t)
    return (o[0].clamp(0,1).permute(1,2,0).numpy()*255).round().astype(np.uint8)[:,:,::-1]
os.makedirs(OUT,exist_ok=True)
for f in sorted(glob.glob(IN+'/*.webp')):
    n=os.path.basename(f)[:-5]
    im=np.array(Image.open(f).convert('RGBA'));P=6
    im=np.pad(im,((P,P),(P,P),(0,0)),mode='edge'); im[:P,:,3]=0;im[-P:,:,3]=0;im[:,:P,3]=0;im[:,-P:,3]=0
    rgb=im[:,:,:3].copy();a=im[:,:,3]
    rgb=cv2.inpaint(rgb,(a<8).astype(np.uint8)*255,3,cv2.INPAINT_TELEA)
    big=sr(rgb);ab=sr(np.dstack([a]*3))[:,:,0]
    o=Image.fromarray(np.dstack([big,ab]),'RGBA').crop((P*4,P*4,(im.shape[1]-P)*4,(im.shape[0]-P)*4))
    o.save(f'{OUT}/{n}.webp',quality=92,method=6);print(n,o.size,flush=True)
