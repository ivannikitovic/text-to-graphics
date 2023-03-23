from pathlib import Path
import requests
import xml.etree.ElementTree as ET
import urllib.request
import os
import tarfile
import re

NUMBER_OF_PAPERS = 75
SOURCE_DIRECTORY = Path("./zipped_source")
OUTPUT_DIRECTORY = Path("./output_tex")

if str(SOURCE_DIRECTORY) not in os.listdir("."):
    os.mkdir(SOURCE_DIRECTORY)

if str(OUTPUT_DIRECTORY) not in os.listdir("."):
    os.mkdir(OUTPUT_DIRECTORY)

# arXiv API for getting the math/physics paper ids
url = 'http://export.arxiv.org/api/query'

params = {
    'search_query': 'cat:math* OR cat:physics*',
    'start': '0',
    'max_results': str(NUMBER_OF_PAPERS),
    'sortBy': 'submittedDate',
    'sortOrder': 'descending'
}

response = requests.get(url, params=params)
root = ET.fromstring(response.content)

arxiv_ids = []
for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
    arxiv_id = entry.find('{http://www.w3.org/2005/Atom}id').text.split('/')[-1]
    arxiv_ids.append(arxiv_id)
    
# Download the source files
for arxiv_id in arxiv_ids:
    url = 'https://arxiv.org/e-print/' + arxiv_id
    filename = arxiv_id + '.tar.gz'
    if filename not in os.listdir(SOURCE_DIRECTORY):
        urllib.request.urlretrieve(url, SOURCE_DIRECTORY / filename)
        print('Downloaded ' + filename)
    else:
        print('Found ' + filename)

print()

for filename in os.listdir(SOURCE_DIRECTORY):
    if filename.endswith('.tar.gz'):

        try:
            with tarfile.open(SOURCE_DIRECTORY / filename) as tar:
                # Find the .tex file in the archive
                tex_file = None
                try:
                    for member in tar.getmembers():
                        if member.name.endswith('.tex'):
                            tex_file = member
                            break
                except EOFError as error:
                    print(filename + ': not found or corrupted, skipping')

                # If a .tex file is found, extract the tikzpicture block
                if tex_file is not None:
                    with tar.extractfile(tex_file) as tex:
                        # Read the .tex file and find the tikzpicture block
                        tikz_list = []
                        use_packages = set()
                        tikz_idx = 0
                        in_tikz = False

                        entire_file = tex.read().decode('utf-8', errors='replace')
                        if re.search(r"\\usepackage(.*?){(.*?)}", entire_file, re.DOTALL):
                            test2 = re.findall(r"\\usepackage(?:.*?){(?:.*?)}", entire_file, re.DOTALL)
                            packages = test2
                        tex = tar.extractfile(tex_file)
                        # TODO: ! THIS IS HORRIBLE TO UNZIP IT AGAIN :(, FIX THIS
                        # TODO: order of packages important, need to figure that out!

                        for line in tex:
                            line = line.decode('utf-8', errors='replace')

                            if re.search(r"(\\begin{tikzpicture}).*", line):
                                in_tikz = True
                                tikz_list.append("")
                                tikz_list[tikz_idx] += re.search(r"(\\begin{tikzpicture}).*", line).group(0)

                            elif re.search(r".*(\\end{tikzpicture})", line):
                                in_tikz = False
                                tikz_list[tikz_idx] += re.search(r".*(\\end{tikzpicture})", line).group(0)
                                tikz_idx += 1

                            elif in_tikz:
                                tikz_list[tikz_idx] += line

                        if tikz_list == []:
                            print(filename + ': no TikZ found')

                        for i, tikz in enumerate(tikz_list):
                            output_filename = filename.replace('.tar.gz', f'_{str(i)}' + '.tex')
                            if output_filename in os.listdir(OUTPUT_DIRECTORY):
                                print('found ' + output_filename)
                                continue

                            header = "\\documentclass{article}\n"

                            header += "\n".join(packages)

                            header += "\\usepackage{tikz}\n\\thispagestyle{empty}\n\\begin{document}"
                            footer = "\\end{document}"

                            with open(OUTPUT_DIRECTORY / output_filename, 'w') as output:
                                output.write(header + tikz + footer)
                            print(filename + ': extracted TikZ code to ' + str(OUTPUT_DIRECTORY))
                                
                else:
                    print(filename + ': no .tex file found')   

        except tarfile.ReadError:
           print(filename + ': not found or corrupted, skipping')
