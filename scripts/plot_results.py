"""Standard reportlab chart of measured synthetic fixture metrics; no invented results."""
import json
from pathlib import Path
from reportlab.graphics.shapes import Drawing,String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderSVG
p=Path(__file__).resolve().parents[1]/'experiments/run-001'
rows=json.loads((p/'summary.json').read_text())[:4]
d=Drawing(640,330)
d.add(String(30,306,'Synthetic fixture check: evidence recall / conflict F1',fontSize=16))
d.add(String(30,286,'Small authored corpus; no claim of scientific superiority',fontSize=10))
chart=VerticalBarChart();chart.x=65;chart.y=55;chart.width=530;chart.height=205
chart.data=[[r['evidence_recall'] or 0 for r in rows],[r['conflict_f1'] or 0 for r in rows]]
chart.categoryAxis.categoryNames=[r['strategy'] for r in rows]
chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=1;chart.valueAxis.valueStep=.2
from reportlab.lib.colors import HexColor
chart.bars[0].fillColor=HexColor('#176654');chart.bars[1].fillColor=HexColor('#bd841f')
d.add(chart);d.add(String(65,16,'Green: evidence recall. Amber: literal conflict-signal F1. No generation.',fontSize=10))
renderSVG.drawToFile(d,str(p/'quality.svg'))
print(p/'quality.svg')
