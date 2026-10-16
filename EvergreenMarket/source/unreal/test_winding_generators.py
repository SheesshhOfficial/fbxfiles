"""Verify both procedural cube generators use outward face order."""
import ast
from pathlib import Path
import unittest

class CubeWindingTests(unittest.TestCase):
    def check_file(self,path):
        tree=ast.parse(path.read_text())
        candidates=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='faces' for t in node.targets):
                try: value=ast.literal_eval(node.value)
                except (ValueError,TypeError): continue
                if len(value)==6 and all(len(f)==4 for f in value): candidates.append(value)
        self.assertEqual(len(candidates),1)
        v=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        for face in candidates[0]:
            a,b,c=[v[i] for i in face[:3]]
            u=[b[i]-a[i] for i in range(3)];w=[c[i]-a[i] for i in range(3)]
            normal=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
            center=[sum(v[j][i] for j in face)/4 for i in range(3)]
            self.assertGreater(sum(a*b for a,b in zip(normal,center)),0)
    def test_render_boxes_outward(self):self.check_file(Path(__file__).resolve().parents[1]/'blender'/'build_supermarket.py')
    def test_collision_boxes_outward(self):self.check_file(Path(__file__).with_name('convert_supermarket.py'))

if __name__=='__main__':unittest.main()
