import re
import os
import subprocess

input_md = "Final Report.md"
output_md = "Final Report processed new v2.md"

with open(input_md, "r", encoding="utf-8") as f:
    content = f.read()

mermaid_blocks = re.findall(r"```mermaid(.*?)```", content, re.DOTALL)

for i, block in enumerate(mermaid_blocks):
    mmd_file = f"diagram_{i}.mmd"
    img_file = f"diagram_{i}.png"

    with open(mmd_file, "w", encoding="utf-8") as f:
        f.write(block.strip())

    subprocess.run(["mmdc.cmd", "-i", mmd_file, "-o", img_file])

    # Replace block with image reference
    content = content.replace(f"```mermaid{block}```", f"![diagram]({img_file})")

with open(output_md, "w", encoding="utf-8") as f:
    f.write(content)

print("Processed markdown saved as processed.md")