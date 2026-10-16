"""Deterministic logical assemblies for the authored Evergreen scene.

Read-only with respect to Blender objects. Call build_groups(objects, centers),
where centers maps object.name to an evaluated WORLD bounding-box centre.
Unmatched scenery remains available to the caller. Inspect ERRORS and SUMMARY
after the call; a failed assembly is never partially committed or guessed.
Coordinates and anchors are Blender metres. Tiers are recommendations only.
"""
import math
import re
from collections import defaultdict, Counter

ERRORS = []
SUMMARY = {}


def build_groups(objects, centers):
    global ERRORS, SUMMARY
    ERRORS = []
    SUMMARY = {}
    objects = list(objects)
    indexed = defaultdict(list)
    for ob in objects:
        indexed[re.sub(r"\.\d+$", "", ob.name)].append(ob)
    used = set()
    groups = []
    candidate_prefixes = set()

    def pos(ob):
        # Text origins are source anchors; visible glyph bounds vary by content.
        if getattr(ob, 'type', '') == 'FONT':
            return tuple(float(v) for v in ob.location)
        return tuple(float(v) for v in centers[ob.name])

    def near(prefix, target, tol=None, unclaimed=True):
        candidate_prefixes.add(prefix)
        out = []
        for ob in indexed.get(prefix, []):
            if unclaimed and ob.name in used:
                continue
            if ob.name not in centers and getattr(ob, 'type', '') != 'FONT':
                continue
            p = pos(ob)
            tolerance = tol if tol is not None else (.023 if getattr(ob, 'type', '') == 'CURVE' else .001)
            if max(abs(p[i] - target[i]) for i in range(3)) <= tolerance:
                out.append(ob)
        return out

    def add(family, tier, anchor, requests=(), rotation=0.0, extra=(), expected=None):
        members = list(extra)
        problems = []
        for req in requests:
            prefix, target = req[:2]
            matches = near(prefix, target, req[2] if len(req) > 2 else None)
            if len(matches) != 1:
                problems.append({'prefix': prefix, 'target': list(target), 'matches': [o.name for o in matches]})
            else:
                members.append(matches[0])
        names = [o.name for o in members]
        if len(names) != len(set(names)):
            problems.append({'duplicate_members': names})
        if any(n in used for n in names):
            problems.append({'already_claimed': [n for n in names if n in used]})
        if expected is not None and len(members) != expected:
            problems.append({'expected_members': expected, 'actual_members': len(members)})
        if problems:
            ERRORS.append({'family': family, 'anchor': list(anchor), 'problems': problems})
            return False
        groups.append({'family': family, 'tier': tier, 'anchor': [float(v) for v in anchor],
                       'rotation_z': float(rotation), 'members': members})
        used.update(names)
        return True

    def wheel(x, y, z=.12):
        return [('Rubber caster', (x, y, z)), ('Caster hub', (x, y-.025, z))]

    # Each cart has 38 components; every original cart has zero source rotation.
    for x,y in [(-16,-15),(-15.2,-15),(-14.4,-15),(-13.6,-15),(-10,-1),(18,5),(-10,13)]:
        r=[]
        for xx in (-.27,.27):
            for yy in (-.4,.4): r += wheel(x+xx,y+yy)
        r += [('Cart lower frame',(x,y,.23)),('Cart handle',(x,y+.65,1.0))]
        for xx in (-.3,.3): r.append(('Cart handle frame',(x+xx,y+.535,.6)))
        for z in (.47,.62,.78,.94): r.append(('Wire basket rim',(x,y,z)))
        for j in range(13): r.append(('Wire cart basket',(x,y+(-.39+j*.065)*1.15,.705)))
        for j in range(9): r.append(('Wire cart longitudinal',(x+(-.25+j*.0625)*1.175,y,.705)))
        add('ShoppingCart','conditional_large',(x,y,.04),r,expected=38)

    # Stacked baskets overlap: exact component heights prevent cross-layer joins.
    for j in range(7):
        x,y,z=-11.8,-15,.15+j*.09
        r=[('Shopping basket base',(x,y,z)),('Basket rim',(x,y,z+.25))]
        for yy in (-.2,.2):
            for k in range(9): r.append(('Basket slot rib',(x-.28+k*.07,y+yy,z+.13)))
        for xx in (-.3,.3): r.append(('Basket end',(x+xx,y,z+.13)))
        add('ShoppingBasket','default',(x,y,z-.0225),r,expected=22)

    def pallet(x,y,z):
        r=[('Pallet stringer',(x+xx,y,z+.08)) for xx in (-.48,0,.48)]
        r += [('Pallet deck board',(x,y+yy,z+.18)) for yy in (-.52,-.26,0,.26,.52)]
        add('WoodPallet','conditional_large_flat',(x,y,z),r,expected=8)

    def carton(x,y,z,w,d,h,variant):
        add('ShippingCarton_'+variant,'default',(x,y,z),[
            ('PROP shipping carton',(x,y,z+h/2)),
            ('Carton packing tape',(x,y,z+h+.003)),
            ('Carton printed label',(x,y-d/2-.007,z+h*.6)),
            ('Carton handling text',(x,y-d/2-.013,z+h*.6))],expected=4)

    for x in (-20,-11,-2):
        for y in (22,27.5):
            for z in (.25,1.65,3.05):
                for xx in (-1.05,0,1.05):
                    pallet(x+xx,y,z+.035)
                    for zz in (0,.42):
                        for dy in (-.28,.28):
                            for dx in (-.25,.25): carton(x+xx+dx,y+dy,z+.3+zz,.46,.5,.39,'Rack')
    for x,y in [(-16,25),(-7,20),(3,28)]:
        pallet(x,y,0)
        for k in range(6): carton(x-.29+(k%2)*.58,y-.32+((k//2)%2)*.64,.23+(k//4)*.5,.55,.59,.48,'Floor')
    for x in (25,28,31):
        for y in (14,18):
            for j in range(3): pallet(x,y,j*.23)
            if (x+y)%2:
                for k in range(4): carton(x-.3+(k%2)*.6,y-.3+(k//2)*.6,.7,.55,.55,.6,'Yard')

    islands=[(-17,-7),(-13,-7),(-17,-1),(-13,-1),(-17,5)]
    for x,y in islands:
        for xx in (-.67,.67):
            for yy in (-1.05,0,1.05):
                cx,cy,z=x+xx,y+yy,.87
                r=[('Produce crate base',(cx,cy,z+.045))]
                for level in range(3):
                    zz=z+.13+level*.09
                    for dx in (-.6,.6): r.append(('Produce crate side slat',(cx+dx,cy,zz)))
                    for dy in (-.475,.475): r.append(('Produce crate end slat',(cx,cy+dy,zz)))
                for dx in (-.6,.6):
                    for dy in (-.475,.475): r.append(('Produce crate corner',(cx+dx,cy+dy,z+.2)))
                add('ProduceCrate','default',(cx,cy,z),r,expected=17)

    for x,y,a in [(14.7,22,0),(16.9,22,0),(14.7,25.3,math.pi),(16.9,25.3,math.pi)]:
        r=[('Staff chair seat',(x,y,.47)),('Staff chair back',(x,y+(-.25 if a==0 else .25),.85))]
        for xx in (-.23,.23):
            for yy in (-.23,.23): r.append(('Chair steel leg',(x+xx,y+yy,.23)))
        add('StaffChair','default',(x,y,0),r,rotation=a,expected=6)
    for x,y in [(14.9,23.5),(16.2,24),(17,23.2),(10.5,20.9)]:
        z=.96 if x>12 else 1.14
        add('CeramicMug','conditional_tiny',(x,y,z-.075),[
            ('PROP ceramic mug',(x,y,z)),('Mug handle',(x+.09,y,z+.025))],expected=2)
    for x,y in [(12,21),(20,26),(4,19)]:
        add('UtilityBin','default',(x,y,0),[('PROP utility bin',(x,y,.4)),('Bin lid',(x,y,.81))],expected=2)
    for x in (-5,1,7,13):
        for j in range(3):
            xx=x-.38+j*.3
            add('PaperShoppingBag','default',(xx,-14.6,1.1),[
                ('Paper shopping bag',(xx,-14.6,1.35)),('Paper bag handle',(xx,-14.6,1.66))],expected=2)

    for y in (10,13.5,16.5):
        for z in (1.12,1.68,2.24):
            for a in range(3):
                for b in range(6):
                    x,yy=-21+a*.57,y-1.1+b*.43
                    r=[('PROP crusty loaf',(x,yy,z+.13))]
                    for q in (-.09,.03,.14): r.append(('Bread scoring',(x+q-.005,yy-.005,z+.22)))
                    add('CrustyLoaf','conditional_tiny',(x,yy,z+.01),r,expected=4)
    for ob in indexed.get('PROP bakery roll',[]):
        x,y,z=pos(ob)
        add('BakeryRoll','conditional_tiny',(x,y,z-.09),extra=[ob],expected=1)
    for fruit in ('apple','green apple','orange','lemon','eggplant'):
        prefix='PROP_'+fruit
        candidate_prefixes.add(prefix)
        for ob in indexed.get(prefix,[]):
            x,y,z=pos(ob); h=.16 if fruit=='eggplant' else .1
            stems=near('Fruit stem',(x,y,z+h),.001)
            if len(stems)>1:
                ERRORS.append({'family':fruit,'anchor':[x,y,z],'ambiguous_stems':[s.name for s in stems]})
                continue
            add('Fruit_'+fruit.replace(' ','_')+('_Stemmed' if stems else '_Plain'),
                'conditional_tiny',(x,y,z-h),extra=[ob]+stems,expected=1+bool(stems))

    # Complete stocked cleaning trolley. Buckets are included, not duplicated.
    r=[('Janitor trolley base',(4.7,21,.25))]
    for x in (4.2,5.2):
        for y in (20.75,21.25): r += wheel(x,y)
    for x in (4.4,5): r += [('Cleaning bucket',(x,21,.58)),('Bucket dark opening',(x,21,.89))]
    for x in (4.2,4.5): r.append(('Mop handle',(x+.1,21.3,1.0)))
    add('CleaningTrolley','conditional_large',(4.7,21,.04),r,expected=15)
    add('WetFloorSign','default',(5.6,20.9,.0487),[
        ('Folded wet floor sign',(5.6,20.9,.45)),('Safety lettering',(5.6,20.85,.5))],expected=2)
    r=[('Pallet jack hydraulic body',(-7,25,.24)),('Pallet jack handle',(-7,25.35,.825))]
    for x in (-7.35,-6.65): r += [('Pallet jack fork',(x,24.25,.13))]+wheel(x,23.6)
    add('PalletJack','conditional_large',(-7,25,.04),r,expected=8)
    for y in (21,24):
        r=[('Commercial refuse container',(35,y,.75)),('Dumpster lid',(35,y,1.5)),('Recycling label',(35,y-1.065,.95))]
        for xx in (-.7,.7):
            for yy in (-.8,.8): r += wheel(35+xx,y+yy,.1)
        add('CommercialRefuseContainer','conditional_large',(35,y,.02),r,expected=11)
    for x,y in [(-21.65,-12),(7.6,21),(21.6,15.9)]:
        add('FireExtinguisher','default',(x,y,.55),[
            ('Fire extinguisher',(x,y,.8)),('Extinguisher bracket',(x,y+.04,1.1)),
            ('Extinguisher hose',(x+.11,y,.825))],expected=3)
    add('CoffeeMachine','default',(10.8,21.3,1.02),[
        ('Coffee machine',(10.8,21.3,1.32)),('Coffee front plate',(10.8,21.06,1.32))],expected=2)
    add('Microwave','default',(10,21.35,1.01),[
        ('Microwave',(10,21.35,1.22)),('Microwave glass',(9.9,21.08,1.24))],expected=2)
    for i,(x,y) in enumerate([(-20,-7),(-20,0),(-20,7)],1):
        leaves=[o for o in indexed.get('Herb foliage',[]) if o.name not in used
                and abs(pos(o)[0]-x)<.3 and abs(pos(o)[1]-y)<.3 and 1.17<pos(o)[2]<1.39]
        candidate_prefixes.add('Herb foliage')
        add('HerbPlanter_V%02d'%i,'default',(x,y,.55),[('Herb pot',(x,y,.8))],extra=leaves,expected=16)
    for ob in indexed.get('Baking tray',[]):
        x,y,z=pos(ob)
        add('BakingTray','conditional_tiny_flat',(x,y,z-.015),extra=[ob],expected=1)

    # Fixed assemblies whose logical grouping is unambiguous.
    for x in (-18,-10,10,18):
        add('SafetyBollard','fixed_scenery',(x,-20.5,.005),[
            ('Safety bollard',(x,-20.5,.48)),('Bollard reflective band',(x,-20.5,.79))],expected=2)
    for x in (10,12,14,16,18,20):
        r=[('Staff locker',(x,29.35,1.05)),('Locker recessed door',(x,28.82,1.06)),
           ('Locker handle',(x+.57,28.75,1.05)),('Locker number',(x,28.78,1.5))]
        r += [('Locker vent',(x,28.79,z)) for z in (1.7,1.78,1.86)]
        add('StaffLocker_%02d'%int(x-9),'fixed_scenery',(x,29.35,0),r,expected=7)
    r=[('Staff table',(16,23.7,.79))]
    for xx in (-1.45,1.45):
        for yy in (-.75,.75): r.append(('Table leg',(16+xx,23.7+yy,.39)))
    add('StaffTable','fixed_scenery',(16,23.7,0),r,expected=5)
    add('StaffKitchenette','fixed_scenery',(10,21.2,0),[
        ('Staff kitchenette',(10,21.2,.45)),('Kitchen worktop',(10,21.2,.96)),
        ('Kitchen sink',(9.3,21.2,1.025)),('Kitchen tap',(9.3,21.4,1.215))],expected=4)
    for y in (10,13.5,16.5):
        r=[('Bakery cabinet base',(-20.5,y,.52)),('Bakery top light',(-20.4,y,2.85))]
        r += [('Bakery oak shelf',(-20.4,y,z)) for z in (1.12,1.68,2.24)]
        r += [('Bakery upright',(-20.45,y+dy,1.5)) for dy in (-1.4,1.4)]
        add('BakeryWallCabinet','fixed_scenery',(-20.5,y,0),r,expected=7)
    add('BakeryIsland','fixed_scenery',(-15.5,13,0),[
        ('Bakery island',(-15.5,13,.5)),('Bakery marble counter',(-15.5,13,1.05)),
        ('Bakery sneeze glass',(-15.5,13.9,1.6))],expected=3)
    for x,y in islands:
        r=[('Produce island plinth',(x,y,.24)),('Produce oak worktop',(x,y,.78))]
        for xx in (-1.15,1.15):
            for yy in (-1.5,1.5): r.append(('Island leg',(x+xx,y+yy,.53)))
        add('ProduceIsland','fixed_scenery',(x,y,0),r,expected=6)

    # Fail closed on any missed known component; leave untouched for diagnosis.
    unclaimed={p:[o.name for o in indexed.get(p,[]) if o.name not in used]
               for p in sorted(candidate_prefixes)}
    unclaimed={p:n for p,n in unclaimed.items() if n}
    if unclaimed:
        ERRORS.append({'unclaimed_candidate_components':unclaimed})
    flat=[o.name for g in groups for o in g['members']]
    assert len(flat)==len(set(flat)), 'An object was assigned to multiple logical assemblies'
    expected_counts={'ShoppingCart':7,'ShoppingBasket':7,'WoodPallet':75,
                     'ShippingCarton_Rack':432,'ShippingCarton_Floor':18,'ShippingCarton_Yard':16,
                     'ProduceCrate':30,'StaffChair':4,'CeramicMug':4,'UtilityBin':3,
                     'PaperShoppingBag':12,'CrustyLoaf':162,'BakeryRoll':36,
                     'CleaningTrolley':1,'WetFloorSign':1,'PalletJack':1,
                     'CommercialRefuseContainer':2,'FireExtinguisher':3,
                     'CoffeeMachine':1,'Microwave':1,'BakingTray':6,'SafetyBollard':4,
                     'StaffTable':1,'StaffKitchenette':1,'BakeryWallCabinet':3,'BakeryIsland':1,'ProduceIsland':5}
    counts=Counter(g['family'] for g in groups)
    for family,expected in expected_counts.items():
        if counts[family]!=expected:
            ERRORS.append({'family':family,'expected_groups':expected,'actual_groups':counts[family]})
    for fruit in ('apple','green_apple','orange','lemon','eggplant'):
        for variant,expected in [('Stemmed',30),('Plain',90)]:
            family='Fruit_'+fruit+'_'+variant
            if counts[family]!=expected:
                ERRORS.append({'family':family,'expected_groups':expected,'actual_groups':counts[family]})
    SUMMARY={'group_count':len(groups),'claimed_objects':len(used),
             'unclaimed_objects':len(objects)-len(used),'family_counts':dict(sorted(counts.items())),
             'error_count':len(ERRORS)}
    return groups
