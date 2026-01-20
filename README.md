# Overview
The container-scripts repository is a set of scripts that externalizes the spack-stack container. 

At a high-level, the ```convert-modules.py``` script copies out the spack-stack from the container and "syncs" it with the container and in some cases the host machine. This allows users to build their model with the spack-stack container using build [wrapper scripts](#role-of-wrapper-scripts). The model executables will have to be externalized to run inside of the container. 

# File Explanation
The following is a list of these scripts as well as their primary function.

| File                                  | Primary Function |
| -----------                           | -----------------|
|```build_container_executable.sh```    | A wrapper template used to create the build wrapper scripts when ran inside of the container. |
|```convert-modules.py```               | Main script that calls other scripts. Is one of three scripts the user interacts with. |
|```externalize.sh```                   | Creates (“externalize”) wrapper script. Used when user shells into the container. |
|```make-external```                    | Helper script for the user to create (“externalize”) wrapper scripts. Found in the user's PATH variable path when the stack is loaded. Ran when outside of the container. |
|```run_container_executable.sh```      | A wrapper template used to create the executable wrappers when ran inside of the container. |
|```update_ss_container_compilers.sh``` | Updates the externalized spack-stack compilers and MPI to either the host compilers or the Intel sandbox. |
|```Build_modularized_executable.sh```  | A wrapper template used to create the build wrappers when ran outside of the container. | 
|```dot-externalize.sh```               | Creates (“externalize”) wrapper script binary executables. Used when user is outside of the container. | 
|```gen-build-tools.sh```               | Creates (“externalize”) wrapper script for build executable. Used when user is in (shell) the container. |
|```modular-externalize.sh```           | Creates (“externalize”) wrapper script for modules. Used when user is outside of the container. | 
|```Run_modularized_executable.sh```    | A wrapper template used to create the executable wrappers when the user is outside of the container. | 

# Externalization Breakdown
It is a two-step process to externalize the spack-stack container. First, the spack-stack needs to be externalized by the convert-modules.py script. Second, wrapper scripts need to be created for the executables. 

## Externalize spack-stack
- Run ```convert-modules.py``` 
  - Takes about 5-15 mins to install
  - Copies out the entire stack
    - appends “SINGULARITYENV_” to the variable names in the lua files. This allows the variables to be imported into the container when you interact with it via wrapper scripts
  - Calls make-external to create wrapper scripts for binary executables
    - Ex: ncdump, ndate, etc.
  - Calls gen-build.sh to create wrapper scripts for build tools
    - Ex: cmake , ecbuild, etc
  - Calls update_ss_container_compilers.sh to update the compilers if using runtime container
    - “Syncs” the Intel host compilers and MPI or the Intel Sandbox to the copied out externalized spack-stack

## Role of wrapper scripts
A wrapper script is the primary way to interact with the externalized spack-stack container by externalizing the executables (see list below for the externalized scripts). When an executable is externalized, the executable is renamed and the wrapper script replaces the executable on the host machine. Meaning the wrapper script will be called in the executables place. 

The wrapper script consists of a number of singularity variables, the singularity exec command, and the executable name it replaced with any arguments. When the wrapper script is called, it will run the executable it replaced inside of the container. See below for contents of a wrapper script for the cmake build executable:


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
