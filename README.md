# Conda Watch

This is a command-line interface for Conda Watch, a tool for monitoring changes in Conda packages.

## Installation

Run the following commands from your own project directory.

- Install the rdflib package which is used to create a graph database and serialze the 
data to disk. Install rdflib into your own project, not the conda_watch project.

```bash
conda install -y rdflib
```

- Copy the conda-watch.py script into /usr/local/bin so that it is available from any
directory. Note that sudo is needed. Make sure to look at the python script to examine
it for security issues. Never trust code from the internet!

```bash
sudo cp conda-watch.py /usr/local/bin
```

- Now setup the DEBUG trap which runs the conda-watch script after every shell command. Running "trap - DEBUG" removes this trap.

```bash
trap 'conda-watch.py ${BASH_COMMAND}' DEBUG
```

Now the script is watching for "conda install", "conda remove", and "conda update" 
commands.

## Experimentation

If you want to experiment with changing the script, then install it into a single directory.

- Add the conda-watch.py script to your python project directory.
- Add the current directory to your path.
```bash
export PATH=.:$PATH
```
- Set the DEBUG trap.
```bash
trap 'conda-watch.py ${BASH_COMMAND}' DEBUG
```

## Usage

For normal use, just run conda commands normally. The script will store commands and package
lists in a local TTL text file.

You can learn about your conda history with the following commands.

- `cw-dates`: List the dates that conda commands were run. The cw-history command is
probably more generally useful.

- `cw-history`: Show the history of commands.

These commands are for the geeks who understand TTL files.

- `cw-subjects`: List all unique subjects.
- `cw-predicates`: List all unique predicates.
- `cw-triples`: List all triples.

## Commentary

This script monitors the conda environment after every shell command after it is installed. 
It stores the results in a file called conda-watch.ttl in the current directory. Always run
your conda commands from the root of your project directory. 

Each time that you install, remove, or update your conda environment, the script will store
the timestamp, the command, and the packages that are installed in the conda environment.

Use:
 * cw-history to see the history of conda commands that have been run.
 * cw-tripes to see all of the information that has been stored in the conda-watch.ttl file.

The data model used by this Python script is RDF. RDF is a way to represent information in 
a structured way. It is based on the idea of triples, which are made up of a subject, a 
predicate, and an object. 

The script uses the rdflib library to create and manage the RDF graph. The graph is stored 
in a file called conda-watch.ttl. The script also provides two commands for interacting with 
the graph: cw-history and cw-triples. The cw-history command prints a table of all of the 
conda commands that have been run, while the cw-triples command prints all of the triples 
in the graph.

Side note: I used .hidden.* to hide files that I don't want in the git repository. 
You might want to place the TTL under version control. If so, then remove the 
.hidden. from the default value for data_file.

