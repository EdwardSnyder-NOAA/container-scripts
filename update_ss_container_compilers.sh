#!/bin/bash

#set -x

################################################################################
# Help                                                                         #
################################################################################

Help()
{
   # Display Help
   echo 
   echo "This script updates the compilers in the spack-stack container."
   echo
   echo "Syntax: ./update_ss_container_compilers.sh [-h|-i <intel sandbox location>|-s <container spack-stack locaton>]"
   echo "options:"
   echo "-h     Print this Help."
   echo "-i     (optional) location of intel sandbox in the format of /path/to/intel-sandbox"
   echo "-s     (required) location of container spack-stack in format of /path/to/modulefiles/spack-stack-#.#.#"
   echo
}

while getopts ":hi:s:" flag;
do 
    case "${flag}" in
    h) Help
        exit ;;
    i) intel_sandbox="${OPTARG#=}" ;;
    s) ss_location="${OPTARG#=}" ;;
    #:) echo "Missing argument for -s" >&2
    #   exit 1 ;;
   \?) echo "Invalid option. Exiting!"
        exit 1 ;;
    esac
done

if [[ -z "$ss_location" ]]; then
    echo "Missing container spack-stack location argument!"
    Help
    exit 1
fi

################################################################################
# Main Program                                                                 #
################################################################################


# Set up compiler and mpi variables
if [[ -z "$intel_sandbox" ]]; then
    
    echo "Using host compilers and mpi"
    new_ifort=$(which ifort)
    new_icx=$(which icx)
    new_icpx=$(which icpx)
    
    new_lib="${LIBRARY_PATH}"
    new_ld_lib="${LD_LIBRARY_PATH}"

    new_i_mpi_root="${I_MPI_ROOT}"
    new_intel_oneapi_mpi_root="${INTEL_ONEAPI_MPI_ROOT}"
    new_path="${new_i_mpi_root}/bin":$(dirname "$new_icx")

else
    # Verify if intel sandbox location exists
    intel_sandbox_rp=$(realpath "$intel_sandbox")
    if [[ ! -d "$intel_sandbox_rp" ]]; then
        echo "intel sandbox location doesn't exist!"
        exit 1
    fi

    echo "Using Intel sandbox compilers and mpi"
    new_ifort=$(realpath "$intel_sandbox_rp/opt/intel/oneapi/compiler/latest/bin/ifort")
    new_icx=$(realpath "$intel_sandbox_rp/opt/intel/oneapi/compiler/latest/bin/icx")
    new_icpx=$(realpath "$intel_sandbox_rp/opt/intel/oneapi/compiler/latest/bin/icpx")

    new_lib="/opt/intel/oneapi/redist/opt/mpi/libfabric/lib:/opt/intel/oneapi/redist/lib"
    new_ld_lib="/opt/intel/oneapi/redist/opt/mpi/libfabric/lib:/opt/intel/oneapi/redist/lib"

    new_i_mpi_root="$intel_sandbox_rp/opt/intel/oneapi/mpi/2021.13"
    new_intel_oneapi_mpi_root="$intel_sandbox_rp/opt/intel/oneapi"
    new_path="${new_i_mpi_root}/bin":$(dirname "$new_icx")
fi

# Ensure that the compilers are MPI are set before running
echo $new_ifort 
echo $new_icx
echo $new_icpx
echo $new_lib
echo $new_ld_lib
echo $new_i_mpi_root
echo $new_intel_oneapi_mpi_root
echo $new_path
#exit 1
#new_ifort=$(which ifort)
#new_icx=$(which icx)
#new_icpx=$(which icpx)

if [[ -z "$new_ifort" || -z "$new_icx" || -z "$new_icpx" ]]; then
    echo "Please load the compilers you want in your spack-stack before running this script!"
    exit 1
fi

if [[ -z "$new_i_mpi_root" || -z "$new_intel_oneapi_mpi_root" ]]; then
    echo "Please load the MPI you want in your spack-stack before running this script"
    exit 1
fi

# Verify if spack-stack location exists
ss_location_rp=$(realpath "$ss_location")
if [[ ! -d "$ss_location_rp" ]]; then
    echo "spack-stack location doesn't exist!"
    exit 1
fi

ss_ver=$(basename "$ss_location_rp")
[[ ! "$ss_ver" =~ "spack-stack-" ]] && echo "spack-stack path wasn't passed properly! Check command line argument." && exit 1

# sed function for compiler variables
sed_compilers () {
    if [[ $1 == 'ifort' ]]; then
        env_vars=( "F77" "FC" "F90")
    elif [[ $1 == 'icx' ]]; then
        env_vars=("CC")
    elif [[ $1 == 'icpx' ]]; then
        env_vars=("CXX")
    fi
    #echo $env_vars
    # Get compiler in container spack-stack
    for env_var in "${env_vars[@]}"; do
        #echo $env_var
	ss_compiler=$(/usr/bin/grep -r SERIAL_$env_var $2 | awk -F '"' '{print $4}')
	ss_mpi=$(/usr/bin/grep -r I_MPI_$env_var $3 | awk -F '"' '{print $4}')
	#echo $ss_compiler
	#echo $2
	new_compiler="new_$1"

        if [[ $env_var == "F90" ]]; then
	    echo "Updating to ${!new_compiler} in $3"
            sed -i  "s|"$ss_mpi"|"${!new_compiler}"|g" $3
        else
            echo "Updating to ${!new_compiler} in $2"
            sed -i "s|"$ss_compiler"|"${!new_compiler}"|g" $2
	    echo "Updating to ${!new_compiler} in $3"
            sed -i "s|"$ss_mpi"|"${!new_compiler}"|g" $3
        fi
    done
}

# Get spack-stack lua files that need to be updated
comp_lua_file=$(/usr/bin/grep -rl MODULEPATH "$ss_location_rp/Core")
comp_type=$(ls "$ss_location_rp/Core/" | awk -F '-' '{print $2}')
mpi_lua_file=$(/usr/bin/grep -rl MODULEPATH $ss_location_rp/$comp_type)

# Run sed_compilers function to update compilers
for compiler in icx icpx ifort; do
    sed_compilers $compiler "$comp_lua_file" "$mpi_lua_file"
done

# Changes for non-compiler variables
echo "Setting various variables"
ss_path=$(/usr/bin/grep -r ENV_PATH "$comp_lua_file" | awk -F '"' '{print $4}')
sed -i "s|"$ss_path"|"$new_path"|g" $comp_lua_file

ss_i_mpi_root=$(/usr/bin/grep -r I_MPI_ROOT "$comp_lua_file" | awk -F '"' '{print $4}')
sed -i "s|"$ss_i_mpi_root"|"$new_i_mpi_root"|g" $comp_lua_file

ss_lib_path=$(/usr/bin/grep -r ENV_LIBRARY_PATH "$comp_lua_file" | awk -F '"' '{print $4}')
sed -i "s|"$ss_lib_path"|"$new_lib"|g" $comp_lua_file

ss_ld_lib_path=$(/usr/bin/grep -r ENV_LD_LIBRARY_PATH "$comp_lua_file" | awk -F '"' '{print $4}')
sed -i "s|"$ss_ld_lib_path"|"$new_ld_lib"|g" $comp_lua_file

ss_intel_oneapi_mpi_root=$(/usr/bin/grep -r intel_oneapi_mpi_ROOT "$mpi_lua_file" | awk -F '"' '{print $4}')
sed -i "s|"$ss_intel_oneapi_mpi_root"|"$new_intel_oneapi_mpi_root"|g" $mpi_lua_file

# Get list of dirs to bind
echo "Finding dirs to bind to wrapper script"
top_dir=()
add_me=1

for p in $new_i_mpi_root $new_intel_oneapi_mpi_root $new_icx; do
    dir=$(echo $p | awk -F'/' '{print $2}')
    for td in "${top_dir[@]}"; do
        if [[ "$td" == "$dir" || "opt" == "$dir" ]]; then
            echo "$dir is found in array. Break loop."
            add_me=0
            break
        fi
    done
    if [[ $add_me == 1 ]]; then
        echo "Add $dir to array"
        top_dir+=($dir)
    fi
done

# Create wrapper array
echo "Creating array of wrapper scripts"
base_ss_location=$(dirname $ss_location_rp)
wrapper_array=()

while IFS= read -r line; do
    wrapper_array+=( "$line" )
done < <(grep -rl ENV_FI_PROVIDER_PATH $ss_location_rp/bin/* $base_ss_location/$comp_type/*/*/bin/*)

echo "Updating bind dir in wrapper scripts"
for wrap in "${wrapper_array[@]}"; do

    # Update FI PROVIDER PATH
    #sed -i "s|FI_PROVIDER_PATH=\(.*\)|FI_PROVIDER_PATH="${FI_PROVIDER_PATH}"|g" $wrap

    #fp=$(realpath $wrap)
    #top_dir=$(echo $wrap | awk -F'/' '{print $2}')
    for td in "${top_dir[@]}"; do
        if ! grep -qr "B /$td" $wrap; then
            echo "Missing top dir! Add it!"
            sed -i "s| -B| -B /$top_dir -B|1" $wrap
        fi
    done
done
echo "DONE"
