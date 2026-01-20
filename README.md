# Overview
The container-scripts repository is a set of scripts that externalizes the spack-stack container. 

At a high-level, the ```convert-modules.py``` script copies out the spack-stack from the container and "syncs" it via [externalization](#externalization-breakdown) with the container. This allows users to build their model inside of the spack-stack container using build [wrapper scripts](#role-of-wrapper-scripts). The model executables built using the externalized spack-stack container will also be externalized, so that they can run inside of the container via the executable wrapper scripts. 

# File Explanation
Description of each file in the container-scripts repository:

| File                                  | Primary Function |
| -----------                           | -----------------|
|```build_container_executable.sh```    | A wrapper template used to create the build wrapper scripts. Currently not being used. |
|```convert-modules.py```               | Main script that drives the externalization process. |
|```externalize.sh```                   | Creates (“externalize”) wrapper script for executables. Used when the user is in/(shells in) the container. |
|```make-external```                    | Helper script for the user to create (“externalize”) wrapper scripts by calling ```dot-externalize.sh```. Found in the user's ```PATH``` variable path when the stack-oneapi is loaded. Ran when outside of the container. |
|```run_container_executable.sh```      | A wrapper template used by ```externalize.sh``` to create the executable wrappers. |
|```update_ss_container_compilers.sh``` | Updates the externalized spack-stack compilers and MPI to either the host compilers or the Intel sandbox. |
|```build_modularized_executable.sh```  | A wrapper template used by ```gen-build-tools.sh``` to create the build wrappers. | 
|```dot-externalize.sh```               | Creates (“externalize”) wrapper script for binary executables. Used when the user is outside of the container. | 
|```gen-build-tools.sh```               | Creates (“externalize”) wrapper script for build executables. Used when the user is in/(shells in) the container. |
|```modular-externalize.sh```           | Creates (“externalize”) wrapper script for modules. Used when the user is outside of the container. | 
|```run_modularized_executable.sh```    | A wrapper template used by ```dot-externalize.sh``` or ```modular-externalize.sh``` to create the executable or module wrappers. | 

# Externalization Breakdown
It is a two-step process to externalize the spack-stack container:
1. The spack-stack needs to be externalized by the ```convert-modules.py``` script.
2. The wrapper scripts need to be created for the executables. 

## Externalize spack-stack
- Run ```convert-modules.py``` 
  - Takes about 5-15 mins to install
  - Copies out the entire stack
    - appends “SINGULARITYENV_” or “APPTAINERENV_” to the variable names in the lua files. This allows the variables to be imported into the container when you interact with it via wrapper scripts
  - Calls ```make-external``` to create wrapper scripts for binary executables
    - Ex: ncdump, ndate, etc.
  - Calls ```gen-build.sh``` to create wrapper scripts for build tools
    - Ex: cmake , ecbuild, etc
  - Calls ```update_ss_container_compilers.sh``` to update the compilers if using the runtime container

## Role of wrapper scripts
A wrapper script is the primary way to interact with the externalized spack-stack container by externalizing the executables via the ```make-external``` or the ```externalize.sh``` scripts. When an executable is externalized, the executable is renamed and the wrapper script replaces the executable on the host machine. Meaning the wrapper script will be called in the executables place. 

The wrapper script consists of a number of singularity variables, the singularity exec command, and the executable name it replaced with any arguments. When the wrapper script is called, it will run the executable it replaced inside of the container using the singularity exec command. See below for contents of a wrapper script for the cmake build executable:
```
#!/bin/bash
#set -x
export img=/work/noaa/epic/esnyder/ss-192-cont/new-rt/again/final/ubuntu22.04-intel-ufs-env-v1.9.2-runtime.img
export SINGULARITYENV_FI_PROVIDER=tcp
export SINGULARITYENV_FI_PROVIDER_PATH=/apps/spack-managed/oneapi-2024.1.0/intel-oneapi-mpi-2021.12.0-ehon7g4v724zl5ks5ihv53suriijlbpk/mpi/2021.12/opt/mpi/libfabric/lib/prov:/usr/lib64/libfabric
export SINGULARITY_SHELL=/bin/bash
cmd=cmake
arg="$@"
singularity exec -e   -B /apps -B /work "${img}" $cmd $arg
```

# Installing of the externalized spack-stack container
The user has two choices when it comes to installing the spack-stack container either to use the host compilers or the Intel sandbox. Both methods use the same initial setup and the externalization of the executables (i.e. wrapper scripts).

## Set up for all configurations
1. Obtain the spack-stack container
2. Set the container to the ```img```variable
   ```
   export img=/path/to/ubuntu22.04-intel-ufs-env-v1.9.2-runtime.img
   ```
3. Create and navigate to the modulefiles directory
   ```
   mkdir modulefiles
   cd modulefiles
   ```
4. Copy out the convert-modules.py file
   ```
   singularity exec -B /<top-dir> $img cp /opt/container-scripts/convert-modules.py .
   ```
   Notes: top-dir is the first dir in your $PWD. And you may have to module load singularity or apptainer before running this command.

### Using host compilers
Verify that the host machine has Intel compilers and Intel MPI loaded. This is done by running one of the following commands:
```
which ifort icx icpx
echo $I_MPI_ROOT
echo $INTEL_ONEAPI_MPI_ROOT
```
If things look in order, then run the follow to build the externalized spack-stack with the host compilers:
```
python3 convert-modules.py -i $img -o $PWD/spack-stack-1.9.2 --host-compilers
```

### Using Intel sandbox
Lets say the host machine doesn’t have the Intel compilers or Intel MPI installed. In this case, the user can create the Intel sandbox with the Intel compiles in them. To do that, the user would need to run the following commands:
```
mkdir /example-dir/cache
mkdir /example-dir/tmp
export SINGULARITY_CACHEDIR=/example-dir/cache
export SINGULARITY_TMPDIR=/example-dir/tmp
singularity build --sandbox intel-sandbox docker://noaaepic/intel-hpckit:2024.2.0-1-devel-ubuntu22.04
```
Note: example-dir is the location of a writable directory with disk space available.

## Building and running with the externalized spack-stack container
Once the externalized spack-stack is built, the UFS WM or Application needs to point to it. This is done by updating the ```MODULEPATH``` variable in the modulefiles. See the [UFS WM PR](https://github.com/ufs-community/ufs-weather-model/compare/develop...EdwardSnyder-NOAA:ufs-weather-model:container-ss192) for an example of how the modulefiles are being updated. 

After the application has been built, the executables need to be externalized. The simplest way to do that is to load the externalized spack-stack, and the stack-oneapi module. This will put the ```make-external``` script in the user's ```PATH``` variable. Then simply run the script to externalize the executable. Wildcards are also accepted here: 
```
make-external /path/to/executable.exe
make-external /path/to/executables/*
```
Please note that additional modifications are needed to the UFS WM or Applications workflow to incorporate this new method. See this [UFS WM PR](https://github.com/ufs-community/ufs-weather-model/compare/develop...EdwardSnyder-NOAA:ufs-weather-model:container-ss192) for how to use this container with the UFS WM RTs system by updating the ```compile.sh``` file.
