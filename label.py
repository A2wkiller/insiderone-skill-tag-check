import csv, re, json
from collections import Counter, defaultdict

UP='/mnt/user-data/uploads/'
skills=[r['skill'].strip() for r in csv.DictReader(open(UP+'skill-list.csv',encoding='utf-8-sig'))]
jds=list(csv.DictReader(open(UP+'job-descriptions-tagged.csv',encoding='utf-8-sig')))

# Synonym map: model's variant -> canonical skill on the list (judged the same skill)
SYN={'node':'Node.js','postgres':'PostgreSQL','excel':'Microsoft Excel','financial modeling':'Financial Modelling',
     'js':'JavaScript','ml':'Machine Learning','social media':'Social Media Marketing','api':'REST APIs'}
canon={s.lower():s for s in skills}

NTH=re.compile(r'bonus if|nice to have|plus, not a must',re.I)

def find_skills(sentence):
    """list skills named in a sentence, longest-first so 'User Research' is not also read as 'Research'"""
    found=[];s=sentence
    for sk in sorted(skills,key=len,reverse=True):
        pat=r'(?<![\w.])'+re.escape(sk)+r'(?![\w])'
        if re.search(pat,s):
            found.append(sk); s=re.sub(pat,' ',s)
    return found

def truth(desc):
    sents=[x.strip() for x in re.split(r'(?<=[.])\s+(?=[A-Z])',desc)]
    sents=sents[1:]   # sentence 1 holds the job title ("Machine Learning Intern") - not a requirement
    req,nth=[],[]
    for s in sents:
        if re.search(r'Stipend|communication matters',s): continue
        f=find_skills(s)
        (nth if NTH.search(s) else req).extend(f)
    return req,nth

def norm(tag):
    t=tag.strip(); l=t.lower()
    if l in canon: return canon[l],'exact'
    if l in SYN: return SYN[l],'synonym'
    return None,'off_list'

rows=[];tagrows=[]
for r in jds:
    req,nth=truth(r['description'])
    tags=[t.strip() for t in r['model_tags'].split(';') if t.strip()]
    right=[];wrong=[];seen=set()
    for t in tags:
        c,kind=norm(t)
        if c in req and c not in seen:
            seen.add(c); right.append(t)
            tagrows.append((r['jd_id'],t,c,'RIGHT','synonym (variant name)' if kind=='synonym' else 'required skill, canonical name'))
        elif c in nth:
            wrong.append(t); tagrows.append((r['jd_id'],t,c,'WRONG','nice-to-have tagged as a requirement'))
        elif kind=='off_list':
            wrong.append(t); tagrows.append((r['jd_id'],t,None,'WRONG','not on skill list (soft skill)' ))
        else:
            wrong.append(t); tagrows.append((r['jd_id'],t,c,'WRONG','list skill not mentioned in the text'))
    missing=[s for s in req if s not in seen]
    rows.append(dict(jd_id=r['jd_id'],title=r['title'],req=req,nth=nth,tags=tags,right=right,wrong=wrong,missing=missing))
json.dump(dict(rows=rows,tagrows=tagrows),open('labels.json','w'),indent=1)

nt=len(tagrows); nright=sum(1 for t in tagrows if t[3]=='RIGHT')
nreq=sum(len(r['req']) for r in rows); nmiss=sum(len(r['missing']) for r in rows)
print('JDs',len(rows),'tags',nt,'right',nright,'wrong',nt-nright)
print('required skills',nreq,'found',nreq-nmiss,'missed',nmiss)
print('wrong by reason',Counter(t[4] for t in tagrows if t[3]=='WRONG'))
print('right by kind',Counter(t[4] for t in tagrows if t[3]=='RIGHT'))
print('wrong tag names',Counter(t[1] for t in tagrows if t[3]=='WRONG').most_common())
print('missed names',Counter(s for r in rows for s in r['missing']).most_common())
print('JDs fully correct (no wrong, no missing):',sum(1 for r in rows if not r['wrong'] and not r['missing']))
print('JDs with >=1 wrong:',sum(1 for r in rows if r['wrong']),' >=1 missing:',sum(1 for r in rows if r['missing']))
print('required per JD',Counter(len(r['req']) for r in rows), 'nth per JD',Counter(len(r['nth']) for r in rows))
