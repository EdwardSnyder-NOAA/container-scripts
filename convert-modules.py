import os
import re
import subprocess
from argparse import ArgumentParser
import stat

def is_binary_executable(file_path):
    # Check if the file exists and is a regular file
    if not os.path.isfile(file_path):
        return False

    try:
        isascii = os.popen("file "+file_path+" | /usr/bin/grep ASCII").read().strip()
        if re.search("ASCII",isascii):
            return False
        else:
            return True

    except OSError:
        pass

    return False

def get_binary_executables(dirpath):
    # List files that are executable binaries
    file_list = os.listdir(dirpath)
    binary_executables = [file for file in file_list if is_binary_executable(os.path.join(dirpath,file))]

    return binary_executables


def read_envs_from_file(file_path):
    """
    Read environment variables from a text file with one per line.
    
    :param file_path: str, The path to the file containing environment variable names.
    :return: list, A list of environment variable names to be replaced.
    """
    envs_to_modify = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                env_name = line.strip()
                if env_name:
                    envs_to_modify.append(env_name)
        return envs_to_modify
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

def modify_lua_content(content, envs_to_modify, compiler_type):
    """
    Modify environment variable references in Lua content by prepending APPTAINERENV_.
    
    :param content: str, The Lua file content as a string.
    :param envs_to_modify: list, Environment variable names to be prefixed.
    :return: str, The modified Lua file content.
    """

    """
    Determine if system is running singularity or apptainer
    """

    output = subprocess.check_output(["singularity", "help"]).decode("utf-8")
    global env_regex
    if 'apptainer' in output:
      env_regex = "APPTAINERENV_"
    else:
      env_regex = "SINGULARITYENV_"
    for env in envs_to_modify:
        # Create regex pattern for variables with double quotes
        pattern = rf'"{env}"'
        modified_content = re.sub(pattern, f'"{env_regex}{env}"', content)
        if modified_content != content:
            content = modified_content
    
    # Iterate over each line in the content
    modified_content_lines = []
    local_path = args.output_dir+"/bin"
    command = "singularity exec -B "+basepath+" $img cp /opt/container-scripts/make-external ."
    os.system(command)
    # Update bind dirs and add FI PROVIDER to script
    command = "sed -i 's| -B|"+comp_top_dirs+" -B|g' make-external"
    os.system(command)
    #command = "sed -i 's|fi_provider_path=\(.*\)|fi_provider_path="+fi_provider+"|g' make-external"
    #os.system(command)
    for line in content.split('\n'):
    # check to see if the path is being set in the modulefile
        pattern = rf'"{env_regex}PATH"'
        match = re.search(pattern,line)
        new_pattern = os.getcwd()
        if match:
           if(compiler_type == "intel"):
             new_line = re.sub(r'"([^"]*)\s*(?=intel)', f'"{new_pattern}/', line)
           else:
             new_line = re.sub(r'"([^"]*)\s*(?=oneapi)', f'"{new_pattern}/', line)
#          new_line = re.sub(r'"([^"]*)\s*(?=' + re.escape(compiler_type) + ')', f'"{new_pattern}/"', line)
           new_line = re.sub(pattern, '"PATH"', new_line)
           parts = new_line.split('"')
           bindir = parts[3]
           parts = line.split('"')
           containerdir = parts[3]
           print("checking bindir of ",bindir)
           # create the same directory on the local host
           host_root_dir=os.path.abspath(os.path.join(bindir, "../.."))
           container_root_dir=os.path.abspath(os.path.join(containerdir, ".."))
           command="singularity exec -B "+basepath+" "+args.img+" mkdir -p "+bindir
           print(command)
           os.system(command)
           # copy in all the files from the container to the host
           command = "singularity exec -B "+basepath+" "+args.img+" cp -r "+container_root_dir+" "+host_root_dir
           print(command)
           os.system(command)
           print("container bindir is ",containerdir)
           # now externalize the executables in that directory on the host
           if(os.path.exists(bindir)):
             binary_files = get_binary_executables(bindir)
             print(binary_files)
             for binfile in binary_files:
               command = "./make-external "+os.path.join(bindir,binfile) 
               print(command)
               os.system(command)
           content += new_line
           break

    return content


def copy_and_modify_lua_files(output_dir, vars_file, compiler_type):
    """
    Copy all Lua files from the source directory to a new output directory,
    modifying them by prepending APPTAINERENV_ or SINGULARITYENV to specified environment variables.
    
    :param output_dir: str, The path to the output directory where modified Lua files will be saved.
    :param vars_file: str, The path to the file containing environment variable names.
    """
    source_dir = "./modulefiles"
    print("running copy and modify")
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".lua"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    modified_content = modify_lua_content(content, read_envs_from_file(vars_file),compiler_type)
                    
                    # Determine the output file path relative to the source directory
                    relative_path = os.path.relpath(file_path, source_dir)
                    output_file_path = os.path.join(output_dir, relative_path)
                    
                    # Ensure the correct parent directories exist
                    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                    
                    with open(output_file_path, 'w') as f:
                        f.write(modified_content)
        
        print("Modified Lua files have been saved to the specified output directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = ArgumentParser(description="Modify Lua environment variable references")
    parser.add_argument("-i", "--container-image", dest="img", required=True,
                        help="Path to the singularity image file containing spack-stack")
    parser.add_argument("-o", "--output-dir", dest="output_dir", required=True,
                        help="Path to the output directory for modified Lua files")
    
    args = parser.parse_args()
    #set the img as an environment variable
    os.environ['img'] = args.img
    #get the basename of PWD to bind with singularity
    command = "dirname $PWD | awk -F'/' '{print $2}'"
    basepath = "/"+os.popen(command).read().strip()+" "

    # Check if host compilers are loaded
    icx_loc = os.popen("/usr/bin/which icx").read().strip()
    icpx_loc = os.popen("/usr/bin/which icpx").read().strip()
    ifort_loc = os.popen("/usr/bin/which ifort").read().strip()

    compiler_list = [icx_loc,icpx_loc,ifort_loc]
    if any(len(item) == 0 for item in compiler_list):
        print("Missing compilers. Please load them before running this script!")
        exit(1)

    # Check is MPI variables exists
    i_mpi_root = os.getenv('I_MPI_ROOT')
    #fi_provider = os.getenv('FI_PROVIDER_PATH')
    if i_mpi_root is None:
        print("Missing I_MPI_ROOT variable! Exiting!")
        exit(1)

    # Create compiler base path list & compiler top dir list
    compilers_base_list = []
    compilers_top_dir = [i_mpi_root.split("/")[1]]
    # Get compilers base path(s)
    for path in [icx_loc,icpx_loc,ifort_loc]:
        base_path = os.path.dirname(os.path.abspath(path))
        base_dir = base_path.split("/")[1] 
        if base_path not in compilers_base_list:
            compilers_base_list.append(base_path)
        if base_dir not in compilers_top_dir:
            compilers_top_dir.append(base_dir)
    compilers_base_string = ":".join(compilers_base_list)   

    # Create compiler host dirs, so that they can be added to the make-external wrappers
    dir_format=" -B /{0}"
    comp_top_dirs=""
    for top_dir in compilers_top_dir:
        comp_top_dirs = comp_top_dirs + dir_format.format(top_dir)

    #get the spack-stack version
    command =  'singularity exec $img ls /opt/spack-stack'
    spack_stack_ver = os.popen(command).read().strip()
    # copy the all the modulefiles out of the container image
    command = "singularity exec -e -B "+basepath+args.img+" cp -r /opt/spack-stack/"+spack_stack_ver+"/envs/unified-env/install/modulefiles ."
    print(command)
    os.system(command)

    # get the stack type (intel v oneapi)
    stack_type=os.popen("ls ./modulefiles/Core").read().strip()
    compiler_type=stack_type.split("-")[1]

#   command = "singularity exec -e -B "+basepath+args.img+" cp -r /opt/spack-stack/"+spack_stack_ver+"/envs/unified-env/install/"+compiler_type+" ."
#   os.system(command)

    # get a list of all the files that contain either setenv, or _path
    os.system("/usr/bin/grep -R setenv modulefiles/* | awk -F '\"' '{print $2}' | sort | uniq > .envs")
    os.system("/usr/bin/grep -R _path modulefiles/* | awk -F '\"' '{print $2}' | sort | uniq >> .envs")
    os.system("sed -i '/MODULEPATH/d' .envs")
    # walk through all the files and change variables to contain APPTAINERENV_ or SINGULARITYENV_
    copy_and_modify_lua_files(args.output_dir, ".envs", compiler_type)

    # get the original module path from the lua file
    command = '/usr/bin/grep MODULEPATH ./modulefiles/Core/'+stack_type+'/*.lua | awk -F \'"\' \'{print $4}\''
    # Split if we have more than one spack-stack location
    spack_stack_path = os.popen(command).read().strip().split("\n")
    # Loop through list
    for ss_path in spack_stack_path:
        #print(ss_path)
        parts = ss_path.split('/')
        modulefiles_index = parts.index("modulefiles")
        parts[:modulefiles_index + 1] = [args.output_dir]
        new_path = '/'.join(parts)
        #print(f"new_path: {new_path}")
        command ="/usr/bin/grep -R -l MODULEPATH "+args.output_dir+"/Core | xargs sed -i 's|"+ss_path+"|"+new_path+"|g'"
        os.system(command)

    # get the origin module path for the mpi module
    command = '/usr/bin/grep -R MODULEPATH ./modulefiles/'+compiler_type+' | awk -F \'"\' \'{print $4}\' | head -n 1'
    mpi_stack_path = os.popen(command).read().strip()
    print(mpi_stack_path)
    # hack to get this working
    mpi_stack_path = re.sub("fms-2024.01","unified-env",mpi_stack_path)

    print("using this modulepath to grep",mpi_stack_path)
    # replace the original path with the new path on the host system
    parts = mpi_stack_path.split('/')
    modulefiles_index = parts.index("modulefiles")
    parts[:modulefiles_index + 1] = [args.output_dir]
    new_path = '/'.join(parts)
    
    # Update to host compilers in openmpi compiler lua file
    command = "/usr/bin/grep -R -l MODULEPATH "+args.output_dir+"/"+compiler_type
    stack_oneapi_lua_file = os.popen(command).read().strip()
    
    for compiler in compiler_list:
        comp_name = os.path.basename(compiler)
        if comp_name == 'ifort':
            env_name = ['F77','F90','FC']
        elif comp_name == 'icpx':
            env_name = ['CXX']
        elif comp_name == 'icx':
            env_name = ['CC']

        for env in env_name:
            command = '/usr/bin/grep -R I_MPI_'+env+' '+stack_oneapi_lua_file+' | awk -F \'"\' \'{print $4}\''
            container_path = os.popen(command).read().strip()
            command = "sed -i 's|"+container_path+"|"+compiler+"|g' "+stack_oneapi_lua_file
            os.system(command)
            
    command ="sed -i 's|"+mpi_stack_path+"|"+new_path+"|g' " + stack_oneapi_lua_file
    print("running this command for modulepath ",command)
    os.system(command)

    # Update intel oneapi mpi root variable to host
    command = '/usr/bin/grep -R intel_oneapi_mpi_ROOT '+stack_oneapi_lua_file+' | awk -F \'"\' \'{print $4}\''
    mpi_root=os.popen(command).read().strip()
    host_mpi_root = os.getenv('INTEL_ONEAPI_MPI_ROOT')
    command = "sed -i 's|"+mpi_root+"|"+host_mpi_root+"|g' "+stack_oneapi_lua_file
    os.system(command)

    # Set PATH and I_MPI_ROOT variables to host compilers in Core stack lua file
    stack_intel_lua_file = args.output_dir+'/Core/'+stack_type+'/*.lua'
    #env_regex = "APPTAINERENV_"
    command = f"sed -i '/prereq/a prepend_path(\"{env_regex}I_MPI_ROOT\",\""+i_mpi_root+"\")' "+stack_intel_lua_file
    os.system(command)
    command = f"sed -i '/prereq/a setenv(\"{env_regex}PATH\",\""+compilers_base_string+":"+i_mpi_root+"/bin\")' "+stack_intel_lua_file
    os.system(command)

    # Update compilers to host in Core stack lua file
    for compiler in compiler_list:
        comp_name = os.path.basename(compiler)
        if comp_name == 'ifort':
            env_name = ['F77', 'FC']
        elif comp_name == 'icpx':
            env_name = ['CXX']
        elif comp_name == 'icx':
            env_name = ['CC']

        for env in env_name:
            command = '/usr/bin/grep -R SERIAL_'+env+' '+stack_intel_lua_file+' | awk -F \'"\' \'{print $4}\''
            container_path = os.popen(command).read().strip()
            command = "sed -i 's|"+container_path+"|"+compiler+"|g' "+stack_intel_lua_file
            os.system(command)
    
    # Update library paths to host library
    command = '/usr/bin/grep -R LIBRARY_PATH '+stack_intel_lua_file+' | awk -F \'"\' \'{print $4}\''
    lib_path=os.popen(command).read().strip()
    host_lib_path = os.getenv('LIBRARY_PATH')
    command = "sed -i 's|"+lib_path+"|"+host_lib_path+"|g' "+stack_intel_lua_file
    os.system(command)

    command = '/usr/bin/grep -R LD_LIBRARY_PATH '+stack_intel_lua_file+' | awk -F \'"\' \'{print $4}\''
    ld_lib_path=os.popen(command).read().strip()
    host_ld_lib_path = os.getenv('LD_LIBRARY_PATH')
    command = "sed -i 's|"+ld_lib_path+"|"+host_ld_lib_path+"|g' "+stack_intel_lua_file
    os.system(command)
    
    # some lua systems are incompatable with depends_on, so change that to load. It is slower, but works
    # NOTE: depends_on works now but leaving in if it is needed on other T1 platforms
    #command = "/usr/bin/grep -R -l depends_on "+args.output_dir+"/* | xargs sed -i 's/depends_on/load/g'"
    #os.system(command)

    #set path on host system to $PWD/args.output_dir/bin, which is where the gen tools will be placed
    #add img to the stack-intel/oneapi module as well
    local_path = args.output_dir+"/bin"
    os.system("mkdir "+local_path)
    new_line = 'prepend_path("PATH","'+local_path+'")'
    sed_command = f'sed -i \'/ENV_PATH/a {new_line}\' {stack_intel_lua_file}'
    os.system(sed_command)
    new_line = 'setenv("img","'+args.img+'")'
    sed_command = f'sed -i \'/ENV_PATH/a {new_line}\' {stack_intel_lua_file}'
    os.system(sed_command)

    # Add compiler and mpi base path to gen-builds, so that they can be added to the build tool wrappers
    # generate the build tools locally in $PWD/bin. This path will be added to the path set in stack-intel module
    command = "singularity exec -B "+basepath + comp_top_dirs +" -e $img /opt/container-scripts/gen-build-tools.sh -e "+local_path
    os.system(command)
    os.system("rm -rf ./modulefiles")
    #os.system("rm ./make-external")
    # Fix build tools
    #command = "sed -i 's|FI_PROVIDER_PATH=\(.*\)|FI_PROVIDER_PATH="+fi_provider+"|g' "+local_path+"/*"
    #os.system(command)

    #put make-external in the bin path
    command = "mv make-external "+local_path
    os.system(command)

    command = "echo $(find "+args.output_dir+" -iname netcdf-c)/*"
    luafile = os.popen(command).read().strip()
    os.system("echo >> "+luafile)
    command = "cat "+luafile+" | /usr/bin/grep ENV_LD_LIBRARY_PATH | sed 's/LD_LIB/LIB/g' >>"+luafile
    os.system(command)
