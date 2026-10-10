import re
with open('frontend/src/main.jsx', encoding='utf-8') as f:
    text = f.read()
matches = re.findall(r'className=["\']([^"\']+)["\']', text)
classes = set()
for m in matches:
    for c in m.split():
        if c and '{' not in c and '$' not in c:
            classes.add(c)
print('Total unique classes:', len(classes))
tw = [c for c in classes if any(c.startswith(p) for p in ['text-', 'bg-', 'p-', 'm-', 'flex', 'grid', 'gap-', 'w-', 'h-', 'items-', 'justify-', 'font-', 'rounded', 'border-', 'block', 'hidden', 'truncate', 'leading-'])]
print('Tailwind-like classes count:', len(tw))
print('Examples:', sorted(tw))
