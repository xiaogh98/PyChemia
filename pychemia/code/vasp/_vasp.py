import os
import json
from ._poscar import write_poscar, write_potcar, read_poscar
from ._kpoints import write_kpoints, read_kpoints
from ._incar import write_incar, InputVariables, read_incar
from ._outcar import VaspOutput
from pychemia import Structure, pcm_log
from pychemia.dft import KPoints
from pychemia.code import Codes
from pychemia.utils.computing import unicode2string


class VaspJob(Codes):
    def __init__(self):

        Codes.__init__(self)
        self.structure = None
        self.workdir = None
        self.input_variables = None
        self.potcar_setup = None
        self.potcar_pspfiles = None
        self.potcar_pspdir = 'potpaw_PBE'
        self.kpoints = None
        self.outcar = None
        self.poscar_setup = None
        self.binary = None
        self.stdout_file = None
        self.runner = None
        self.stdout_filename = 'vasp_stdout.log'

    def initialize(self, structure, workdir='.', kpoints=None, binary='vasp'):
        self.workdir = workdir
        self.structure = structure
        self.set_kpoints(kpoints)
        self.binary = binary

    def _check_workdir(self):

        if self.workdir is None:
            raise ValueError("A proper working directory has not been setup")
        elif not os.path.isdir(self.workdir):
            os.makedirs(self.workdir)

    def write_poscar(self):

        self._check_workdir()
        assert (isinstance(self.structure, Structure))

        write_poscar(self.structure, filepath=self.workdir + os.sep + 'POSCAR')

    def write_potcar(self):

        self._check_workdir()
        assert (isinstance(self.structure, Structure))

        pspfiles = write_potcar(self.structure, filepath=self.workdir + os.sep + 'POTCAR', pspdir=self.potcar_pspdir,
                                options=self.potcar_setup, pspfiles=self.potcar_pspfiles)

        self.potcar_pspfiles = pspfiles

    def set_kpoints(self, kpoints):

        assert isinstance(kpoints, KPoints)
        self.kpoints = kpoints

    def write_kpoints(self):

        self._check_workdir()
        assert (isinstance(self.structure, Structure))

        write_kpoints(self.kpoints, filepath=self.workdir + os.sep + 'KPOINTS')

    def write_incar(self):

        self._check_workdir()
        assert (isinstance(self.input_variables, InputVariables))

        write_incar(self.input_variables, filepath=self.workdir + os.sep + 'INCAR')

    def set_input_variables(self, input_variables):

        self._check_workdir()
        assert (isinstance(input_variables, InputVariables))
        self.input_variables = input_variables

    def set_inputs(self):

        self.write_incar()
        self.write_kpoints()
        self.write_poscar()
        self.write_potcar()
        self.save_json(self.workdir + os.sep + 'vaspjob.json')

    @property
    def variables(self):
        return self.input_variables.variables

    @property
    def to_dict(self):
        ret = {'structure': self.structure.to_dict,
               'potcar_pspfiles': self.potcar_pspfiles,
               'potcar_setup': self.potcar_setup,
               'potcar_pspdir': self.potcar_pspdir,
               'workdir': self.workdir,
               'variables': self.variables,
               'kpoints': self.kpoints.to_dict,
               'poscar_setup': self.poscar_setup}
        return ret

    def fromdict(self, vj_dict):
        self.structure = Structure.from_dict(vj_dict['structure'])
        self.potcar_pspfiles = vj_dict['potcar_pspfiles']
        self.potcar_setup = vj_dict['potcar_setup']
        self.workdir = vj_dict['workdir']
        self.input_variables = InputVariables(variables=vj_dict['variables'])
        self.kpoints = vj_dict['kpoints']
        self.poscar_setup = vj_dict['poscar_setup']
        self.potcar_pspdir = vj_dict['potcar_pspdir']

    def load_json(self, filename):
        filep = open(filename, 'r')
        vj_dict = unicode2string(json.load(filep))
        self.fromdict(vj_dict)

    def save_json(self, filename):

        filep = open(filename, 'w')
        json.dump(self.to_dict, filep, sort_keys=True, indent=4, separators=(',', ': '))
        filep.close()

    def read_incar(self):
        self.input_variables = read_incar(self.workdir + os.sep + 'INCAR')

    def read_kpoints(self):
        self.kpoints = read_kpoints(self.workdir + os.sep + 'KPOINTS')

    def read_poscar(self):
        self.structure = read_poscar(self.workdir + os.sep + 'POSCAR')

    def get_outputs(self):
        if os.path.isfile(self.workdir + os.sep + 'OUTCAR'):
            self.outcar = VaspOutput(self.workdir + os.sep + 'OUTCAR')

    def update(self):
        self.read_incar()
        self.read_kpoints()
        self.read_poscar()
        self.get_outputs()

    def finalize(self):
        pass

    def job_static(self):
        inp = InputVariables()
        inp.set_minimum()
        self._check_workdir()
        self.write_potcar()
        inp.set_encut(ENCUT=1.3, POTCAR=self.workdir + os.sep + 'POTCAR')
        inp.set_electron_scf()
        self.set_input_variables(inp)

    def clean(self):
        for i in ['OUTCAR', 'WAVECAR']:
            if os.path.isfile(self.workdir + os.sep + i):
                os.remove(self.workdir + os.sep + i)


class VaspAnalyser:
    def __init__(self, workdir):
        self.workdir = workdir

    def run(self):
        self.files_presence()

    def files_presence(self):

        for i in ['INCAR', 'KPOINTS', 'POSCAR', 'POTCAR']:
            if not os.path.isfile(self.workdir + os.sep + i):
                pcm_log.warning(' File: %s not found' % i)

        for i in ['OUTCAR', 'CONTCAR', 'WAVECAR', 'CHGCAR']:
            if not os.path.isfile(self.workdir + os.sep + i):
                pcm_log.warning(' File: %s not found' % i)
