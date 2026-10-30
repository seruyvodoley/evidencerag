"""Render the code-native bracket/A brand mark as browser icons; no external assets."""
from pathlib import Path
from PIL import Image, ImageDraw

out=Path(__file__).resolve().parents[1]/'apps/web/public'
out.mkdir(parents=True,exist_ok=True)
svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36"><rect width="36" height="36" rx="7" fill="#176654"/><g fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"><path d="M12 7H6v22h6M24 7h6v22h-6M12 25l6-14 6 14M14 21h8"/></g></svg>'''
(out/'favicon.svg').write_text(svg)
scale=24
image=Image.new('RGBA',(36*scale,36*scale),(0,0,0,0));draw=ImageDraw.Draw(image)
draw.rounded_rectangle((0,0,36*scale-1,36*scale-1),radius=7*scale,fill='#176654')
for points in [[(12,7),(6,7),(6,29),(12,29)],[(24,7),(30,7),(30,29),(24,29)],[(12,25),(18,11),(24,25)],[(14,21),(22,21)]]:
 draw.line([(x*scale,y*scale) for x,y in points],fill='white',width=round(2.2*scale),joint='curve')
for size,name in [(16,'favicon-16.png'),(32,'favicon-32.png'),(180,'apple-touch-icon.png')]:
 image.resize((size,size),Image.Resampling.LANCZOS).save(out/name)
image.resize((256,256),Image.Resampling.LANCZOS).save(out/'favicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48)])
print('Brand icons saved in apps/web/public')
