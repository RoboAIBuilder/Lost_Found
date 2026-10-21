import json, os, random
HERE = os.path.dirname(__file__)
R = random.Random(42)

# ---- photo items: (kind, rgb, extra, closeup, title, category, color, brand, description, keywords)
P = [
 ("bottle",[92,170,220],{"sticker":[30,120,60],"cap":[30,30,35]},True,"Light blue Hydro Flask with soccer sticker","Water bottle","light blue","Hydro Flask","32 oz light blue bottle with black lid. Green soccer ball sticker on the front, small dent near the bottom.",["water bottle","hydroflask","flask","bottle","blue","soccer","sticker","dent"]),
 ("bottle",[235,180,200],{"cap":[240,240,240],"band":[200,120,150]},False,"Pink Stanley tumbler","Water bottle","pink","Stanley","40 oz pink Stanley with white lid, straw missing.",["stanley","cup","tumbler","bottle","pink","straw"]),
 ("bottle",[40,44,52],{"sticker":[230,60,60],"cap":[230,60,60]},True,"Black Owala bottle with red lid","Water bottle","black, red","Owala","Black Owala FreeSip with red lid. Red heart sticker; initials A.K. scratched on the bottom.",["owala","water bottle","black","red","heart","sticker","initials"]),
 ("bottle",[120,190,140],{"cap":[60,60,60]},False,"Sage green water bottle","Water bottle","sage green","","Plain sage green metal bottle, gray screw lid, no stickers.",["water bottle","green","metal","plain"]),
 ("bottle",[150,110,210],{"sticker":[250,200,60],"cap":[90,60,150]},True,"Purple bottle with star sticker","Water bottle","purple","Simple Modern","Purple Simple Modern bottle with a yellow star sticker and a chip in the paint near the lid.",["water bottle","purple","star","sticker","simple modern"]),
 ("hoodie",[30,45,90],{"logo":"NIKE","logo_c":[240,240,240]},True,"Navy Nike hoodie, size M","Jacket / hoodie","navy","Nike","Navy pullover hoodie, youth M, white Nike logo on chest. Front pocket has a pencil inside.",["hoodie","sweatshirt","jacket","navy","blue","nike","medium","pullover"]),
 ("hoodie",[130,130,135],{"logo":"EMS","logo_c":[200,30,40]},False,"Gray school spirit hoodie","Jacket / hoodie","heather gray","","Gray hoodie with red school spirit print, adult S. Cuffs a bit stretched.",["hoodie","sweatshirt","gray","grey","school","spirit","red"]),
 ("hoodie",[20,20,22],{"string":[20,20,22]},False,"Black zip-up hoodie","Jacket / hoodie","black","","Plain black zip hoodie, no logo, size S. Zipper pull missing.",["hoodie","sweatshirt","zip","black","plain","jacket"]),
 ("hoodie",[220,90,60],{"logo":"UA","logo_c":[255,255,255]},False,"Orange Under Armour hoodie","Jacket / hoodie","orange","Under Armour","Bright orange Under Armour hoodie, youth L.",["hoodie","sweatshirt","orange","under armour","ua"]),
 ("puffer",[25,30,40],{},True,"Black North Face puffer jacket","Jacket / hoodie","black","The North Face","Black puffer jacket, youth L. Gloves stuffed in the left pocket.",["jacket","coat","puffer","north face","black","winter","gloves"]),
 ("puffer",[180,40,50],{},False,"Red puffer vest-style jacket","Jacket / hoodie","red","Columbia","Red Columbia puffer, size M, hood zipped off.",["jacket","coat","puffer","red","columbia","winter"]),
 ("backpack",[40,90,170],{"patch":[250,200,40],"keychain":[240,90,140]},True,"Blue JanSport backpack with keychain","Backpack / bag","blue","JanSport","Royal blue JanSport with yellow smiley patch and a pink plush keychain. Has a math binder inside.",["backpack","bookbag","bag","blue","jansport","keychain","patch","binder"]),
 ("backpack",[60,60,60],{},False,"Gray Herschel backpack","Backpack / bag","charcoal gray","Herschel","Charcoal Herschel backpack, empty except for a gym shirt.",["backpack","bag","gray","grey","herschel","gym"]),
 ("backpack",[210,150,190],{"patch":[255,255,255]},False,"Pink drawstring bag","Backpack / bag","pink","","Pink cinch/drawstring bag with sneakers inside.",["drawstring","bag","cinch","pink","sneakers","gym bag"]),
 ("lunchbox",[120,70,170],{"print":[250,220,90]},True,"Purple lunch box with yellow dots","Lunch box","purple","PackIt","Purple insulated lunch box with yellow polka dots. Empty ice pack inside.",["lunch box","lunchbox","lunch bag","purple","polka dots","ice pack"]),
 ("lunchbox",[40,140,110],{},False,"Green lunch bag","Lunch box","green","L.L.Bean","Dark green lunch bag, name tag slot is empty.",["lunch box","lunch bag","green","llbean"]),
 ("calculator",[30,32,38],{"initials":"J.M.","top":[80,130,200]},True,"TI-84 Plus CE calculator","Calculator","black","Texas Instruments","Black TI-84 Plus CE graphing calculator, initials J.M. in white paint marker on the back.",["calculator","ti-84","ti84","graphing","texas instruments","black","initials"]),
 ("calculator",[230,230,232],{"keys":[90,90,95],"top":[60,160,120]},False,"White TI-84 calculator","Calculator","white","Texas Instruments","White TI-84 Plus CE, no case, small crack in the screen corner.",["calculator","ti-84","graphing","white","cracked"]),
 ("calculator",[60,80,130],{"keys":[40,40,45],"top":[200,90,60]},False,"Blue TI-30XS scientific calculator","Calculator","blue","Texas Instruments","Blue TI-30XS MultiView scientific calculator with slide cover.",["calculator","scientific","ti-30","blue","texas instruments"]),
 ("notebook",[200,50,50],{"label":"SCI 7"},False,"Red Five Star science notebook","Book / notebook","red","Five Star","Red spiral notebook labeled SCI 7, half full of lab notes.",["notebook","spiral","red","science","five star","sci 7"]),
 ("notebook",[30,30,30],{"marble":True},False,"Black composition notebook","Book / notebook","black and white","","Marble composition notebook, ELA journal entries inside.",["notebook","composition","marble","black","ela","journal"]),
 ("glasses",[40,30,30],{"case":[70,110,170]},True,"Black-frame glasses in blue case","Glasses","black","","Black rectangular prescription glasses with a blue hard case.",["glasses","eyeglasses","spectacles","black","case","prescription"]),
 ("glasses",[200,120,160],{},False,"Pink kids' glasses","Glasses","pink","","Pink round frames, one nose pad loose.",["glasses","eyeglasses","pink","round"]),
 ("keys",[200,40,40],{"charm":[60,160,220]},True,"House keys on red lanyard","Keys / ID","red","","Two keys (one gold, one silver) on a red lanyard with a blue round charm.",["keys","key","lanyard","red","house key","charm"]),
 ("headphones",[240,240,242],{},False,"White over-ear headphones","Electronics","white","Beats","White Beats Solo over-ear headphones, no case.",["headphones","beats","white","over ear","headset"]),
 ("headphones",[30,30,35],{},False,"Black Skullcandy headphones","Electronics","black","Skullcandy","Black Skullcandy wireless headphones, right ear cushion peeling.",["headphones","skullcandy","black","wireless","headset"]),
 ("earbuds",[245,245,245],{"skin":[120,180,230]},True,"AirPods case with blue cover","Electronics","white, blue","Apple","AirPods case in a light blue silicone cover. Only the left earbud is inside.",["airpods","earbuds","apple","case","blue","cover"]),
 ("cap",[30,60,130],{"logo":"NY","logo_c":[255,255,255]},False,"Navy Yankees cap","Other clothing","navy","New Era","Navy NY Yankees baseball cap, adjustable strap.",["hat","cap","baseball cap","yankees","navy","ny"]),
 ("beanie",[200,40,50],{"pom":[250,250,250]},False,"Red knit beanie with pom-pom","Other clothing","red","","Red knit winter hat with white pom-pom.",["beanie","hat","winter hat","red","pom pom","knit"]),
 ("sneaker",[245,245,245],{"swoosh":[20,20,20],"sole":[230,230,230]},True,"One white Nike sneaker, size 6","Sports gear","white","Nike","Single white Nike Air Force 1, size 6, left foot. Black swoosh.",["shoe","sneaker","nike","white","air force","size 6","left"]),
 ("ball",[20,20,20],{},False,"Soccer ball with name on it","Sports gear","white, black","Adidas","Size 5 soccer ball, 'CARLOS' written in marker between panels.",["soccer ball","ball","football","soccer","name","adidas"]),
 ("ball",[0,0,0],{"kind":"basketball"},False,"Basketball","Sports gear","orange","Spalding","Spalding outdoor basketball, worn grip.",["basketball","ball","orange","spalding"]),
 ("umbrella",[30,40,90],{"dots":[250,250,250]},False,"Navy polka-dot umbrella","Other","navy","","Compact navy umbrella with white dots, curved wooden handle.",["umbrella","navy","dots","rain"]),
 ("pencilcase",[250,200,40],{"patches":[[230,80,120],[80,160,230],[120,200,120]]},True,"Yellow pencil case with pins","School supplies","yellow","","Yellow zip pencil pouch with three enamel pins. Pencils, a ruler, and a pink eraser inside.",["pencil case","pouch","yellow","pins","pencils","supplies"]),
 ("charger",[245,245,245],{},False,"White USB-C charger and cable","Electronics","white","Apple","White Apple 20W USB-C charger with a 3 ft cable.",["charger","cable","usb-c","apple","white","phone charger"]),
]

# ---- text-only items
T = [
 ("Water bottle",[("Blue Yeti tumbler","blue","Yeti","Blue Yeti Rambler with magnetic slider lid.",["yeti","tumbler","cup","blue"]),
                  ("Clear plastic Nalgene","clear","Nalgene","Clear Nalgene with mountain stickers.",["nalgene","clear","plastic","stickers"]),
                  ("Teal Contigo bottle","teal","Contigo","Teal Contigo with flip spout, lid cracked.",["contigo","teal","water bottle"]),
                  ("White CamelBak bottle","white","CamelBak","White CamelBak with bite valve.",["camelbak","white","water bottle"]),
                  ("Black Stanley tumbler","black","Stanley","Black 30 oz Stanley, scratched handle.",["stanley","tumbler","black","cup"]),
                  ("Green Hydro Flask with name tape","green","Hydro Flask","Green Hydro Flask, masking tape with 'MAYA' on the lid.",["hydroflask","green","name","maya"])]),
 ("Jacket / hoodie",[("Gray Adidas track jacket","gray","Adidas","Gray Adidas zip track jacket, three white stripes.",["jacket","adidas","gray","track"]),
                     ("Green camo hoodie","green camo","","Camo pullover hoodie, youth M.",["hoodie","camo","green","sweatshirt"]),
                     ("Light pink fleece","light pink","","Pink half-zip fleece, size S.",["fleece","pink","sweater","half zip"]),
                     ("Maroon cardigan","maroon","Old Navy","Maroon button cardigan, adult XS.",["cardigan","sweater","maroon","old navy"]),
                     ("Blue rain jacket","blue","Columbia","Blue Columbia rain shell with hood.",["rain jacket","raincoat","blue","columbia"]),
                     ("White Champion hoodie","white","Champion","White Champion hoodie, ink stain on sleeve.",["hoodie","champion","white","sweatshirt","stain"]),
                     ("Black denim jacket","black","Levi's","Black denim jacket with patches on the back.",["jean jacket","denim","black","levis","patches"]),
                     ("Navy school fleece","navy","","Navy fleece with school logo, youth L.",["fleece","navy","school","jacket"])]),
 ("Other clothing",[("Gray sweatpants","gray","Nike","Gray Nike joggers, size M.",["sweatpants","joggers","pants","gray","nike"]),
                    ("Black gym shorts","black","Under Armour","Black UA gym shorts.",["shorts","gym","black","under armour","pe"]),
                    ("Purple scarf","purple","","Knit purple scarf with fringe.",["scarf","purple","knit"]),
                    ("Pair of black gloves","black","","Black knit gloves, touchscreen tips.",["gloves","black","winter"]),
                    ("Red PE shirt","red","","Red school PE t-shirt, size M, name smudged on tag.",["pe shirt","gym shirt","t-shirt","red"]),
                    ("Black beanie","black","Carhartt","Black Carhartt beanie.",["beanie","hat","carhartt","black"]),
                    ("White baseball cap","white","","White cap with small embroidered palm tree.",["hat","cap","white","palm tree"])]),
 ("Backpack / bag",[("Black Nike backpack","black","Nike","Black Nike Elemental backpack with water bottle pocket torn.",["backpack","nike","black","bag"]),
                    ("Green tote bag","green","","Canvas tote from the book fair.",["tote","bag","green","book fair"]),
                    ("Red gym duffel","red","Adidas","Small red Adidas duffel with cleats inside.",["duffel","gym bag","red","adidas","cleats"]),
                    ("Tan crossbody bag","tan","","Small tan crossbody with lip balm inside.",["purse","crossbody","bag","tan"])]),
 ("Lunch box",[("Blue Bentgo box","blue","Bentgo","Blue Bentgo bento container, leftover crackers.",["bentgo","bento","lunch box","blue"]),
               ("Black lunch bag","black","","Black insulated lunch bag with gray zipper.",["lunch bag","black","insulated"]),
               ("Pink thermos","pink","Thermos","Pink Thermos food jar.",["thermos","pink","food jar","soup"])]),
 ("Electronics",[("Black wired earbuds","black","","Black wired earbuds with 3.5 mm plug.",["earbuds","earphones","headphones","black","wired"]),
                 ("Phone charger cable","white","","White Lightning cable, 6 ft.",["charger","cable","lightning","iphone"]),
                 ("School Chromebook charger","black","Dell","Black Dell USB-C laptop charger with school asset sticker.",["chromebook","charger","laptop","dell"]),
                 ("Red phone case (no phone)","red","","Red silicone iPhone case, empty.",["phone case","case","red","iphone"]),
                 ("Fitbit watch","black","Fitbit","Black Fitbit Inspire, band intact.",["watch","fitbit","fitness tracker","black"]),
                 ("Wired gaming headset","green, black","Razer","Green and black Razer headset.",["headset","headphones","razer","gaming","green"])]),
 ("Calculator",[("Gray Casio calculator","gray","Casio","Gray Casio fx-300 scientific calculator.",["calculator","casio","scientific","gray"]),
                ("TI-84 with green case","black","Texas Instruments","TI-84 Plus in a green slide-on case.",["calculator","ti-84","graphing","green case"])]),
 ("Book / notebook",[("Library book: Wonder","various","","Wonder by R.J. Palacio, school library copy.",["book","library book","wonder","novel"]),
                     ("Blue binder","blue","Five Star","Blue 1.5 in binder with math worksheets.",["binder","blue","math","five star"]),
                     ("Spanish workbook","orange","","Orange Spanish 1 workbook, partly filled in.",["workbook","spanish","orange","book"]),
                     ("Sketchbook","black","Canson","Black Canson sketchbook with anime drawings.",["sketchbook","drawing","art","black"]),
                     ("Yellow spiral notebook","yellow","Mead","Yellow Mead notebook labeled 'Social Studies'.",["notebook","yellow","social studies","spiral"]),
                     ("Library book: Dog Man","various","","Dog Man book, library copy, cover bent.",["book","dog man","library book","graphic novel"]),
                     ("Green folder","green","","Green plastic folder with field trip permission slip.",["folder","green","permission slip"])]),
 ("School supplies",[("Black pencil case","black","","Black zip pencil case with gel pens.",["pencil case","pouch","black","pens"]),
                     ("Ruler and protractor set","clear","","Clear plastic ruler and protractor.",["ruler","protractor","math","geometry"]),
                     ("Pack of colored pencils","multi","Crayola","24-pack Crayola colored pencils in a tin.",["colored pencils","crayola","art"]),
                     ("Scientific compass","silver","","Metal drawing compass for geometry.",["compass","geometry","math"]),
                     ("Clear pencil pouch","clear","","Clear pouch with highlighters.",["pencil case","highlighters","clear"])]),
 ("Sports gear",[("Shin guards","black","Nike","Pair of black Nike shin guards.",["shin guards","soccer","nike","black"]),
                 ("Volleyball","white, blue","Mikasa","Mikasa volleyball, initials R.T.",["volleyball","ball","mikasa","initials"]),
                 ("Baseball glove","brown","Rawlings","Brown Rawlings youth glove, left-handed thrower.",["glove","mitt","baseball","softball","rawlings"]),
                 ("Black cleats, size 7","black","Adidas","Black Adidas soccer cleats, size 7.",["cleats","shoes","soccer","adidas","black"]),
                 ("Lacrosse stick","white","STX","White STX lacrosse stick.",["lacrosse","stick","stx"]),
                 ("Jump rope","red","","Red speed jump rope.",["jump rope","rope","red","pe"]),
                 ("Tennis racket","blue","Wilson","Blue Wilson junior racket, no cover.",["tennis","racket","wilson","blue"])]),
 ("Glasses",[("Tortoiseshell glasses","brown","","Tortoiseshell frames in a black soft pouch.",["glasses","eyeglasses","tortoise","brown"]),
             ("Sunglasses","black","Ray-Ban","Black Ray-Ban style sunglasses.",["sunglasses","shades","black"]),
             ("Clear-frame glasses","clear","","Clear plastic frames, no case.",["glasses","eyeglasses","clear"])]),
 ("Jewelry / accessory",[("Silver bracelet","silver","","Thin silver chain bracelet with a heart charm.",["bracelet","jewelry","silver","heart"]),
                         ("Friendship bracelets","multi","","Three braided string bracelets.",["bracelet","friendship","string"]),
                         ("Black hair clip","black","","Large black claw clip.",["hair clip","claw clip","black"]),
                         ("Gold stud earring","gold","","Single small gold stud earring.",["earring","gold","jewelry"]),
                         ("Digital watch","black","Casio","Black Casio digital watch.",["watch","casio","black","digital"]),
                         ("Scrunchie set","pink","","Two pink velvet scrunchies.",["scrunchie","hair","pink"])]),
 ("Keys / ID",[("Student ID on blue lanyard","blue","","Student ID card on a blue school lanyard.",["id","student id","lanyard","blue","badge"]),
               ("Single house key","silver","","One silver key with a green rubber cap.",["key","house key","silver","green"]),
               ("Bike lock key","black","","Small key on a ring with a bike lock tag.",["key","bike lock","ring"])]),
 ("Other",[("Retainer case","blue","","Blue retainer case. Empty.",["retainer","case","blue","orthodontic"]),
           ("Stuffed animal keychain","brown","","Small brown teddy bear keychain.",["keychain","teddy bear","plush","brown"]),
           ("Reusable lunch fork set","green","","Green travel utensil set.",["fork","spoon","utensils","green"]),
           ("Clarinet reed case","black","","Black reed case with three reeds.",["reed","clarinet","band","music"]),
           ("Black umbrella","black","Totes","Compact black Totes umbrella.",["umbrella","black","totes","rain"]),
           ("Lip balm","pink","","Pink lip balm tube.",["chapstick","lip balm","pink"]),
           ("Rubik's cube","multi","","3x3 speed cube, stickerless.",["rubiks cube","cube","puzzle","toy"])]),
]

LOCS = ["Main office, bin A","Main office, bin B","Main office, shelf 2","Main office, coat rack","Gym office, cubby 3","Library desk drawer","Nurse's office cabinet","Main office, valuables drawer"]
WHERE = ["Gym bleachers","Cafeteria","Bus loop","Library","Room 214","Hallway B lockers","Soccer field","Music room","Art room","Auditorium","Locker room","Room 108","Front steps","Playground",""]

def loc_for(cat):
    if cat in ("Electronics","Keys / ID","Jewelry / accessory","Glasses","Calculator"): return R.choice(["Main office, valuables drawer","Nurse's office cabinet"])
    if cat == "Jacket / hoodie": return R.choice(["Main office, coat rack","Main office, bin A"])
    if cat == "Sports gear": return R.choice(["Gym office, cubby 3","Main office, bin B"])
    if cat == "Book / notebook": return R.choice(["Library desk drawer","Main office, shelf 2"])
    return R.choice(["Main office, bin A","Main office, bin B","Main office, shelf 2"])

import time
NOW = int(time.time()*1000); DAY = 86400000
items, specs = [], []
used_tags = set()
def tag():
    while True:
        t = f"LF-{R.randint(1000,9999)}"
        if t not in used_tags: used_tags.add(t); return t

for n,(kind,rgb,extra,close,title,cat,color,brand,desc,kw) in enumerate(P, start=1):
    specs.append({"n":n,"kind":kind,"rgb":rgb,"extra":extra,"closeup":close})
    items.append({"photo_n":n,"closeup":close,"title":title,"category":cat,"color":color,"brand":brand,"description":desc,"keywords":kw})

for cat, rows in T:
    for (title,color,brand,desc,kw) in rows:
        items.append({"photo_n":None,"title":title,"category":cat,"color":color,"brand":brand,"description":desc,"keywords":kw})

# duplicates to reach a realistic volume (schools get many near-identical items)
DUPES = [("Water bottle","Blue water bottle, no lid","blue","","Blue metal bottle, lid missing.",["water bottle","blue","no lid"]),
         ("Jacket / hoodie","Navy hoodie, no logo","navy","","Plain navy pullover, youth S.",["hoodie","navy","sweatshirt","plain"]),
         ("Jacket / hoodie","Black hoodie, size L","black","Nike","Black Nike hoodie, adult L.",["hoodie","black","nike","large"]),
         ("Other clothing","Single white sock","white","","One white athletic sock from the locker room.",["sock","white"]),
         ("Water bottle","Gray Stanley tumbler","gray","Stanley","Gray Stanley 30 oz with straw.",["stanley","gray","tumbler","cup"]),
         ("School supplies","Blue pencil case","blue","","Blue zip pencil case with markers.",["pencil case","blue","markers"]),
         ("Electronics","White wired earbuds","white","Apple","Apple wired EarPods.",["earbuds","earpods","apple","white","wired"]),
         ("Book / notebook","Library book: Diary of a Wimpy Kid","various","","Diary of a Wimpy Kid #3, library copy.",["book","wimpy kid","library book"]),
         ("Other clothing","Gray beanie","gray","","Gray knit beanie.",["beanie","hat","gray"]),
         ("Water bottle","Purple Owala bottle","purple","Owala","Purple Owala, lid sticky.",["owala","purple","water bottle"]),
         ("Jacket / hoodie","Green zip-up jacket","green","The North Face","Green North Face fleece zip-up.",["jacket","fleece","green","north face"]),
         ("Sports gear","Mouthguard in case","clear","Shock Doctor","Clear mouthguard in a blue case.",["mouthguard","sports","case"])]
for d in DUPES:
    cat,title,color,brand,desc,kw = d
    items.append({"photo_n":None,"title":title,"category":cat,"color":color,"brand":brand,"description":desc,"keywords":kw})

# assign tags, dates, places, status
for i,it in enumerate(items):
    it["tag"]=tag()
    days = R.choice([R.randint(0,14)]*5 + [R.randint(15,29)]*3 + [R.randint(30,75)]*2)
    it["foundAt"] = NOW - days*DAY - R.randint(1,9)*3600000
    it["location"]=loc_for(it["category"])
    it["foundWhere"]=R.choice(WHERE)
    it["status"]="available"
returned_idx = R.sample([i for i,it in enumerate(items) if it["photo_n"] is None], 10)
for i in returned_idx:
    items[i]["status"]="returned"; items[i]["returnedAt"]=items[i]["foundAt"]+R.randint(1,6)*DAY
R.shuffle(items)
for i,it in enumerate(items): it["doc_id"]=f"mock-{i+1:03d}"

json.dump(specs, open(os.path.join(HERE,"photo_specs.json"),"w"))
json.dump(items, open(os.path.join(HERE,"items_draft.json"),"w"), indent=1)
print(len(items),"items;",sum(1 for i in items if i["photo_n"]),"with photos;",sum(1 for i in items if i["status"]=="returned"),"returned;",sum(1 for i in items if (NOW-i["foundAt"])>=30*DAY and i["status"]!="returned"),"30+ days")
