#!/bin/bash
# + Rar Cleanup Traversal (RCT)
# + ------------------------------------------------------------- +
# | Walks through directory structure and attempts to find all
# | rar files. If a rar file is found, it checks if it has
# | already been extraced or not. If so, it deletes the files
# | in the currently traversed directory.
# | ---
# | Also see https://github.com/arfoll/unrarall.
# | My script is just meant to be a small extension of that.
# + ------------------------------------------------------------- +

# Check if ${1} is a non-empty string:
if [ "${1}" == "" ]; then
  echo "No argument given, aborting."
  exit 1
fi

# Check if ${1} is a valid directory:
if [ ! -d "${1}" ]; then
  echo "${1} is not a valid directory, aborting."
  exit 1
fi

# Check if unrar is installed:
if [ ! $(command -v unrar) ]; then
  echo "Missing unrar command, aborting"
  exit 1
fi


# Set Verbosity (0 = True/On, 1 = False/Off)
RCT_VERBOSE=0

# DEFINE FUNCTIONS

# RarCleanupTraversal (rct)
# Walks Through all Directory in $1 (input) and checks for extraced rar files.
# If the file is extracted, it deletes all rar files it can find.
function rct() {
  for file in "${1}"/*
  do
      # If: Not a directory or a Symlink
      if [ ! -d "${file}" -o -L "${file}" ] ; then
          # check if it's a rar file:
          if [[ "${file}" =~ .*.rar$ ]]; then
            unrar_compare_extracted_fsize "${file}"
            # Check if last command succeeded => OK to proceed
            if [ ${?} -eq 0 ]; then
              # delete all archive files
              _CURRENT_DIR="${1}"
              # extract filename-base from the full file path
              _CURRENT_FILE=$(basename -- "${file%.*}")
              [ RCT_VERBOSE ] && echo "Delete archive files based on ${_CURRENT_FILE}"
              find "${_CURRENT_DIR}" -maxdepth 1 -type f -regextype posix-egrep -iregex ".*/${_CURRENT_FILE}"'\.(sfv|[0-9]+|[r-z][0-9]+|rar|part[0-9]+.rar)$' -exec rm -f '{}' \;
            fi
          fi
      else
          # Do not Enter Directory, if it's a symlink
          if [ ! -L $"{file}" ]; then
            [ RCT_VERBOSE ] && echo "Traversing: ${file}/"
            rct "${file}"
          fi
      fi
  done
}

# --------------------------------------------------------------- #
# Make sure that all files in the archive are extracted correctly
# by comparing the filesize inside the archive with the extracted
# file in the directory.
# --------------------------------------------------------------- #
# TODO: Test with nested files
# --------------------------------------------------------------- #
function unrar_compare_extracted_fsize(){
  # Define RarFile
  rarfile="${1}"
  # Extract all Filenames from rarfile
  files_in_rar=$(unrar l "${rarfile}" | grep '\.\..*' | awk '{ print $5 }')
  # Extract Size+Filenames from rarfile
  files_in_rar_with_size=$(unrar l "${rarfile}" | grep '\.\..*' | awk '{ print $2, $5 }')
  # Define Variable for Success and set it to true by default
  # If any file is not found or the sizes do not match,
  # it should be extracted again.
  ALL_OK=0
  # Iterate over filenames
  while read -r fname; do
  # check if a file exists
    if [ -f "${fname}" ]; then
      # check if filesize matches with the one in the rarfile
      fsize=$(stat --printf="%s" ${fname})
      rsize=$(echo "${files_in_rar_with_size}" | grep "${fname}" | awk '{ print $1 }')
      if [ ${fsize} -eq ${rsize} ]; then
        [ RCT_VERBOSE ] && echo "Extracted-File-Size of ${fname} is equal to Rared-File-Size [ ${fsize} / ${rsize} ]"
      else
        [ RCT_VERBOSE ] && echo "File Sizes do not match!"
        ALL_OK=1
      fi
    else
      [ RCT_VERBOSE ] && echo "Files are not extracted!"
      ALL_OK=1
    fi
  done <<< "${files_in_rar}"
  # Output result
  if [[ ALL_OK -eq 0 ]]; then
    [ RCT_VERBOSE ] && echo "OK $(basename "${1}")"
    return 0
  else
    [ RCT_VERBOSE ] && echo "ERROR $(basename "${1}")"
    return 1
  fi
}


# EXECUTE!
rct "${1}"
