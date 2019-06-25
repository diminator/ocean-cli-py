import pathlib
import jupytext
import json


def snippet_header():
    return f'''from ocean_cli.ocean import get_ocean'''


def snippet_object(did):

    return f'''
response = get_ocean('config.ini').authorize('{did}')
response
'''


def create_notebook(did, name):
    snippet = snippet_header() + \
              snippet_object(did)
    # Get the IPython script root dir
    root_dir = pathlib.Path.cwd().joinpath("")
    kernelspec = """ {"kernelspec" : {
       "display_name": "Manta Ray",
       "language": "python",
       "name": "python3"
       }}
    """.replace("\n", "")
    kernel_spec_dict = json.loads(kernelspec)

    # The output path
    jupyter_file_name = name + '.ipynb'
    out_path = root_dir / jupyter_file_name

    # Parse the script to Jupyter format
    parsed = jupytext.reads(snippet, fmt='.py', format_name='percent')
    parsed['metadata'].update(kernel_spec_dict)

    # Delete the file if it exists
    if out_path.exists():
        out_path.unlink()

    # Write the result
    jupytext.writef(parsed, out_path)

    return snippet
