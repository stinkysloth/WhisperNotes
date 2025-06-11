#!/usr/bin/env python
"""Fix unterminated triple-quoted string in whisper_notes.py"""
import re
import sys

def fix_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for any unbalanced triple quotes
    triple_quotes = re.findall('"""', content)
    if len(triple_quotes) % 2 != 0:
        print(f"Found {len(triple_quotes)} triple quotes, which is an odd number")
        # Find the last instance of triple quotes and add a closing one
        lines = content.split('\n')
        fixed_content = []
        string_open = False
        
        for i, line in enumerate(lines, 1):
            if '"""' in line:
                count = line.count('"""')
                for _ in range(count):
                    string_open = not string_open
            fixed_content.append(line)
        
        if string_open:
            print(f"String still open at end of file, adding closing triple quotes")
            fixed_content.append('"""')
        
        # Write the fixed content back
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_content))
        print(f"Fixed {filename}")
    else:
        print(f"No unbalanced triple quotes found, but there may still be syntax issues")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "whisper_notes.py"
    
    fixed = fix_file(filename)
    if fixed:
        print("Attempted to fix the file, please check it manually.")
    else:
        print("No obvious issues found with triple quotes.")
