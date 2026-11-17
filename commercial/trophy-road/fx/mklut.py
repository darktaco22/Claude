import sys,time
from spectral_film_lut import film_loader as fl
from spectral_film_lut.utils import create_lut
import inspect
print(inspect.signature(fl.load_filmstocks))
t=time.time(); st=fl.load_filmstocks(lambda *a,**k:None,0.18); print(len(st),time.time()-t)
ks=[k for k in st if '5219' in k or '2383' in k or 'Eterna' in k or '5207' in k]; print(ks)
neg=st[[k for k in ks if '5219' in k][0]]; pr=st[[k for k in ks if '2383' in k][0]]
lut=create_lut(neg,pr,lut_size=33,name='/root/road/fx/cine_srgb',cube=True,verbose=False,filter_mode=None,input_colorspace='sRGB')
print('ok',time.time()-t)
