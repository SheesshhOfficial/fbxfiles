"""Local model of named-profile reload behavior, not a real Unreal runtime."""
import unittest
from types import SimpleNamespace as NS
import setup_prop_actor_pilot as ep

U=NS(CollisionEnabled=NS(QUERY_ONLY='QueryOnly'),CollisionChannel=NS(ECC_WORLD_STATIC='WorldStatic',ECC_VISIBILITY='Visibility',ECC_PAWN='Pawn'),CollisionResponseType=NS(ECR_IGNORE='Ignore',ECR_BLOCK='Block'))
class Component:
    def __init__(self):self.profile='BlockAll';self.calls=[];self.reload()
    def modify(self):self.calls.append('modify')
    def reload(self):
        if self.profile=='BlockAll':self.enabled='QueryAndPhysics';self.responses={'Visibility':'Block','Pawn':'Block'}
    def set_collision_profile_name(self,name,update_overlaps=True):self.calls.append('profile');self.profile=name;self.reload()
    def get_collision_profile_name(self):return self.profile
    def set_collision_object_type(self,value):self.object_type=value
    def set_collision_enabled(self,value):self.enabled=value
    def get_collision_enabled(self):return self.enabled
    def set_collision_response_to_all_channels(self,value):self.responses={'Visibility':value,'Pawn':value}
    def set_collision_response_to_channel(self,channel,value):self.responses[channel]=value
    def get_collision_response_to_channel(self,channel):return self.responses[channel]
class ProfileTests(unittest.TestCase):
    def test_old_named_profile_reverts(self):
        c=Component();c.set_collision_enabled('QueryOnly');c.set_collision_response_to_all_channels('Ignore');c.set_collision_response_to_channel('Visibility','Block');c.reload()
        self.assertEqual(c.get_collision_response_to_channel('Pawn'),'Block')
        with self.assertRaisesRegex(ValueError,'BlockAll'):ep._check_pilot_collision(U,c)
    def test_custom_survives_profile_refresh_and_reload(self):
        c=Component();ep._apply_pilot_collision(U,c);c.reload();ep._check_pilot_collision(U,c)
        self.assertEqual(c.calls[:2],['modify','profile']);self.assertEqual(c.object_type,'WorldStatic')
    def test_each_policy_mismatch_rejected(self):
        for key,value in [('profile','BlockAll'),('enabled','QueryAndPhysics'),('Visibility','Ignore'),('Pawn','Block')]:
            c=Component();ep._apply_pilot_collision(U,c)
            if key in ('profile','enabled'):setattr(c,key,value)
            else:c.responses[key]=value
            with self.assertRaisesRegex(ValueError,'Pilot collision mismatch'):ep._check_pilot_collision(U,c)
if __name__=='__main__':unittest.main()
