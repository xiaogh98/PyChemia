"""
There are two kinds of Repositories in PyChemia

Structure Repositories where many structures are stored
Execution Repositories where  the out of every calculation
is stored

Each structure contains some metadata that is accessible with
the StructureEntry object
Also each calculation has it own metadata accessible by ExecutionEntry
object
"""
import hashlib

import json as _json
import os as _os
import uuid as _uuid
import shutil as _shutil
import math
from pychemia.geometry import load_structure_json
from pychemia.utils.computing import unicode2string


class StructureEntry():
    """
    Defines one entry in the repository of Structures
    """

    def __init__(self, structure=None, repository=None, identifier=None, original_file=None, tags=None):
        """
        Creates a new Entry for Structures
        If identifier is provided the corresponding Structure is load in the Entry
        Otherwise a new entry is created with a UUID random identifier

        Args:
        identifier: (string) UUID identifier for a structure
        repository: (object) The StructureRepository that will be associated
        original_file: (string) Path to the original file (CIF, POSCAR, etc)
        tags: (string or list) Tags that will be associated to that structure
        """
        self.properties = None

        if identifier is None:
            self.structure = structure
            self.identifier = str(_uuid.uuid4())
            self.path = None
            if original_file is not None:
                assert (_os.path.isfile(original_file))
            self.original_file = original_file
            self.parents = []
            self.children = []
            if isinstance(tags, str):
                self.tags = [tags]
            elif isinstance(tags, list):
                self.tags = tags
            elif tags is None:
                self.tags = []
            else:
                raise ValueError('The variable tags must be a string or list of strings')

        else:
            assert (original_file is None)
            assert (structure is None)
            assert (tags is None)
            assert (repository is not None)
            self.identifier = identifier
            self.repository = repository
            self.path = self.repository.path + '/' + self.identifier
            if not _os.path.isdir(self.path):
                raise ValueError("Directory not found: " + self.path)
            if not _os.path.isfile(self.path + '/metadata.json'):
                raise ValueError("No metadata found in " + self.path)
            if not _os.path.isfile(self.path + '/structure.json'):
                raise ValueError("No structure found in " + self.path)
            self.load()

    def metadatatodict(self):
        ret = {'tags': self.tags,
               'parents': self.parents,
               'children': self.children}
        return ret

    def load(self):
        assert isinstance(self.identifier, str)
        rf = open(self.path + '/metadata.json', 'r')
        self.metadatafromdict(unicode2string(_json.load(rf)))
        rf.close()
        if self.tags is None:
            self.tags = []
        if self.children is None:
            self.children = []
        if self.parents is None:
            self.parents = []
        self.structure = load_structure_json(self.path + '/structure.json')
        if _os.path.isfile(self.path + '/properties.json'):
            rf = open(self.path + '/properties.json', 'r')
            self.properties = unicode2string(_json.load(rf))
            rf.close()
        self.load_originals()

    def load_originals(self):
        orig_dir = self.path + '/original'
        if _os.path.isdir(orig_dir):
            self.original_file = [_os.path.abspath(orig_dir + '/'+x) for x in _os.listdir(orig_dir)]
        else:
            self.original_file = []

    def save(self):
        if self.path is None:
            self.path = self.repository.path + '/' + self.identifier
        wf = open(self.path + '/metadata.json', 'w')
        _json.dump(self.metadatatodict(), wf, sort_keys=True, indent=4, separators=(',', ': '))
        wf.close()
        self.structure.save_json(self.path + '/structure.json')
        if self.properties is not None:
            wf = open(self.path + '/properties.json', 'w')
            _json.dump(self.properties, wf, sort_keys=True, indent=4, separators=(',', ': '))
            wf.close()
        if self.original_file is not None:
            self.add_original_file(self.original_file)

    def metadatafromdict(self, entrydict):
        self.tags = entrydict['tags']
        self.parents = entrydict['parents']
        self.children = entrydict['children']

    def add_tags(self, tags):
        _add2list(tags, self.tags)

    def add_parents(self, parents):
        _add2list(parents, self.parents)

    def add_children(self, children):
        _add2list(children, self.children)

    def add_original_file(self, filep):
        orig_dir = self.path + '/original'
        if isinstance(filep, str):
            filep = [filep]
        self.load_originals()
        hashs = {}
        for iorig in self.original_file:
            rf = open(iorig, 'r')
            hashs[iorig] = hashlib.sha224(rf.read()).hexdigest()
            rf.close()

        for ifile in filep:
            assert(_os.path.isfile(ifile))
            rf = open(ifile, 'r')
            hash_ifile = hashlib.sha224(rf.read()).hexdigest()

            if hash_ifile in hashs.values():
                continue

            if ifile not in self.original_file:
                if not _os.path.isdir(orig_dir):
                    _os.mkdir(orig_dir)

                if not _os.path.isfile(orig_dir + '/' + _os.path.basename(ifile)):
                    _shutil.copy2(ifile, orig_dir)
                else:
                    i = 0
                    while True:
                        newfile = ifile + '_' + str(i)
                        if not _os.path.isfile(orig_dir + '/' + _os.path.basename(newfile)):
                            _shutil.copy(ifile, orig_dir + '/'+_os.path.basename(newfile))
                            break
                        else:
                            i += 1
        self.load_originals()

    def __str__(self):
        ret = 'Structure: \n' + str(self.structure)
        ret += '\nTags: ' + str(self.tags)
        ret += '\nParents: ' + str(self.parents)
        ret += '\nChildren: ' + str(self.children)
        ret += '\nIdentifier: ' + str(self.identifier)
        ret += '\nOriginal Files:'+str(self.original_file)
        ret += '\n'
        return ret

    def __eq__(self, other):
        ret = True
        if self.structure != other.structure:
            print 'Not equal structure'
            ret = False
        elif self.children is None and other.children is not None:
            ret =False
        elif self.children is not None and other.children is None:
            ret =False
        elif self.children is not None and set(self.children) != set(other.children):
            print 'Not equal children'
            ret = False
        elif self.parents is None and other.parents is not None:
            ret =False
        elif self.parents is not None and other.parents is None:
            ret =False
        elif self.parents is not None and set(self.parents) != set(other.parents):
            print 'Not equal parents'
            ret = False
        elif self.tags is None and other.tags is not None:
            ret =False
        elif self.tags is not None and other.tags is None:
            ret =False
        elif self.tags is not None and set(self.tags) != set(other.tags):
            print 'Not equal tags'
            ret = False
        return ret

    def __ne__(self, other):
        return not self.__eq__(other)


class ExecutionEntry():
    """
    Defines one execution in the Execution Repository
    """

    def __init__(self, path):
        """
        Creates a new execution repository
        """
        self.path = path


class StructureRepository():
    """
    Defines the location of the executions repository
    and structure repository and methods to add, remove
    and check those repositories
    """

    def __init__(self, path):
        """
        Creates new repositories for calculations and structures

        Args:
        path: (string) Directory path for the structure repository
        """
        self.path = _os.path.abspath(path)

        if _os.path.isfile(self.path + '/repo.json'):
            self.load()
        else:
            self.tags = {}

            if _os.path.lexists(self.path):
                if not _os.path.isdir(self.path):
                    raise ValueError('Path exists already and it is not a directory')
            else:
                _os.mkdir(self.path)
            self.save()

    def todict(self):
        """
        Serialize the values of the repositories into a dictionary
        """
        repos_dict = {'tags': self.tags}

        return repos_dict

    def fromdict(self, repos_dict):
        self.tags = repos_dict['tags']

    def save(self):
        """
        Save an existing repository information
        """
        wf = open(self.path + '/repo.json', 'w')
        _json.dump(self.todict(), wf, sort_keys=True, indent=4, separators=(',', ': '))
        wf.close()

    def load(self):
        """
        Loads an existing repositories from its configuration file
        """
        rf = open(self.path + '/repo.json', 'r')
        self.fromdict(unicode2string(_json.load(rf)))
        rf.close()

    @property
    def get_all_entries(self):
        return [x for x in _os.listdir(self.path) if _os.path.isfile(self.path + '/' + x + '/metadata.json')]

    def __len__(self):
        return len(self.get_all_entries)

    def get_formulas(self):
        formulas = {}
        for i in self.get_all_entries:
            ientry = StructureEntry(repository=self, identifier=i)
            formula = ientry.structure.formula
            if formula in formulas:
                formulas[formula].append(i)
            else:
                formulas[formula] = [i]
        return formulas

    def merge2entries(self, orig, dest):
        assert(orig.structure == dest.structure)
        dest.add_parents(orig.parents)
        dest.add_children(orig.children)
        dest.add_tags(orig.tags)
        if orig.original_file is not None and len(orig.original_file) > 0:
            dest.add_original_file(orig.original_file)
        dest.save()
        self.del_entry(orig)

    def clean(self):
        for i in self.tags:
            for j in self.tags[i]:
                if not _os.path.isdir(self.path+'/'+j) or not _os.path.isfile(self.path+'/'+j+'/metadata.json'):
                    print 'Removing', j
                    self.tags[i].remove(j)
        self.save()

    def refine(self):
        formulas = self.get_formulas()
        for j in formulas:
            print j
            if len(formulas[j]) > 1:
                for i in range(len(formulas[j])-1):
                    stru1 = StructureEntry(repository=self, identifier=formulas[j][i])
                    stru2 = StructureEntry(repository=self, identifier=formulas[j][i+1])
                    if stru1 == stru2:
                        self.merge2entries(stru1, stru2)
        self.save()

    def merge(self, other):
        """
        Add all the contents from other repositories into the
        calling object

        :param other: StructureRepository
        """
        conflict_entries = []
        for i in other.get_all_enties:
            if i in self.get_all_entries:
                other_structure = StructureEntry(repository=other, identifier=i)
                this_structure = StructureEntry(repository=self, identifier=i)
                if this_structure != other_structure:
                    conflict_entries.append(i)
        if len(conflict_entries) == 0:
            for i in other.get_all_enties:
                if i not in self.get_all_entries:
                    _shutil.copytree(other.path+'/'+i, self.path+'/'+i)
        else:
            print('Conflict entries found, No merge done')
            return conflict_entries

    def add_entry(self, entry):
        """
        Add a new StructureEntry into the repository
        """
        entry.repository = self
        entry.path = self.path + '/' + entry.identifier
        if not _os.path.isdir(entry.path):
            _os.mkdir(entry.path)
        entry.save()
        if entry.tags is not None:
            for itag in entry.tags:
                if itag in self.tags:
                    if not entry.identifier in self.tags[itag]:
                        self.tags[itag].append(entry.identifier)
                else:
                    self.tags[itag] = [entry.identifier]
        self.save()

    def add_many_entries(self, list_of_entries, tag, number_threads=1):

        from threading import Thread
        from pychemia.external.pymatgen import cif2structure

        def worker(cifs, tag, results):
            results['succeed'] = []
            results['failed'] = []
            for i in cifs:
                try:
                    struct=cif2structure(i, primitive=True)
                except:
                    struct=None
                    results['failed'].append(i)
                if struct is not None:
                    structentry = StructureEntry(structure=struct, original_file=i, tags=[tag])
                    self.add_entry(structentry)
                    results['succeed'].append(i)

        results={}
        th = []
        results = []
        num = int(math.ceil(float(len(list_of_entries))/number_threads))
        for i in range(number_threads):
            results.append({})
            th.append(Thread(target=worker, args=(list_of_entries[i*num:min((i+1)*num, len(list_of_entries))], tag, results[i])))
        for i in th:
            i.start()
        return th, results


    def del_entry(self, entry):
        print 'Deleting ', entry.identifier
        for i in entry.tags:
            self.tags[i].remove(entry.identifier)
        _shutil.rmtree(entry.path)

    def __str__(self):
        ret = 'Location: ' + self.path
        ret += '\nNumber of entries: ' + str(len(self))
        if len(self.tags) > 0:
            for itag in self.tags:
                ret += '\n\t' + itag + ':'
                ret += '\n' + str(self.tags[itag])
        else:
            ret += '\nTags: ' + str(self.tags)
        return ret


class ExecutionRepository():
    """
    Defines the location and properties of the Repository
    where all the executions will be stored
    """

    def __init__(self):
        """
        Creates a Repository for Executions
        """
        pass


def _add2list(orig, dest):
    if isinstance(orig, str):
        if not orig in dest:
            dest.append(orig)
    elif isinstance(orig, list):
        for iorig in dest:
            if not iorig in dest:
                dest.append(iorig)
