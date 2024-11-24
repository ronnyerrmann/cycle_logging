#!/bin/bash

WORK_DIR=/tmp/tiles/
SRTM_BASE_1=/mnt/backup500/srtm/1/
SRTM_BASE_3=/mnt/backup500/srtm/3/
DEST_DIR=/mnt/backup500/srtm/tiles/   # if changed, adjust TILES_FOLDERS in my_base.py

mkdir -p "${WORK_DIR}" "${DEST_DIR}"

create_individual_tifs() {
  local srtm_base="$1"
  shift   # remove first parameter
  local base_names=("$@") # Capture all arguments as an array
  for base in "${base_names[@]}"; do
    cmd="gdal_translate ${srtm_base}${base}.hgt.zip ${WORK_DIR}${base}.tif"
    echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
    ${cmd}
  done
}

process_area() {
  local srtm_base="$1"
  shift

  # Get all the the dynamic ranges
  local ranges=()
  while [[ "$1" != "" ]]; do
    if [[ "$1" == N* || "$1" == S* ]]; then
      break
    fi
    ranges+=("$1")
    shift
  done

  local base_names=("$@") # Remaining htg names

  create_individual_tifs "${srtm_base}" "${base_names[@]}"

  # merge
  all_tifs=""
  for base in "${base_names[@]}"; do
    all_tifs="${all_tifs} ${WORK_DIR}${base}.tif"
  done
  rm -f "${WORK_DIR}merged.tif"
  cmd="gdal_merge.py -o ${WORK_DIR}merged.tif ${all_tifs}"
  echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
  ${cmd}
  rm -f "${all_tifs}"

  for dynamic_range in "${ranges[@]}"; do
    # Create the tiles
    IFS='_' read -r start end _ <<< "${dynamic_range}"
    rm -f "${WORK_DIR}merged_8bit.tif"
    cmd="gdal_translate -ot Byte -scale ${start} ${end} ${WORK_DIR}merged.tif ${WORK_DIR}merged_8bit.tif"
    echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
    ${cmd}

    cmd="gdal2tiles.py -z 5-13 -tms ${WORK_DIR}merged_8bit.tif ${WORK_DIR}tiles_${dynamic_range}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
    ${cmd}

    echo "$(date '+%Y-%m-%d %H:%M:%S') storing tiles here"
    if [[ "${WORK_DIR}" != "${DEST_DIR}" ]]; then
      rsync -au "${WORK_DIR}tiles_${dynamic_range}" "${DEST_DIR}"
      rm -r "${WORK_DIR}tiles_${dynamic_range}"
    fi
  done
}

# Give the following parameters:
#  - srtm 1 or 3 resolution
#  - all the dynamic ranges for the tiles in the form <min>_<max>
#    - the png will be stored as 8 bit, e.g. 256 different grey scales
#  - all the base names for the htg.zip files

# UK
process_area $SRTM_BASE_3 "0_255" "0_1024" \
  "N49W006" \
  "N50E000" "N50E001" "N50W001" "N50W002" "N50W003" "N50W004" "N50W005" "N50W006" \
  "N51E000" "N51E001" "N51W001" "N51W002" "N51W003" "N51W004" "N51W005" \
  "N52E000" "N52E001" "N52W001" "N52W002" "N52W003" "N52W004" "N52W005" \
  "N53E000" "N53W001" "N53W002" "N53W003" "N53W004" "N53W005" \
  "N54W001" "N54W002" "N54W003" "N54W004" "N54W005" \
  "N55W002" "N55W003" "N55W004" "N55W005" "N55W006" "N55W007" \
  "N56W003" "N56W004" "N56W005" "N56W006" "N56W007" \
  "N57W003" "N57W004" "N57W005" "N57W006" "N57W007" \
  "N58W003" "N58W004" "N58W005" "N58W006" "N58W007"

# La Palma
process_area $SRTM_BASE_3 "0_255" "0_1024" "0_4096" \
  "N28W017" "N28W018" "N28W019"
