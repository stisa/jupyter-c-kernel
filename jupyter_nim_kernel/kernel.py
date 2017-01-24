from queue import Queue
from threading import Thread

from ipykernel.kernelbase import Kernel
import subprocess
import tempfile
import os
import os.path as path

class RealTimeSubprocess(subprocess.Popen):
    """
    A subprocess that allows to read its stdout and stderr in real time
    """

    def __init__(self, cmd, write_to_stdout, write_to_stderr):
        """
        :param cmd: the command to execute
        :param write_to_stdout: a callable that will be called with chunks of data from stdout
        :param write_to_stderr: a callable that will be called with chunks of data from stderr
        """

        self._write_to_stdout = write_to_stdout
        self._write_to_stderr = write_to_stderr

        super().__init__(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

        self._stdout_queue = Queue()
        self._stdout_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stdout, self._stdout_queue))
        self._stdout_thread.daemon = True
        self._stdout_thread.start()

        self._stderr_queue = Queue()
        self._stderr_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stderr, self._stderr_queue))
        self._stderr_thread.daemon = True
        self._stderr_thread.start()

    @staticmethod
    def _enqueue_output(stream, queue):
        """
        Add chunks of data from a stream to a queue until the stream is empty.
        """
        for line in iter(lambda: stream.read(4096), b''):
            queue.put(line)
        stream.close()

    def write_contents(self):
        """
        Write the available content from stdin and stderr where specified when the instance was created
        :return:
        """

        def read_all_from_queue(queue):
            res = b''
            size = queue.qsize()
            while size != 0:
                res += queue.get_nowait()
                size -= 1
            return res

        stdout_contents = read_all_from_queue(self._stdout_queue)
        if stdout_contents:
            self._write_to_stdout(stdout_contents)
        stderr_contents = read_all_from_queue(self._stderr_queue)
        if stderr_contents:
            self._write_to_stderr(stderr_contents)

class MyRandomSequence(tempfile._RandomNameSequence):
    characters = "abcdefghijklmnopqrstuvwxyz0123456789"

class NimKernel(Kernel):
    implementation = 'jupyter_nim_kernel'
    implementation_version = '1.0'
    language = 'nim'
    language_version = '0.14.2'
    language_info = {'name': 'nim',
                     'mimetype': 'text/plain',
                     'file_extension': '.nim'}
    banner = "Nim kernel.\n" \
             "Uses nim, and creates source code files and executables in temporary folder.\n"

    def __init__(self, *args, **kwargs):
        super(NimKernel, self).__init__(*args, **kwargs)
        self.files = [] # all files generated by temp
        self.sources = [] # list of .nim files
        self.debug = False # controls debug statements without commenting
        
      # mastertemp = tempfile.mkstemp(suffix='.out')
      # os.close(mastertemp[0])
      # self.master_path = mastertemp[1] # absolute pathname to tmpfile
      # msp = "-o:"+self.master_path
      # filepath = path.join(path.dirname(path.realpath(__file__)), '..', 'resources', 'master.nim')
      # subprocess.call(['nim', 'c', '--verbosity:0', '--app:lib', msp, filepath])
      # subprocess.call(['gcc', filepath, '-std=c11', '-rdynamic', '-ldl', '-o', self.master_path])

    def debug_to_file (self,msg, filename='C:\\Users\\silvio\\Documents\\Dev\\nim\\jupyter-kernel\\jupyter-nim-kernel\\debug.txt'):
        if (self.debug==True):
            fsa = open(filename,'a')
            fsa.write(str(msg))

    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for file in self.files:
            os.remove(file)
        #os.remove(self.master_path)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        kwargs['prefix'] = 'nim'

        # only names which are ok for nim modules
        tempfile._name_sequence = MyRandomSequence()

        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
        if ( file.name.endswith(".nim")):
            self.sources.append(file.name)
        return file

    def _write_to_stdout(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def create_jupyter_subprocess(self, cmd):
        return RealTimeSubprocess(cmd,
                                  lambda contents: self._write_to_stdout(contents.decode()),
                                  lambda contents: self._write_to_stderr(contents.decode()))

    def compile_with_nimc(self, source_filename, binary_filename,additional=[]):
        #args = ['gcc', source_filename, '-std=c11', '-fPIC', '-shared', '-rdynamic', '-o', binary_filename]
        obf = '-o:'+binary_filename
        args = ['nim', 'c', '--hint[Processing]:off', '--verbosity:0', '-t:-fPIC', '-t:-shared']+additional+[obf, source_filename]
        return self.create_jupyter_subprocess(args)

    def load_block(self, blockid):
        if self.execution_count!=blockid:
            if(len(self.sources)>=blockid ):
                srccontent = open(self.sources[blockid-1], 'r').read().replace('echo','#echo') # comment out echos
                return srccontent
            else:
                self._write_to_stderr("[Nim kernel] Block "+str(blockid)+" not found")
        else: 
            self._write_to_stderr("[Nim kernel] You cannot load the block while you are executing it")

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
                   
        other_args=[] # List of additional commands to pass to the compiler
  
        magiclines = [l for l in code.split('\n') if l.startswith('#>')] # search for lines that use magics

        # Execute magics
        for l in magiclines:
            # Magic to load a block, takes 1 argument, the execution id of a block #TODO: allow ranges of blocks?
            if l[0:11]=='#>loadblock':
                blocktoload = int(l[11:].split()[0])
                code = '\n'+self.load_block(blocktoload)+'\n'+code
            
            # Magic to pass flags directly to nim            
            elif l[0:10]=='#>passflag':
                other_args.append(l[10:].replace(' ','')) # trim and append to commands TODO: if I avoid trimming, can we pass multiple flag in one line?
            
        # Compile code using a temp file
        with self.new_temp_file(suffix='.nim') as source_file:
            source_file.write(code)
            source_file.flush()
            with self.new_temp_file(suffix='.out') as binary_file:
                p = self.compile_with_nimc(source_file.name, binary_file.name, other_args)
                while p.poll() is None:
                    p.write_contents()
                p.write_contents()
                if p.returncode != 0:  # Compilation failed
                    self._write_to_stderr(
                            "[Nim kernel] nimc exited with code {}, the executable will not be executed".format(
                                    p.returncode))
                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}

        # Run the compiled temp file 
        p = self.create_jupyter_subprocess([binary_file.name]) #self.master_path,
        while p.poll() is None:
            p.write_contents()
        p.write_contents()
        if p.returncode != 0:
            self._write_to_stderr("[Nim kernel] Executable exited with code {}".format(p.returncode))
        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}

    def do_shutdown(self, restart):
        """Cleanup the created source code files and executables when shutting down the kernel"""
        self.cleanup_files()

    def do_complete(self, code, cursor_pos):
        ws = set('\n\r\t ')
        lf = set('\n\r')
        sw = cursor_pos
        while sw > 0 and code[sw - 1] not in ws:
            sw -= 1
        sl = sw
        while sl > 0 and code[sl - 1] not in lf:
            sl -= 1
        wrd = code[sw:cursor_pos]
#        lin = code[sl:cursor_pos]

        # TODO: nimsuggest??

        matches = [] # list of all possible matches

        # Snippets
        if 'proc'.startswith(wrd):
            matches.append("proc name(arg:type):returnType = \n    #proc")
        elif 'if'.startswith(wrd):
            matches.append("if (expression):\n    #then")
        elif 'method'.startswith(wrd):
            matches.append("method name(arg:type): returnType = \n    #method")
        elif 'iterator'.startswith(wrd):
            matches.append("iterator name(arg:type): returnType = \n    #iterator")
        elif 'array'.startswith(wrd):
            matches.append("array[length, type]")
        elif 'seq'.startswith(wrd):
            matches.append("seq[type]")
        elif 'for'.startswith(wrd):
            matches.append("for index in iterable):\n    #for loop")
        elif 'while'.startswith(wrd):
            matches.append("while(condition):\n    #while loop")
        elif 'block'.startswith(wrd):
            matches.append("block name:\n    #block")
        elif 'case'.startswith(wrd):
            matches.append("case variable:\nof value:\n    #then\nelse:\n    #else")
        elif 'try'.startswith(wrd):
            matches.append("try:\n    #something\nexcept exception:\n    #handle exception")
        elif 'template'.startswith(wrd):
            matches.append("template name (arg:type): returnType =\n    #template")
        elif 'macro'.startswith(wrd):
            matches.append("macro name (arg:type): returnType =\n    #macro")
                
        # Single word matches
        single = 'int float string addr and as asm atomic bind break cast concept ' \
            'const continue converter defer discard distinct div do ' \
            'elif else end enum except export finally for from func ' \
            'generic import in include interface is isnot ' \
            'let mixin mod nil not notin object of or out ' \
            'ptr raise ref return shl shr static ' \
            'tuple type using var when with without xor yield'.split()

        magics = ['#>loadblock ','#>passflag ']
        
        # Add all matches to our list
        matches = matches+[t for t in single if t.startswith(wrd)]+[mag for mag in magics if mag.startswith(wrd)]

        return {'status': 'ok', 'matches': matches,
            'cursor_start': sw, 'cursor_end': cursor_pos, 'metadata': {}}