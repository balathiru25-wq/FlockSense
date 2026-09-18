import re

files = [
    'frontend/src/App.tsx',
    'frontend/src/components/AlertsFeed.tsx',
    'frontend/src/components/AudioUploadWidget.tsx',
    'frontend/src/components/FarmerDashboardView.tsx',
    'frontend/src/components/FlockStatusCard.tsx',
    'frontend/src/components/GlobalAudioCard.tsx',
    'frontend/src/components/Header.tsx',
    'frontend/src/components/LanguageSelectionModal.tsx',
    'frontend/src/components/TopCandidatesList.tsx',
    'frontend/src/components/TrackDetailModal.tsx',
    'frontend/src/components/TracksView.tsx'
]

def fix_line(line):
    if 'className=' not in line:
        return line
    # Find positions of className=
    pos = 0
    while True:
        idx = line.find('className=', pos)
        if idx == -1:
            break
        after = idx + len('className=')
        if after < len(line):
            first_char = line[after]
            if first_char in ('"', "'", '{', ''):
                pos = after + 1
                continue
            # Needs quotes! Find the end of this JSX attribute value
            # It ends at ' >', '/>', or ' attr='
            end_idx = len(line)
            for j in range(after, len(line)):
                if line[j] in ('>', '}') or (line[j:j+2] == '/>') or (line[j:j+2] == ' >'):
                    end_idx = j
                    break
                # or space followed by an attribute name like ' style=' or ' id='
                if line[j] == ' ' and j+1 < len(line) and re.match(r'^[a-zA-Z0-9_\-]+=', line[j+1:]):
                    end_idx = j
                    break
            val = line[after:end_idx].strip()
            # If val contains dynamic ternary like {...} or something partly eaten
            # Wrap in double quotes
            val_quoted = f'"{val}"'
            line = line[:after] + val_quoted + line[end_idx:]
            pos = after + len(val_quoted)
        else:
            break
    return line

for p in files:
    try:
        with open(p, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        fixed = [fix_line(l) for l in lines]
        with open(p, 'w', encoding='utf-8') as f:
            f.writelines(fixed)
        print('Fixed:', p)
    except Exception as e:
        print('Err:', p, e)