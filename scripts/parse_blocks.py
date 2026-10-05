import re, json, sys

def parse(md):
    lines = md.split('\n')
    blocks=[]; i=0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i+=1; continue
        if s == '---':
            blocks.append({'t':'hr'}); i+=1; continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            blocks.append({'t':'h'+str(len(m.group(1))), 'x':m.group(2)}); i+=1; continue
        if s.startswith('>'):
            q=[]
            while i < len(lines) and lines[i].strip().startswith('>'):
                q.append(re.sub(r'^>\s?','',lines[i].strip()))
                i+=1
            blocks.append({'t':'quote','items':q}); continue
        if re.match(r'^[-*]\s+', s):
            items=[]
            while i < len(lines) and re.match(r'^[-*]\s+', lines[i].strip()):
                items.append(re.sub(r'^[-*]\s+','',lines[i].strip()))
                i+=1
            blocks.append({'t':'ul','items':items}); continue
        # paragraph (single line in this source)
        blocks.append({'t':'p','x':s}); i+=1
    return blocks

md = open('ingest/normalized.md',encoding='utf-8').read()
blocks = parse(md)
for idx,b in enumerate(blocks):
    if b['t'] in ('ul','quote'):
        print(f"{idx:3} {b['t']:5} ({len(b['items'])}): {b['items'][0][:60]}")
    elif b['t']=='hr':
        print(f"{idx:3} hr    ----")
    else:
        print(f"{idx:3} {b['t']:5} : {b['x'][:70]}")
print("TOTAL", len(blocks))
json.dump(blocks, open('/tmp/blocks.json','w'), ensure_ascii=False)
