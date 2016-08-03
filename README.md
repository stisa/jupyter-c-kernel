# Minimal Nim kernel for Jupyter

This is a rough adaptation of https://github.com/brendan-rius/jupyter-c-kernel .
It's mostly functional, there are probably bugs lurking around.

Look at [example-notebook](https://github.com/stisa/jupyter-nim-kernel/blob/master/example-notebook.ipynb) for some examples.

**NOTE**: Context is **NOT** shared between blocks!!
I'll try working on it when I have time.

## Prereqs
- a working `nim` installation ( [download](http://nim-lang.org/download.html) )
- a working `jupyter` (and  **python 3^**) installation ( I recomend [miniconda3](http://conda.pydata.org/miniconda.html) and adding jupyter with `conda install jupyter` )

## Installation
- `pip install jupyter_nim_kernel`
- `git clone https://github.com/stisa/jupyter-nim-kernel.git`
- `cd jupyter-nim-kernel`
- `jupyter-kernelspec install nim_spec/`
- Done, now run `jupyter-notebook` and select `new->Nim`

## Manual Installation
- `git clone https://github.com/stisa/jupyter-nim-kernel.git`
- `cd jupyter-nim-kernel`
- `pip install -e .`
- `jupyter-kernelspec install nim_spec/`
- Done, now run `jupyter-notebook` and select `new->Nim`

## Note
Forked from https://github.com/brendan-rius/jupyter-c-kernel and adapted to work 
with [nim](nim-lang.org).  

This a simple proof of concept. It's not intended to be used in production in its current shape.   

## Known bugs
- The output is littered with `Hint: [Processing]...` statements, despite using `--verbosity:0`
- Every block is treated as a separate file ( not really a bug, it's just not yet implemented )
- Others?

## License
[MIT](LICENSE.txt)

##Changelog

- 03-08-2016 : `stisa` Added some snippets to completion ( e.g. : write `pr` then hit `tab` )
- 02-08-2016 : `oderwat` Fixed temporary filenames being incompatible with nim
- 02-08-2016 : Initial publish