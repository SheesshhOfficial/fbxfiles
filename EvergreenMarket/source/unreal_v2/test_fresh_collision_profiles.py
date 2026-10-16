"""Static regression for persistent Custom collision ordering; no Unreal runtime."""
import ast
import inspect
import unittest
from types import SimpleNamespace as NS
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep

class FreshProfileTests(unittest.TestCase):
    def test_custom_after_editor_flags_before_responses(self):
        for function in (em._new_ism, ec._spawn):
            with self.subTest(function=function.__module__):
                tree=ast.parse(inspect.getsource(function))
                calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
                custom=[n for n in calls if n.func.attr=='set_collision_profile_name']
                self.assertEqual(len(custom),1)
                self.assertEqual(custom[0].args[0].value,'Custom')
                line=custom[0].lineno
                self.assertTrue(all(n.lineno<line for n in calls if n.func.attr=='set_editor_property'))
                self.assertTrue(all(n.lineno>line for n in calls if n.func.attr in ('set_collision_enabled','set_collision_response_to_all_channels','set_collision_response_to_channel')))
                self.assertTrue(any(n.lineno<line and n.func.attr=='modify' for n in calls))
    def test_pilot_collision_applied_last(self):
        tree=ast.parse(inspect.getsource(ep._spawn))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        line=next(n.lineno for n in calls if isinstance(n.func,ast.Name) and n.func.id=='_apply_pilot_collision')
        self.assertTrue(all(n.lineno<line for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='set_editor_property'))
class MaterialPolicyTests(unittest.TestCase):
    def test_expected_modes_and_reject_translucency(self):
        u=NS(BlendMode=NS(BLEND_OPAQUE='opaque',BLEND_MASKED='masked',BLEND_TRANSLUCENT='blend'))
        for mode, value in [('OPAQUE','opaque'),('MASK','masked'),('BLEND','blend')]:
            mat=NS(get_editor_property=lambda key: value if key=='blend_mode' else False)
            em._verify_material_policy(u,mat,{'alpha_mode':mode})
        bad=NS(get_editor_property=lambda key:'blend' if key=='blend_mode' else False)
        with self.assertRaisesRegex(ValueError,'blend mode'):
            em._verify_material_policy(u,bad,{'alpha_mode':'OPAQUE'})
    def test_reject_blanket_two_sided(self):
        u=NS(BlendMode=NS(BLEND_OPAQUE='opaque',BLEND_MASKED='masked',BLEND_TRANSLUCENT='blend'))
        bad=NS(get_editor_property=lambda key:'opaque' if key=='blend_mode' else True)
        with self.assertRaisesRegex(ValueError,'two-sided'):
            em._verify_material_policy(u,bad,{'alpha_mode':'OPAQUE','two_sided':False})
if __name__=='__main__':unittest.main()
