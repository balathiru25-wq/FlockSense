import glob, re

files = glob.glob('frontend/src/**/*.tsx', recursive=True)
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        txt = fp.read()
    matches = re.findall(r'className=[^"\'{]', txt)
    if matches:
        print(f, len(matches))
