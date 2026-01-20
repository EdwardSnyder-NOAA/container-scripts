# Overview
The container-scripts repository is a set of scripts that externalizes the spack-stack container. 

At a high-level, the ```convert-modules.py``` script copies out the spack-stack from the container and "syncs" it with the container and in some cases the host machine. This allows users to build their model with the spack-stack container using build [wrapper scripts](#role-of-wrapper-scripts). The model executables will have to be externalized to run inside of the container. 

# File Explanation
Description of each file in the container-scripts repository:

| File                                  | Primary Function |
| -----------                           | -----------------|
|```build_container_executable.sh```    | A wrapper template used to create the build wrapper scripts. Currently not being used. |
|```convert-modules.py```               | Main script that drives the externalization process. |
|```externalize.sh```                   | Creates (“externalize”) wrapper script for executables. Used when user is in/(shells in) the container. |
|```make-external```                    | Helper script for the user to create (“externalize”) wrapper scripts by calling ```dot-externalize.sh```. Found in the user's PATH variable path when the stack is loaded. Ran when outside of the container. |
|```run_container_executable.sh```      | A wrapper template used by ```externalize.sh``` to create the executable wrappers. |
|```update_ss_container_compilers.sh``` | Updates the externalized spack-stack compilers and MPI to either the host compilers or the Intel sandbox. |
|```build_modularized_executable.sh```  | A wrapper template used by ```gen-build-tools.sh``` to create the build wrappers. | 
|```dot-externalize.sh```               | Creates (“externalize”) wrapper script for binary executables. Used when user is outside of the container. | 
|```gen-build-tools.sh```               | Creates (“externalize”) wrapper script for build executables. Used when user is in/(shells in) the container. |
|```modular-externalize.sh```           | Creates (“externalize”) wrapper script for modules. Used when user is outside of the container. | 
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

# Installing of the spack-stack container

## Set up for all configurations
1. Obtain the spack-stack container
2. Set the container to the img variable
3. Create the modulefile directory
4. Copy out the convert-modules.py file 

## Using Host Compilers
Verify that the host machine has Intel and MPI compilers loaded. This is done by running one of the following commands.
If things look in order, then run the follow:

## Using Intel Sandbox
Let’s say the host machine doesn’t have the Intel compilers. In this case, the user can create the Intel sandbox with the Intel compiles in them. To do that, the user would need to run the following commands:
example-dir is location of a writable directory with disk space available
1. mkdir /example-dir/cache
2. mkdir /example-dir/tmp
3. export SINGULARITY_CACHEDIR=/example-dir/cache
4. export SINGULARITY_TMPDIR=/example-dir/tmp

# modifications to build and run 
To build with the externalized spack-stack, the modulefiles of the application needs to point to this stack. See the UFS WM PR for an example. 

Once the application has been built, the executables need to be externalized. The simplest way to do that, is to load the containerized spack-stack, and the stack-intel module. This will put the make-external script in the users PATH variable. Then simply, run the script to externalize the executable. Wildcards are also accepted here: 
make-external /path/to/executable.exe
make-external /path/to/executables/*
